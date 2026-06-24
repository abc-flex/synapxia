"""Voting tests (HU-LI05) — Constitution Principle II/III.

Votes are ``actions`` rows of type VOTE (content POSITIVE/NEGATIVE) — no new
table. Two layers are covered:

1. Asset Action Service logic, exercised directly against the in-memory SQLite
   `session` fixture (no auth needed; user_id is a plain int — SQLite does not
   enforce the users FK).
2. Route contract: the `/api/actions/votes/*` endpoints must be auth-gated and
   advertised in the OpenAPI schema.
"""

from sqlmodel import select

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
