"""Modify/resubmit tests (HU-Modify) — Constitution Principle II/III.

After a reviewer requests changes (asset → FEEDBACK + a MODIFICATION/ASSIGNED
action for the proposer), the proposer edits the asset + its characterizations and
resubmits. ``modify_service.resubmit_asset`` is one transaction that updates the
asset + characterizations, closes the proposer's MODIFICATION assignment
(MODIFICATION/FINISHED), flips the status back to PROPOSED, and re-arms the
original reviewer (REVIEW/ASSIGNED). These tests drive a proposed asset through
``review_service`` ("changes") and then exercise ``modify_service`` + the
``/api/assets/{id}/resubmit`` route.
"""

from types import SimpleNamespace

import pytest

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import propose_service as propose_svc
from app.lib.internal import review_service as review_svc
from app.lib.internal import modify_service as svc
from app.lib.internal import actions_service
from app.lib.internal.models import Asset, Action, Characterization, ProposeRequest, ModifyRequest
from app.taxo.internal.models import Category, Specification
from app.admin.internal.models import User
from sqlmodel import select


def _mk_category(session, code="PROMPTS", name="Prompts"):
    session.add(Category(code=code, name=name))
    session.commit()


def _mk_spec(session, category, feature, default_value=None):
    session.add(Specification(category=category, feature=feature, default_value=default_value))
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


PROPOSER_ID = 42


def _proposer(uid=PROPOSER_ID):
    """A proposer principal — the service only reads ``.id``."""
    return SimpleNamespace(id=uid, username="prop", profile="COLLABORATOR",
                           is_superuser=False, is_active=True)


def _superuser(uid=1):
    return SimpleNamespace(id=uid, username="prop", profile="ADMINISTRATOR",
                           is_superuser=True, is_active=True)


def _propose(session, reviewer, proposer_id=PROPOSER_ID):
    return propose_svc.propose_asset(
        session, proposer_id=proposer_id,
        data=ProposeRequest(name="My Prompt", category="PROMPTS", reviewer_id=reviewer.id),
    )


def _request_changes(session, reviewer, asset_id, feedback="Please fix the overview"):
    review_svc.review_asset(session, reviewer, asset_id, "changes", feedback=feedback)


def _latest_status(session, asset_id, user_id, type):
    rows = session.exec(
        select(Action).where(
            Action.asset == asset_id, Action.user_id == user_id, Action.type == type,
        ).order_by(Action.id)
    ).all()
    return rows[-1].workflow_status if rows else None


# --- Service: the resubmit transaction --------------------------------------

def test_resubmit_updates_asset_and_chars_and_rearms_reviewer(session):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    _request_changes(session, reviewer, asset.id)
    assert session.get(Asset, asset.id).status == "FEEDBACK"

    updated = svc.resubmit_asset(
        session, _proposer(), asset.id,
        ModifyRequest(name="Refined Prompt", description="now better",
                      values={"OVERVIEW": "updated overview"}),
    )

    # 1. asset back to PROPOSED, editable fields applied
    assert updated.status == "PROPOSED"
    assert updated.name == "Refined Prompt"
    assert updated.description == "now better"
    # 2. characterization updated in place
    char = session.exec(
        select(Characterization).where(
            Characterization.asset == asset.id, Characterization.feature == "OVERVIEW")
    ).first()
    assert char.value == "updated overview"
    # 3. proposer's MODIFICATION assignment closed; reviewer re-armed
    assert _latest_status(session, asset.id, PROPOSER_ID, "MODIFICATION") == "FINISHED"
    assert _latest_status(session, asset.id, reviewer.id, "REVIEW") == "ASSIGNED"


def test_resubmit_notifications_flip(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    _request_changes(session, reviewer, asset.id)
    # before: proposer has the MODIFICATION notification, reviewer has none
    assert any(n["type"] == "MODIFICATION" for n in actions_service.list_notifications(session, PROPOSER_ID))

    svc.resubmit_asset(session, _proposer(), asset.id, ModifyRequest(name="X"))

    # after: proposer's MODIFICATION is gone; reviewer has a fresh unread REVIEW
    assert actions_service.list_notifications(session, PROPOSER_ID) == []
    rev_notifs = actions_service.list_notifications(session, reviewer.id)
    assert any(n["type"] == "REVIEW" and n["unread"] for n in rev_notifs)


def test_resubmit_missing_char_is_created(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)  # no specs → no characterizations created
    _request_changes(session, reviewer, asset.id)

    svc.resubmit_asset(session, _proposer(), asset.id,
                       ModifyRequest(values={"OVERVIEW": "brand new"}))
    char = session.exec(
        select(Characterization).where(
            Characterization.asset == asset.id, Characterization.feature == "OVERVIEW")
    ).first()
    assert char is not None and char.value == "brand new"


def test_resubmit_then_review_approve_publishes(session):
    """The FEEDBACK→PROPOSED flip must re-enable HU-Review (full loop)."""
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    _request_changes(session, reviewer, asset.id)
    svc.resubmit_asset(session, _proposer(), asset.id, ModifyRequest(name="Y"))

    approved = review_svc.review_asset(session, reviewer, asset.id, "approve")
    assert approved.status == "PUBLISHED"


# --- Service: authorization + guards ---------------------------------------

def test_resubmit_by_non_proposer_forbidden(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    _request_changes(session, reviewer, asset.id)

    # someone who doesn't hold the MODIFICATION assignment
    with pytest.raises(svc.ModifyForbidden):
        svc.resubmit_asset(session, _proposer(uid=99), asset.id, ModifyRequest(name="Z"))


def test_resubmit_not_in_feedback_conflict(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    _request_changes(session, reviewer, asset.id)
    # force the asset out of FEEDBACK while the MODIFICATION assignment is still open
    asset.status = "PROPOSED"
    session.add(asset)
    session.commit()

    with pytest.raises(svc.ModifyConflict):
        svc.resubmit_asset(session, _proposer(), asset.id, ModifyRequest(name="Z"))


def test_resubmit_missing_asset_valueerror(session):
    _mk_category(session)
    with pytest.raises(ValueError):
        svc.resubmit_asset(session, _proposer(), 9999, ModifyRequest(name="Z"))


# --- Route contract ---------------------------------------------------------

def test_resubmit_route_ok(session, client):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer, proposer_id=1)  # proposer == the superuser override id
    _request_changes(session, reviewer, asset.id)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post(f"/api/assets/{asset.id}/resubmit",
                    json={"name": "Refined", "values": {}})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "PROPOSED"
    assert r.json()["data"]["name"] == "Refined"


def test_resubmit_route_non_proposer_403(session, client):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)  # proposer is 42, not the superuser (1)
    _request_changes(session, reviewer, asset.id)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post(f"/api/assets/{asset.id}/resubmit", json={"name": "Refined"})
    assert r.status_code == 403
