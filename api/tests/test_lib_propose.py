"""Propose tests (HU-Propose) — Constitution Principle II/III.

Proposing an asset is the review-workflow entry point: a single transaction that
creates the asset (PROPOSED) + one characterization per category spec + a
PROPOSAL/FINISHED action (proposer) + a REVIEW/ASSIGNED action (reviewer) +
MANAGE asset_permissions for both. The REVIEW/ASSIGNED action is what the
notifications feature (HU-LI11) then surfaces — covered here by an integration
assertion against ``actions_service.list_notifications``.

Service logic runs against the in-memory SQLite ``session`` fixture; route
contract runs through ``client`` with a superuser override.
"""

from types import SimpleNamespace

import pytest

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import propose_service as svc
from app.lib.internal import actions_service
from app.lib.internal.models import (
    Asset, Characterization, Action, AssetPermission, ProposeRequest,
)
from app.taxo.internal.models import Category, Specification
from app.admin.internal.models import User
from sqlmodel import select


def _mk_category(session, code="PROMPTS", name="Prompts"):
    cat = Category(code=code, name=name)
    session.add(cat)
    session.commit()
    return cat


def _mk_spec(session, category, feature, default_value=None):
    spec = Specification(category=category, feature=feature, default_value=default_value)
    session.add(spec)
    session.commit()
    return spec


def _mk_user(session, id, username, profile="ADMINISTRATIVE", is_active=True):
    u = User(
        id=id, username=username, email=f"{username}@x.co",
        password_hash="x", first_name="Rev", last_name="Iewer",
        profile=profile, unit="HQ", is_active=is_active,
    )
    session.add(u)
    session.commit()
    return u


def _superuser(uid=1):
    return SimpleNamespace(
        id=uid, username="proposer", profile="COLLABORATOR",
        is_superuser=True, is_active=True,
    )


def _req(**kw):
    kw.setdefault("name", "My Prompt")
    kw.setdefault("category", "PROMPTS")
    return ProposeRequest(**kw)


# --- Service: the full transaction ----------------------------------------

def test_propose_creates_asset_and_workflow_records(session):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "PLATFORM", default_value="OpenAI")
    _mk_spec(session, "PROMPTS", "SUGGESTED_MODEL", default_value="gpt-4")
    reviewer = _mk_user(session, 7, "rev")

    asset = svc.propose_asset(session, proposer_id=42, data=_req(reviewer_id=reviewer.id))

    # 1. Asset
    assert asset.id is not None and asset.status == "PROPOSED"

    # 2. One characterization per spec, defaults applied
    chars = session.exec(select(Characterization).where(Characterization.asset == asset.id)).all()
    assert {c.feature for c in chars} == {"PLATFORM", "SUGGESTED_MODEL"}
    assert {c.value for c in chars} == {"OpenAI", "gpt-4"}

    # 3 + 4. PROPOSAL/FINISHED (proposer) + REVIEW/ASSIGNED (reviewer)
    actions = session.exec(select(Action).where(Action.asset == asset.id)).all()
    proposal = next(a for a in actions if a.type == "PROPOSAL")
    review = next(a for a in actions if a.type == "REVIEW")
    assert proposal.user_id == 42 and proposal.workflow_status == "FINISHED"
    assert review.user_id == reviewer.id and review.workflow_status == "ASSIGNED"

    # 5. MANAGE permission for proposer + reviewer
    perms = session.exec(select(AssetPermission).where(AssetPermission.asset == asset.id)).all()
    assert all(p.access_level == "MANAGE" and p.target_type == "USER" for p in perms)
    assert {p.target_code for p in perms} == {"42", str(reviewer.id)}


def test_proposal_generates_reviewer_notification(session):
    """End-to-end with Phase 5: the REVIEW/ASSIGNED action shows up as a
    notification for the reviewer."""
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")

    svc.propose_asset(session, proposer_id=42, data=_req(reviewer_id=reviewer.id))

    notifs = actions_service.list_notifications(session, reviewer.id)
    assert len(notifs) == 1
    assert notifs[0]["type"] == "REVIEW"
    assert notifs[0]["workflow_status"] == "ASSIGNED"
    assert notifs[0]["unread"] is True


def test_values_override_spec_default(session):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "PLATFORM", default_value="OpenAI")
    _mk_user(session, 7, "rev")

    asset = svc.propose_asset(
        session, 42, _req(values={"PLATFORM": "Anthropic"}))
    char = session.exec(
        select(Characterization).where(Characterization.asset == asset.id)).first()
    assert char.feature == "PLATFORM" and char.value == "Anthropic"


def test_auto_assigns_first_eligible_reviewer(session):
    _mk_category(session)
    _mk_user(session, 5, "alice")  # ADMINISTRATIVE, lowest id
    _mk_user(session, 9, "bob")

    asset = svc.propose_asset(session, 42, _req())  # no reviewer_id
    review = session.exec(
        select(Action).where(Action.asset == asset.id, Action.type == "REVIEW")).first()
    assert review.user_id == 5


def test_no_chars_when_category_has_no_specs(session):
    _mk_category(session)
    _mk_user(session, 7, "rev")
    asset = svc.propose_asset(session, 42, _req())
    chars = session.exec(select(Characterization).where(Characterization.asset == asset.id)).all()
    assert chars == []


# --- Service: validation + atomicity --------------------------------------

def test_reviewer_must_be_administrative(session):
    _mk_category(session)
    _mk_user(session, 3, "plain", profile="COLLABORATOR")
    with pytest.raises(ValueError):
        svc.propose_asset(session, 42, _req(reviewer_id=3))


def test_no_reviewer_available_raises(session):
    _mk_category(session)  # no ADMINISTRATIVE users
    with pytest.raises(ValueError):
        svc.propose_asset(session, 42, _req())


def test_unknown_category_raises_and_writes_nothing(session):
    _mk_user(session, 7, "rev")
    with pytest.raises(ValueError):
        svc.propose_asset(session, 42, _req(category="NOPE"))
    # Atomicity: validation fails before any write.
    assert session.exec(select(Asset)).all() == []
    assert session.exec(select(Action)).all() == []


def test_empty_name_raises(session):
    _mk_category(session)
    _mk_user(session, 7, "rev")
    with pytest.raises(ValueError):
        svc.propose_asset(session, 42, _req(name="   "))


# --- Route contract --------------------------------------------------------

def test_propose_requires_auth(client):
    r = client.post("/api/assets/propose", json={"name": "x", "category": "PROMPTS"})
    assert r.status_code in (401, 403)


def test_reviewers_requires_auth(client):
    assert client.get("/api/assets/reviewers").status_code in (401, 403)


def test_propose_routes_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/assets/propose" in paths
    assert "/api/assets/reviewers" in paths


def test_reviewers_route_lists_administrative_users(session, client):
    _mk_user(session, 5, "alice")
    _mk_user(session, 6, "bob", profile="COLLABORATOR")  # excluded
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get("/api/assets/reviewers")
    assert r.status_code == 200
    body = r.json()["data"]
    assert [o["value"] for o in body] == [5]


def test_propose_route_creates_proposed_asset(session, client):
    _mk_category(session)
    _mk_user(session, 7, "rev")
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post("/api/assets/propose",
                    json={"name": "My Prompt", "category": "PROMPTS", "reviewer_id": 7})
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["status"] == "PROPOSED" and body["name"] == "My Prompt"


def test_propose_route_unknown_category_400(session, client):
    _mk_user(session, 7, "rev")
    app.dependency_overrides[current_active_user] = _superuser
    r = client.post("/api/assets/propose", json={"name": "x", "category": "NOPE"})
    assert r.status_code == 400
