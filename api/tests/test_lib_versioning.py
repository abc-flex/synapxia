"""Asset versioning tests (HU-LI09, versioning half) — Constitution III.

Saving an edit to an existing asset creates a NEW VERSION on the same asset
row: ``version_service.create_version`` bumps ``assets.current_version`` by the
caller-chosen change type (major/minor/patch), applies the core edits, writes
the new version's characterization rows under the bumped ``version_label``
(prior generations stay untouched = history), and logs a VERSIONING/FINISHED
action. The (asset, feature)-keyed characterization CRUD must only ever see the
CURRENT version's rows. These tests drive a proposed asset through the service
and the ``POST /api/assets/{id}/versions`` route.
"""

from types import SimpleNamespace

import pytest

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import propose_service as propose_svc
from app.lib.internal import version_service as svc
from app.lib.internal.models import Asset, Action, Characterization, ProposeRequest, VersionRequest
from app.taxo.internal.models import Category, Feature, Specification
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


def _superuser(uid=1):
    return SimpleNamespace(id=uid, username="root", profile="ADMINISTRATOR",
                           is_superuser=True, is_active=True)


def _propose(session, reviewer, proposer_id=1, **overrides):
    return propose_svc.propose_asset(
        session, proposer_id=proposer_id,
        data=ProposeRequest(name="My Prompt", category="PROMPTS",
                            reviewer_id=reviewer.id, **overrides),
    )


def _chars(session, asset_id, label):
    return {
        c.feature: c
        for c in session.exec(
            select(Characterization).where(
                Characterization.asset == asset_id,
                Characterization.version_label == label,
            )
        ).all()
    }


# --- bump_label math ---------------------------------------------------------

def test_bump_label_math():
    assert svc.bump_label("1.2.3", "patch") == "1.2.4"
    assert svc.bump_label("1.2.3", "minor") == "1.3.0"
    assert svc.bump_label("1.2.3", "major") == "2.0.0"


def test_bump_label_tolerates_missing_or_malformed():
    # NULL / garbage labels are treated as the 1.0.0 base.
    assert svc.bump_label(None, "patch") == "1.0.1"
    assert svc.bump_label("garbage", "minor") == "1.1.0"
    assert svc.bump_label("  1.0.0  ", "major") == "2.0.0"


def test_bump_label_rejects_bad_change_type():
    with pytest.raises(ValueError):
        svc.bump_label("1.0.0", "huge")


# --- Service: the versioning transaction -------------------------------------

def test_create_version_core_only_copies_chars_forward(session):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    assert asset.current_version == "1.0.0"

    updated = svc.create_version(
        session, _superuser(), asset.id,
        VersionRequest(change_type="minor", name="Renamed Prompt"),
    )

    # 1. label bumped + core edit applied
    assert updated.current_version == "1.1.0"
    assert updated.name == "Renamed Prompt"
    assert updated.updated_at is not None
    # 2. characterizations copied unchanged to the new label; old label intact
    assert _chars(session, asset.id, "1.1.0")["OVERVIEW"].value == "orig overview"
    assert _chars(session, asset.id, "1.0.0")["OVERVIEW"].value == "orig overview"
    # 3. one VERSIONING/FINISHED action logged with both labels in the detail
    actions = session.exec(
        select(Action).where(Action.asset == asset.id, Action.type == "VERSIONING")
    ).all()
    assert len(actions) == 1
    assert actions[0].workflow_status == "FINISHED"
    assert actions[0].content == "1.1.0"
    assert "1.0.0" in (actions[0].detail or "")


def test_create_version_values_is_the_full_desired_set(session):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    _mk_spec(session, "PROMPTS", "TOOLS", default_value="orig tools")
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)

    svc.create_version(
        session, _superuser(), asset.id,
        VersionRequest(change_type="patch", values={"OVERVIEW": "v2 overview"}),
    )

    # New label: OVERVIEW edited, TOOLS omitted → dropped.
    new_chars = _chars(session, asset.id, "1.0.1")
    assert new_chars["OVERVIEW"].value == "v2 overview"
    assert "TOOLS" not in new_chars
    # Old label keeps its full untouched set.
    old_chars = _chars(session, asset.id, "1.0.0")
    assert old_chars["OVERVIEW"].value == "orig overview"
    assert old_chars["TOOLS"].value == "orig tools"


def test_create_version_blank_value_drops_feature(session):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)

    svc.create_version(
        session, _superuser(), asset.id,
        VersionRequest(change_type="patch", values={"OVERVIEW": "   "}),
    )
    assert _chars(session, asset.id, "1.0.1") == {}
    assert _chars(session, asset.id, "1.0.0")["OVERVIEW"].value == "orig overview"


def test_create_version_successive_bumps_chain(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)

    svc.create_version(session, _superuser(), asset.id, VersionRequest(change_type="patch"))
    svc.create_version(session, _superuser(), asset.id, VersionRequest(change_type="minor"))
    svc.create_version(session, _superuser(), asset.id, VersionRequest(change_type="major"))
    assert session.get(Asset, asset.id).current_version == "2.0.0"


def test_version_request_defaults_to_patch(session):
    # Omitting change_type must default to a patch bump (1.0.0 -> 1.0.1).
    assert VersionRequest().change_type == "patch"
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    assert asset.current_version == "1.0.0"

    updated = svc.create_version(
        session, _superuser(), asset.id, VersionRequest(values=None),
    )
    assert updated.current_version == "1.0.1"


def test_create_version_guards(session):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)

    with pytest.raises(ValueError):
        svc.create_version(session, _superuser(), 9999,
                           VersionRequest(change_type="patch"))
    with pytest.raises(ValueError):
        svc.create_version(session, _superuser(), asset.id,
                           VersionRequest(change_type="huge"))
    with pytest.raises(ValueError):
        svc.create_version(session, _superuser(), asset.id,
                           VersionRequest(change_type="patch", category="NOPE"))


def test_propose_starts_at_default_version(session):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)

    assert asset.current_version == "1.0.0"
    assert _chars(session, asset.id, "1.0.0")["OVERVIEW"].value == "orig overview"


# --- Characterization CRUD stays scoped to the CURRENT version ---------------

def test_char_list_returns_only_current_version(session, client):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    svc.create_version(session, _superuser(), asset.id,
                       VersionRequest(change_type="minor", values={"OVERVIEW": "v2"}))
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get("/api/characterizations/?limit=1000")
    assert r.status_code == 200
    rows = [c for c in r.json()["data"] if c["asset"] == asset.id]
    # one generation only — the current one
    assert len(rows) == 1
    assert rows[0]["value"] == "v2"
    assert rows[0]["version_label"] == "1.1.0"


def test_char_update_targets_current_version_row(session, client):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    svc.create_version(session, _superuser(), asset.id, VersionRequest(change_type="minor"))
    app.dependency_overrides[current_active_user] = _superuser

    r = client.put(f"/api/characterizations/{asset.id}/OVERVIEW",
                   json={"value": "edited in place"})
    assert r.status_code == 200
    # current generation edited; prior generation untouched
    assert _chars(session, asset.id, "1.1.0")["OVERVIEW"].value == "edited in place"
    assert _chars(session, asset.id, "1.0.0")["OVERVIEW"].value == "orig overview"


def test_char_create_lands_on_current_version(session, client):
    _mk_category(session)
    # The create route validates the Feature row exists (unlike the services).
    session.add(Feature(code="OVERVIEW", name="Overview"))
    session.commit()
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)  # no specs → no chars
    svc.create_version(session, _superuser(), asset.id, VersionRequest(change_type="major"))
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post("/api/characterizations/",
                    json={"asset": asset.id, "feature": "OVERVIEW", "value": "fresh"})
    assert r.status_code == 201
    assert r.json()["data"]["version_label"] == "2.0.0"


# --- Route contract ----------------------------------------------------------

def test_versions_route_ok(session, client):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post(f"/api/assets/{asset.id}/versions",
                    json={"change_type": "major", "name": "V2 Prompt"})
    assert r.status_code == 200
    assert r.json()["data"]["current_version"] == "2.0.0"
    assert r.json()["data"]["name"] == "V2 Prompt"


def test_versions_route_missing_asset_404(session, client):
    _mk_category(session)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post("/api/assets/9999/versions", json={"change_type": "patch"})
    assert r.status_code == 404


def test_versions_route_bad_change_type_400(session, client):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post(f"/api/assets/{asset.id}/versions", json={"change_type": "huge"})
    assert r.status_code == 400


def test_versions_route_in_openapi(client):
    r = client.get("/openapi.json")
    assert "/api/assets/{asset_id}/versions" in r.json()["paths"]


# --- Version history (read side) ---------------------------------------------

def test_list_versions_service(session):
    """list_versions returns one entry per label, newest-first, is_current on
    the live label, and change_type/actor enriched from the VERSIONING action
    for bumps (null for the initial 1.0.0)."""
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    reviewer = _mk_user(session, 7, "rev")
    # The versioner must be a real User row so the actor lookup resolves it.
    versioner = _mk_user(session, 1, "root", is_superuser=True)
    asset = _propose(session, reviewer, proposer_id=reviewer.id)

    svc.create_version(session, versioner, asset.id, VersionRequest(change_type="minor"))
    svc.create_version(session, versioner, asset.id, VersionRequest(change_type="major"))

    versions = svc.list_versions(session, asset.id)
    labels = [v.version_label for v in versions]
    assert labels == ["2.0.0", "1.1.0", "1.0.0"]  # newest-first by date

    top = versions[0]
    assert top.version_label == "2.0.0"
    assert top.is_current is True
    assert top.change_type == "major"
    assert top.actor == "root"

    initial = versions[-1]
    assert initial.version_label == "1.0.0"
    assert initial.is_current is False
    assert initial.change_type is None   # no VERSIONING action for the initial
    assert initial.actor is None

    assert sum(1 for v in versions if v.is_current) == 1


def test_list_versions_route_ok(session, client):
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    svc.create_version(session, _superuser(), asset.id, VersionRequest(change_type="patch"))
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get(f"/api/assets/{asset.id}/versions")
    assert r.status_code == 200
    data = r.json()["data"]
    assert [v["version_label"] for v in data] == ["1.0.1", "1.0.0"]
    assert data[0]["is_current"] is True


def test_list_versions_route_missing_asset_404(session, client):
    app.dependency_overrides[current_active_user] = _superuser
    r = client.get("/api/assets/9999/versions")
    assert r.status_code == 404


def test_version_characterizations_route_returns_that_snapshot(session, client):
    """The snapshot endpoint returns exactly the requested label's rows, and a
    later version's edit does not leak back into an earlier version's snapshot."""
    _mk_category(session)
    _mk_spec(session, "PROMPTS", "OVERVIEW", default_value="orig overview")
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    # Bump to 1.1.0 with an edited OVERVIEW.
    svc.create_version(session, _superuser(), asset.id,
                       VersionRequest(change_type="minor", values={"OVERVIEW": "edited overview"}))
    app.dependency_overrides[current_active_user] = _superuser

    # Old version snapshot keeps the original value.
    r_old = client.get(f"/api/assets/{asset.id}/versions/1.0.0/characterizations")
    assert r_old.status_code == 200
    old = r_old.json()["data"]
    assert {c["feature"]: c["value"] for c in old}["OVERVIEW"] == "orig overview"
    assert all(c["version_label"] == "1.0.0" for c in old)

    # Current version snapshot has the edit.
    r_new = client.get(f"/api/assets/{asset.id}/versions/1.1.0/characterizations")
    assert {c["feature"]: c["value"] for c in r_new.json()["data"]}["OVERVIEW"] == "edited overview"


def test_version_characterizations_unknown_label_empty(session, client):
    _mk_category(session)
    reviewer = _mk_user(session, 7, "rev")
    asset = _propose(session, reviewer)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get(f"/api/assets/{asset.id}/versions/9.9.9/characterizations")
    assert r.status_code == 200
    assert r.json()["data"] == []


def test_version_history_routes_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/assets/{asset_id}/versions" in paths
    assert "/api/assets/{asset_id}/versions/{version_label}/characterizations" in paths
