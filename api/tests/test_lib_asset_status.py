"""Asset Management status policy + its history trail — Constitution III.

Asset Management (`/lib/assets`) is the manager's surface, not the review
workflow. Exactly two status moves are legitimate there and both must leave a
trace on the ``actions`` substrate so the asset's history shows them:

  * create → PUBLISHED only, logged PUBLICATION/HANDLED,
  * edit   → PUBLISHED → DEPRECATED only, logged DEPRECATION/HANDLED.

Anything else is a 400 (including from a version save, which edits the same
asset row). The review workflow's own transitions go through
propose/review/modify_service and are deliberately NOT subject to this policy.
"""

from types import SimpleNamespace

import pytest
from sqlmodel import select

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import actions_service
from app.lib.internal import status_service as svc
from app.lib.internal import version_service
from app.lib.internal.models import Action, Asset, VersionRequest
from app.taxo.internal.models import Category


def _superuser(uid=1):
    return SimpleNamespace(id=uid, username="root", profile="ADMINISTRATOR",
                           unit="HQ", is_superuser=True, is_active=True)


def _override(user=None):
    app.dependency_overrides[current_active_user] = lambda: user or _superuser()


def _mk_asset(session, status="PUBLISHED", name="A"):
    a = Asset(name=name, status=status)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _actions(session, asset_id, type_=None):
    rows = session.exec(
        select(Action).where(Action.asset == asset_id).order_by(Action.id)).all()
    return [r for r in rows if type_ is None or r.type == type_]


# --- Service: the create rule -----------------------------------------------

def test_create_status_must_be_published():
    assert svc.validate_create_status("PUBLISHED") == "PUBLICATION"


def test_create_status_tolerates_the_sort_prefix():
    # Legacy/seeded rows may carry the list_items `N-` prefix.
    assert svc.validate_create_status("3-published") == "PUBLICATION"


@pytest.mark.parametrize("status", ["PROPOSED", "FEEDBACK", "REJECTED", "DEPRECATED", "", None])
def test_create_status_rejects_everything_else(status):
    with pytest.raises(svc.StatusTransitionForbidden):
        svc.validate_create_status(status)


# --- Service: the edit rule --------------------------------------------------

def test_unchanged_status_logs_nothing():
    assert svc.validate_transition("PUBLISHED", "PUBLISHED") is None
    assert svc.validate_transition("PROPOSED", "PROPOSED") is None
    # A blank/absent new status is "not changing it", not an illegal move.
    assert svc.validate_transition("PROPOSED", None) is None


def test_publish_to_deprecate_is_the_only_move():
    assert svc.validate_transition("PUBLISHED", "DEPRECATED") == "DEPRECATION"


@pytest.mark.parametrize("current,new", [
    ("PUBLISHED", "REJECTED"),
    ("PUBLISHED", "PROPOSED"),
    ("DEPRECATED", "PUBLISHED"),   # deprecation is terminal here
    ("PROPOSED", "PUBLISHED"),     # that is the reviewer's call, not a manager's
    ("FEEDBACK", "DEPRECATED"),
    ("REJECTED", "PUBLISHED"),
])
def test_every_other_transition_is_refused(current, new):
    with pytest.raises(svc.StatusTransitionForbidden):
        svc.validate_transition(current, new)


def test_status_transition_forbidden_is_a_value_error():
    # Routes that already map ValueError → 400 keep working unchanged.
    assert issubclass(svc.StatusTransitionForbidden, ValueError)


# --- Route: create -----------------------------------------------------------

def test_create_published_logs_a_publication_action(session, client):
    _override()
    r = client.post("/api/assets/", json={"name": "New", "status": "PUBLISHED"})
    assert r.status_code == 201
    asset_id = r.json()["data"]["id"]

    logged = _actions(session, asset_id, "PUBLICATION")
    assert len(logged) == 1
    assert logged[0].workflow_status == "HANDLED"
    assert logged[0].user_id == 1


def test_create_with_any_other_status_is_400_and_creates_nothing(session, client):
    _override()
    r = client.post("/api/assets/", json={"name": "Nope", "status": "PROPOSED"})
    assert r.status_code == 400
    assert session.exec(select(Asset).where(Asset.name == "Nope")).first() is None


# --- Route: update -----------------------------------------------------------

def test_deprecating_a_published_asset_logs_a_deprecation(session, client):
    _override()
    asset = _mk_asset(session)
    r = client.put(f"/api/assets/{asset.id}", json={"status": "DEPRECATED"})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "DEPRECATED"

    logged = _actions(session, asset.id, "DEPRECATION")
    assert len(logged) == 1 and logged[0].workflow_status == "HANDLED"


def test_forbidden_transition_is_400_and_leaves_the_status_alone(session, client):
    _override()
    asset = _mk_asset(session)
    r = client.put(f"/api/assets/{asset.id}", json={"status": "REJECTED"})
    assert r.status_code == 400
    session.refresh(asset)
    assert asset.status == "PUBLISHED"
    assert _actions(session, asset.id) == []


def test_review_workflow_statuses_cannot_be_touched_here(session, client):
    _override()
    asset = _mk_asset(session, status="PROPOSED", name="Under review")
    r = client.put(f"/api/assets/{asset.id}", json={"status": "PUBLISHED"})
    assert r.status_code == 400
    session.refresh(asset)
    assert asset.status == "PROPOSED"


def test_editing_other_fields_resends_the_same_status_without_logging(session, client):
    """The edit form always submits the whole core-field set — an unchanged
    status must stay a plain no-op, not a refused transition or a spurious
    history entry."""
    _override()
    asset = _mk_asset(session, status="PROPOSED", name="Under review")
    r = client.put(f"/api/assets/{asset.id}",
                   json={"name": "Renamed", "status": "PROPOSED"})
    assert r.status_code == 200
    session.refresh(asset)
    assert asset.name == "Renamed"
    assert _actions(session, asset.id) == []


# --- The same rule on the version-save path ---------------------------------

def test_version_save_can_deprecate_and_logs_it(session):
    session.add(Category(code="PROMPTS", name="Prompts"))
    session.commit()
    asset = _mk_asset(session)
    version_service.create_version(
        session, _superuser(), asset.id,
        VersionRequest(change_type="patch", status="DEPRECATED"))
    session.refresh(asset)
    assert asset.status == "DEPRECATED" and asset.current_version == "1.0.1"
    assert len(_actions(session, asset.id, "DEPRECATION")) == 1


def test_version_save_cannot_smuggle_a_forbidden_status(session):
    asset = _mk_asset(session, status="PROPOSED")
    with pytest.raises(svc.StatusTransitionForbidden):
        version_service.create_version(
            session, _superuser(), asset.id,
            VersionRequest(change_type="patch", status="PUBLISHED"))
    session.refresh(asset)
    assert asset.status == "PROPOSED" and asset.current_version == "1.0.0"


# --- History readback --------------------------------------------------------

def test_both_transitions_read_back_in_the_asset_history(session, client):
    _override()
    created = client.post("/api/assets/", json={"name": "H", "status": "PUBLISHED"})
    asset_id = created.json()["data"]["id"]
    client.put(f"/api/assets/{asset_id}", json={"status": "DEPRECATED"})

    summaries = [e["summary"] for e in actions_service.get_asset_history(session, asset_id)]
    assert "published the asset" in summaries
    assert "deprecated the asset" in summaries


def test_a_blank_status_never_clears_the_stored_one(session, client):
    """The form always submits `status`; a value that resolves to "no change"
    (blank, or the same code differently spelled) must be dropped, not written
    back over the stored status."""
    _override()
    asset = _mk_asset(session, status="PUBLISHED")
    r = client.put(f"/api/assets/{asset.id}", json={"name": "Renamed", "status": ""})
    assert r.status_code == 200
    session.refresh(asset)
    assert asset.status == "PUBLISHED" and asset.name == "Renamed"
