"""Voting tests (HU-LI05) — Constitution Principle II/III.

Votes are ``actions`` rows of type VOTE (content POSITIVE/NEGATIVE) — no new
table. Two layers are covered:

1. Asset Action Service logic, exercised directly against the in-memory SQLite
   `session` fixture (no auth needed; user_id is a plain int — SQLite does not
   enforce the users FK).
2. Route contract: the `/api/actions/votes/*` endpoints must be auth-gated and
   advertised in the OpenAPI schema.
"""

from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import actions_service as svc
from app.lib.internal.models import Action, Asset
from app.lib.internal.actions_service import VOTE_POSITIVE, VOTE_NEGATIVE


def _mk_asset(session, name="Asset One"):
    asset = Asset(name=name, status="PUBLISHED")
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _vote_rows(session, user_id, asset_id):
    return session.exec(
        select(Action).where(
            Action.asset == asset_id,
            Action.user_id == user_id,
            Action.type == "VOTE",
        )
    ).all()


# --- Service logic ---------------------------------------------------------

def test_first_vote_creates_positive(session):
    asset = _mk_asset(session)
    assert svc.count_votes(session, asset.id)["score"] == 0

    svc.set_vote(session, 1, asset.id, VOTE_POSITIVE)
    tally = svc.get_vote_tally(session, asset.id, user_id=1)
    assert tally == {"positive": 1, "negative": 0, "score": 1, "my_vote": "POSITIVE"}


def test_same_value_toggles_off(session):
    asset = _mk_asset(session)
    svc.set_vote(session, 1, asset.id, VOTE_POSITIVE)
    result = svc.set_vote(session, 1, asset.id, VOTE_POSITIVE)  # re-click

    assert result is None
    tally = svc.get_vote_tally(session, asset.id, user_id=1)
    assert tally["positive"] == 0 and tally["score"] == 0
    assert tally["my_vote"] is None
    # Toggling reuses the single row (now inactive) — it is not duplicated.
    assert len(_vote_rows(session, 1, asset.id)) == 1


def test_opposite_value_flips(session):
    asset = _mk_asset(session)
    svc.set_vote(session, 1, asset.id, VOTE_POSITIVE)
    svc.set_vote(session, 1, asset.id, VOTE_NEGATIVE)

    tally = svc.get_vote_tally(session, asset.id, user_id=1)
    assert tally == {"positive": 0, "negative": 1, "score": -1, "my_vote": "NEGATIVE"}
    assert len(_vote_rows(session, 1, asset.id)) == 1


def test_clear_then_revote_reactivates_single_row(session):
    asset = _mk_asset(session)
    svc.set_vote(session, 1, asset.id, VOTE_POSITIVE)
    svc.set_vote(session, 1, asset.id, None)  # clear
    assert svc.get_vote_tally(session, asset.id, user_id=1)["my_vote"] is None

    svc.set_vote(session, 1, asset.id, VOTE_POSITIVE)  # re-vote
    tally = svc.get_vote_tally(session, asset.id, user_id=1)
    assert tally["positive"] == 1 and tally["my_vote"] == "POSITIVE"
    # Reactivated, not duplicated.
    assert len(_vote_rows(session, 1, asset.id)) == 1


def test_tally_aggregates_multiple_users(session):
    asset = _mk_asset(session)
    svc.set_vote(session, 1, asset.id, VOTE_POSITIVE)
    svc.set_vote(session, 2, asset.id, VOTE_POSITIVE)
    svc.set_vote(session, 3, asset.id, VOTE_NEGATIVE)

    tally = svc.get_vote_tally(session, asset.id)
    assert tally == {"positive": 2, "negative": 1, "score": 1, "my_vote": None}


def test_invalid_vote_value_raises(session):
    asset = _mk_asset(session)
    try:
        svc.set_vote(session, 1, asset.id, "MAYBE")
    except ValueError:
        return
    raise AssertionError("Expected ValueError for an invalid vote value")


def test_count_votes_excludes_inactive(session):
    asset = _mk_asset(session)
    svc.set_vote(session, 1, asset.id, VOTE_POSITIVE)
    svc.set_vote(session, 1, asset.id, None)  # logical delete
    assert svc.count_votes(session, asset.id) == {
        "positive": 0, "negative": 0, "score": 0}


# --- Error hardening: a DB-constraint error is a 409, never a raw 500 ------

def test_set_vote_rolls_back_and_reraises_on_integrity_error(session, monkeypatch):
    """The service rolls back and re-raises IntegrityError so the route can map
    it to a 409 (instead of leaving a poisoned session that 500s)."""
    asset = _mk_asset(session)

    rolled_back = {"called": False}
    real_rollback = session.rollback

    def boom():
        raise IntegrityError("INSERT", {}, Exception("constraint violation"))

    def track_rollback():
        rolled_back["called"] = True
        return real_rollback()

    monkeypatch.setattr(session, "commit", boom)
    monkeypatch.setattr(session, "rollback", track_rollback)

    with pytest.raises(IntegrityError):
        svc.set_vote(session, 1, asset.id, VOTE_POSITIVE)
    assert rolled_back["called"] is True


def test_set_vote_route_maps_integrity_error_to_409(session, client, monkeypatch):
    """POST /api/actions/votes returns 409 (not 500) when the write hits a
    DB-constraint violation. Regression for the raw-500 on vote."""
    asset = _mk_asset(session)

    # Bypass RBAC with a superuser stand-in (require_privilege short-circuits).
    app.dependency_overrides[current_active_user] = lambda: SimpleNamespace(
        id=1, username="tester", profile="ADMINISTRATOR",
        is_superuser=True, is_active=True,
    )

    def raiser(*args, **kwargs):
        raise IntegrityError("INSERT", {}, Exception("duplicate vote"))

    monkeypatch.setattr(svc, "set_vote", raiser)

    r = client.post(
        "/api/actions/votes",
        json={"user_id": 1, "asset": asset.id, "content": "POSITIVE"},
    )
    assert r.status_code == 409
    assert "conflict" in r.json()["detail"].lower()


# --- Route contract --------------------------------------------------------

def test_vote_tally_requires_auth(client):
    r = client.get("/api/actions/votes/asset/1")
    assert r.status_code in (401, 403)


def test_set_vote_requires_auth(client):
    r = client.post("/api/actions/votes",
                    json={"user_id": 1, "asset": 1, "content": "POSITIVE"})
    assert r.status_code in (401, 403)


def test_clear_vote_requires_auth(client):
    r = client.delete("/api/actions/votes/1/1")
    assert r.status_code in (401, 403)


def test_vote_routes_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/actions/votes/asset/{asset_id}" in paths
    assert "/api/actions/votes" in paths
    assert "/api/actions/votes/{user_id}/{asset_id}" in paths
