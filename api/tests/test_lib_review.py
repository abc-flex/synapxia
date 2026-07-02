"""Review tests (HU-Review) — Constitution Principle II/III.

A reviewer's decision on a PROPOSED asset is a single transaction that closes the
reviewer's REVIEW assignment (REVIEW/FINISHED), flips the asset status
(PUBLISHED / REJECTED / FEEDBACK), and raises a proposer-directed notification
(PUBLICATION / REJECTION / MODIFICATION, ASSIGNED) carrying the feedback. These
tests build a proposed asset via ``propose_service`` and then exercise
``review_service`` + the ``/api/assets/{id}/review`` route.
"""

from types import SimpleNamespace

import pytest

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import propose_service as propose_svc
from app.lib.internal import review_service as svc
from app.lib.internal import actions_service
from app.lib.internal.models import Asset, Action, ProposeRequest
from app.taxo.internal.models import Category
from app.admin.internal.models import User
from sqlmodel import select


def _mk_category(session, code="PROMPTS", name="Prompts"):
    session.add(Category(code=code, name=name))
    session.commit()


def _mk_user(session, id, username, profile="ADMINISTRATIVE", is_active=True,
             is_superuser=False):
    u = User(
        id=id, username=username, email=f"{username}@x.co",
        password_hash="x", first_name="Rev", last_name="Iewer",
        profile=profile, unit="HQ", is_active=is_active, is_superuser=is_superuser,
    )
    session.add(u)
    session.commit()
    return u


def _superuser(uid=1):
    return SimpleNamespace(
        id=uid, username="rev", profile="ADMINISTRATOR",
        is_superuser=True, is_active=True,
    )


PROPOSER_ID = 42


def _propose(session, reviewer):
    """Propose an asset assigned to ``reviewer``; return the PROPOSED asset."""
    return propose_svc.propose_asset(
        session, proposer_id=PROPOSER_ID,
        data=ProposeRequest(name="My Prompt", category="PROMPTS", reviewer_id=reviewer.id),
    )


def _latest_review_status(session, asset_id, user_id):
    rows = session.exec(
        select(Action).where(
            Action.asset == asset_id, Action.user_id == user_id, Action.type == "REVIEW",
        ).order_by(Action.id)
    ).all()
    return rows[-1].workflow_status if rows else None


# --- Service: decisions -----------------------------------------------------

@pytest.mark.parametrize("decision,status,proposer_type", [
    ("approve", "PUBLISHED", "PUBLICATION"),
    ("reject", "REJECTED", "REJECTION"),
    ("changes", "FEEDBACK", "MODIFICATION"),
])
def test_review_decision_flips_status_and_notifies_proposer(session, decision, status, proposer_type):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)

    updated = svc.review_asset(session, reviewer, asset.id, decision, feedback="Please note this")

    # 1. asset status flipped
    assert updated.status == status
    # 2. the reviewer's REVIEW assignment is closed (latest row FINISHED)
    assert _latest_review_status(session, asset.id, reviewer.id) == "FINISHED"
    # 3. the proposer got a notification of the right type carrying the feedback
    proposer_actions = session.exec(
        select(Action).where(
            Action.asset == asset.id, Action.user_id == PROPOSER_ID, Action.type == proposer_type,
        )
    ).all()
    assert len(proposer_actions) == 1
    assert proposer_actions[0].workflow_status == "ASSIGNED"
    assert proposer_actions[0].content == "Please note this"

    # 4. it surfaces in the proposer's notifications; the reviewer's is gone
    proposer_notifs = actions_service.list_notifications(session, PROPOSER_ID)
    assert any(n["type"] == proposer_type and n["unread"] for n in proposer_notifs)
    assert actions_service.list_notifications(session, reviewer.id) == []


def test_review_feedback_optional_blank_stored_as_none(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)

    svc.review_asset(session, reviewer, asset.id, "approve", feedback="   ")
    pub = session.exec(
        select(Action).where(Action.asset == asset.id, Action.type == "PUBLICATION")
    ).first()
    assert pub.content is None


# --- Service: authorization + guards ---------------------------------------

def test_review_by_non_assigned_eligible_user_forbidden(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    other = _mk_user(session, 8, "other", profile="ADMINISTRATIVE")  # eligible but not assigned
    asset = _propose(session, reviewer)

    with pytest.raises(svc.ReviewForbidden):
        svc.review_asset(session, other, asset.id, "approve")


def test_review_by_ineligible_user_forbidden(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    collab = _mk_user(session, 9, "collab", profile="COLLABORATOR")
    asset = _propose(session, reviewer)

    with pytest.raises(svc.ReviewForbidden):
        svc.review_asset(session, collab, asset.id, "approve")


def test_review_already_decided_conflict(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)

    svc.review_asset(session, reviewer, asset.id, "approve")
    with pytest.raises(svc.ReviewConflict):
        svc.review_asset(session, reviewer, asset.id, "reject")


def test_review_invalid_decision(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)

    with pytest.raises(ValueError):
        svc.review_asset(session, reviewer, asset.id, "bogus")


# --- Route contract ---------------------------------------------------------

def test_review_route_approves(session, client):
    _mk_category(session)
    reviewer = _mk_user(session, 1, "rev", profile="ADMINISTRATOR", is_superuser=True)
    asset = _propose(session, reviewer)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post(f"/api/assets/{asset.id}/review",
                    json={"decision": "approve", "feedback": "ok"})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "PUBLISHED"


def test_review_route_non_assigned_403(session, client):
    _mk_category(session)
    _mk_user(session, 7, "rev")           # the assigned reviewer
    reviewer_used = session.get(User, 7)
    asset = _propose(session, reviewer_used)
    # current user is superuser id=1, who is NOT the assigned reviewer (7)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post(f"/api/assets/{asset.id}/review", json={"decision": "approve"})
    assert r.status_code == 403
