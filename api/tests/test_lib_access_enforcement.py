"""Per-asset permission ENFORCEMENT tests (HU-LI08) — Constitution III.

The `asset_permissions` substrate is now enforced: `GET /api/assets/with-access`
returns only the assets the caller can access (no grant = hidden; superusers see
all) with the caller's effective level in `my_access`; every per-asset write
(asset PUT/DELETE/versions, characterization/relation/permission writes)
requires a MANAGE grant (or superuser) via
`permissions_service.require_asset_manage`; and plain asset create auto-grants
the creator USER/MANAGE so new assets never orphan under the strict rule.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlmodel import select

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import permissions_service as svc
from app.lib.internal.models import Asset, AssetPermission, Characterization
from app.admin.internal.models import Privilege
from app.collab.internal.models import Assignment, Project
from app.taxo.internal.models import Feature

NOW = datetime.utcnow()
PAST = NOW - timedelta(days=1)
FUTURE = NOW + timedelta(days=1)

COLLAB = "COLLABORATOR"


def _user(id=1, unit="GEN_AI", superuser=False, profile=COLLAB):
    return SimpleNamespace(
        id=id, username=f"u{id}", unit=unit, profile=profile,
        is_superuser=superuser, is_active=True,
    )


def _superuser(uid=99):
    return _user(id=uid, superuser=True, profile="ADMINISTRATOR")


def _mk_asset(session, name="A"):
    a = Asset(name=name, status="PUBLISHED")
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _mk_perm(session, asset, target_type, target_code, *, access_level="VIEW",
             is_active=True, valid_from=None, valid_to=None):
    p = AssetPermission(
        asset=asset, target_type=target_type, target_code=target_code,
        access_level=access_level, is_active=is_active,
        valid_from=valid_from or NOW, valid_to=valid_to,
    )
    session.add(p)
    session.commit()
    return p


def _seed_privileges(session, profile=COLLAB):
    """Module-level RBAC rows so a non-superuser passes require_privilege and
    the per-asset guard is the layer under test."""
    for option in ("ASSETS", "CHARACTERIZATIONS"):
        session.add(Privilege(
            profile=profile, module="LIB", option=option,
            can_edit=True, is_active=True))
    session.commit()


def _override(user):
    app.dependency_overrides[current_active_user] = lambda: user


# --- Service: effective access level ----------------------------------------

def test_manage_beats_view(session):
    user = _user()
    a = _mk_asset(session)
    _mk_perm(session, a.id, "USER", "1", access_level="VIEW")
    _mk_perm(session, a.id, "PUBLIC", "ALL", access_level="MANAGE")
    assert svc.assets_user_access(session, user, [a.id]) == {a.id: "MANAGE"}


def test_view_only_and_no_grant(session):
    user = _user()
    granted = _mk_asset(session, "granted")
    ungranted = _mk_asset(session, "ungranted")
    _mk_perm(session, granted.id, "USER", "1", access_level="VIEW")
    access = svc.assets_user_access(session, user, [granted.id, ungranted.id])
    assert access == {granted.id: "VIEW"}


def test_every_scope_type_grants(session):
    user = _user(id=5, unit="GEN_AI")
    session.add(Assignment(user_id=5, team="CORE", role="TL",
                           valid_from=PAST, is_active=True))
    session.add(Project(code="APOLLO", name="Apollo", team="CORE",
                        status="ACTIVE", is_active=True))
    session.commit()

    expectations = [
        ("USER", "5"), ("UNIT", "GEN_AI"), ("ROLE", "TL"),
        ("TEAM", "CORE"), ("PROJECT", "APOLLO"), ("PUBLIC", "ALL"),
    ]
    for target_type, target_code in expectations:
        a = _mk_asset(session, f"by-{target_type}")
        _mk_perm(session, a.id, target_type, target_code, access_level="MANAGE")
        assert svc.user_asset_access(session, user, a.id) == "MANAGE", target_type


def test_temporal_and_inactive_grants_ignored(session):
    user = _user()
    a = _mk_asset(session)
    # Expired MANAGE + future MANAGE + inactive MANAGE → none count.
    _mk_perm(session, a.id, "USER", "1", access_level="MANAGE",
             valid_from=PAST, valid_to=PAST + timedelta(hours=1))
    _mk_perm(session, a.id, "USER", "1", access_level="MANAGE", valid_from=FUTURE)
    _mk_perm(session, a.id, "PUBLIC", "ALL", access_level="MANAGE", is_active=False)
    # Currently-valid VIEW is what remains.
    _mk_perm(session, a.id, "USER", "1", access_level="VIEW")
    assert svc.user_asset_access(session, user, a.id) == "VIEW"


def test_accessible_assets_exact_set(session):
    user = _user(id=1)
    mine = _mk_asset(session, "mine")
    shared = _mk_asset(session, "shared")
    other = _mk_asset(session, "someone-elses")
    _mk_perm(session, mine.id, "USER", "1", access_level="MANAGE")
    _mk_perm(session, shared.id, "PUBLIC", "ALL", access_level="VIEW")
    _mk_perm(session, other.id, "USER", "2", access_level="MANAGE")
    assert svc.accessible_assets(session, user) == {
        mine.id: "MANAGE", shared.id: "VIEW"}


def test_require_asset_manage_guard(session):
    a = _mk_asset(session)
    _mk_perm(session, a.id, "USER", "1", access_level="MANAGE")
    _mk_perm(session, a.id, "USER", "2", access_level="VIEW")

    svc.require_asset_manage(session, _user(id=1), a.id)          # MANAGE → ok
    svc.require_asset_manage(session, _superuser(), a.id)         # bypass → ok
    with pytest.raises(svc.AssetAccessForbidden):
        svc.require_asset_manage(session, _user(id=2), a.id)      # VIEW → no
    with pytest.raises(svc.AssetAccessForbidden):
        svc.require_asset_manage(session, _user(id=3), a.id)      # none → no


# --- Route: caller-scoped with-access listing --------------------------------

def test_with_access_hides_ungranted_and_reports_my_access(session, client):
    _seed_privileges(session)
    visible_m = _mk_asset(session, "managed")
    visible_v = _mk_asset(session, "viewable")
    hidden = _mk_asset(session, "no grants at all")
    _mk_perm(session, visible_m.id, "USER", "1", access_level="MANAGE")
    _mk_perm(session, visible_v.id, "PUBLIC", "ALL", access_level="VIEW")
    _override(_user(id=1))

    r = client.get("/api/assets/with-access")
    assert r.status_code == 200
    rows = {row["id"]: row for row in r.json()["data"]}
    assert set(rows) == {visible_m.id, visible_v.id}
    assert rows[visible_m.id]["my_access"] == "MANAGE"
    assert rows[visible_v.id]["my_access"] == "VIEW"
    # Contract fields still present.
    assert rows[visible_v.id]["is_public"] is True
    assert "VIEW" in rows[visible_v.id]["access_levels"]
    assert rows[visible_v.id]["permission_scopes"] == ["PUBLIC"]
    assert hidden.id not in rows


def test_with_access_superuser_sees_everything(session, client):
    hidden = _mk_asset(session, "no grants at all")
    _override(_superuser())

    r = client.get("/api/assets/with-access")
    assert r.status_code == 200
    rows = {row["id"]: row for row in r.json()["data"]}
    assert hidden.id in rows
    assert rows[hidden.id]["my_access"] == "MANAGE"


def test_with_access_paginates_after_filtering(session, client):
    _seed_privileges(session)
    granted = [_mk_asset(session, f"granted-{i}") for i in ("a", "b", "c")]
    for a in granted:
        _mk_perm(session, a.id, "USER", "1", access_level="MANAGE")
    _mk_asset(session, "aaaa-ungranted-sorts-first")
    _override(_user(id=1))

    r = client.get("/api/assets/with-access?skip=1&limit=1")
    assert r.status_code == 200
    page = r.json()["data"]
    # Filter-first: the page is the 2nd GRANTED asset by name, never an
    # ungranted one and never an empty page.
    assert len(page) == 1
    assert page[0]["name"] == "granted-b"


# --- Route: MANAGE write guards ----------------------------------------------

def _grant_matrix_asset(session):
    """One asset with a MANAGE user (1), a VIEW user (2), and nothing for 3."""
    a = _mk_asset(session)
    _mk_perm(session, a.id, "USER", "1", access_level="MANAGE")
    _mk_perm(session, a.id, "USER", "2", access_level="VIEW")
    return a


def test_asset_put_requires_manage(session, client):
    _seed_privileges(session)
    a = _grant_matrix_asset(session)
    for uid, expected in ((3, 403), (2, 403), (1, 200)):
        _override(_user(id=uid))
        r = client.put(f"/api/assets/{a.id}", json={"description": f"by {uid}"})
        assert r.status_code == expected, f"user {uid}"


def test_asset_delete_requires_manage(session, client):
    _seed_privileges(session)
    a = _grant_matrix_asset(session)
    _override(_user(id=2))
    assert client.delete(f"/api/assets/{a.id}").status_code == 403
    _override(_user(id=1))
    assert client.delete(f"/api/assets/{a.id}").status_code == 200


def test_versions_route_requires_manage(session, client):
    _seed_privileges(session)
    a = _grant_matrix_asset(session)
    _override(_user(id=2))
    r = client.post(f"/api/assets/{a.id}/versions", json={"change_type": "patch"})
    assert r.status_code == 403
    _override(_user(id=1))
    r = client.post(f"/api/assets/{a.id}/versions", json={"change_type": "patch"})
    assert r.status_code == 200
    assert r.json()["data"]["current_version"] == "1.0.1"


def test_characterization_writes_require_manage(session, client):
    _seed_privileges(session)
    a = _grant_matrix_asset(session)
    session.add(Feature(code="OVERVIEW", name="Overview"))
    session.add(Characterization(asset=a.id, feature="MODE", value="x"))
    session.commit()

    _override(_user(id=2))  # VIEW-only
    assert client.post("/api/characterizations/", json={
        "asset": a.id, "feature": "OVERVIEW", "value": "v"}).status_code == 403
    assert client.put(f"/api/characterizations/{a.id}/MODE",
                      json={"value": "y"}).status_code == 403
    assert client.delete(f"/api/characterizations/{a.id}/MODE").status_code == 403

    _override(_user(id=1))  # MANAGE
    assert client.post("/api/characterizations/", json={
        "asset": a.id, "feature": "OVERVIEW", "value": "v"}).status_code == 201
    assert client.put(f"/api/characterizations/{a.id}/MODE",
                      json={"value": "y"}).status_code == 200
    assert client.delete(f"/api/characterizations/{a.id}/MODE").status_code == 200


def test_relation_writes_guard_on_source_only(session, client):
    _seed_privileges(session)
    source = _grant_matrix_asset(session)          # user 1 MANAGEs source
    target = _mk_asset(session, "target-ungranted")  # user 1 has NO grant here

    _override(_user(id=2))  # VIEW on source → blocked
    assert client.post("/api/asset_relations/", json={
        "source": source.id, "target": target.id, "type": "EXTENDS"}).status_code == 403

    _override(_user(id=1))  # MANAGE on source, nothing on target → allowed
    assert client.post("/api/asset_relations/", json={
        "source": source.id, "target": target.id, "type": "EXTENDS"}).status_code == 201
    assert client.put(f"/api/asset_relations/{source.id}/{target.id}",
                      json={"type": "SIMILAR_TO"}).status_code == 200
    assert client.delete(
        f"/api/asset_relations/{source.id}/{target.id}").status_code == 200


def test_view_user_cannot_self_escalate_via_permissions(session, client):
    _seed_privileges(session)
    a = _grant_matrix_asset(session)

    _override(_user(id=2))  # VIEW-only: granting himself MANAGE must 403
    r = client.post("/api/asset_permissions/", json={
        "asset": a.id, "target_type": "USER", "target_code": "2",
        "access_level": "MANAGE"})
    assert r.status_code == 403

    _override(_user(id=1))  # MANAGE holder can grant
    r = client.post("/api/asset_permissions/", json={
        "asset": a.id, "target_type": "USER", "target_code": "2",
        "access_level": "MANAGE"})
    assert r.status_code == 201
    pid = r.json()["data"]["id"]

    _override(_user(id=3))  # no grant: update/delete of grants also blocked
    assert client.put(f"/api/asset_permissions/{pid}",
                      json={"access_level": "VIEW"}).status_code == 403
    assert client.delete(f"/api/asset_permissions/{pid}").status_code == 403


# --- Plain create auto-grants the creator ------------------------------------

def test_create_auto_grants_creator_manage(session, client):
    _seed_privileges(session)
    creator = _user(id=7)
    _override(creator)

    r = client.post("/api/assets/", json={"name": "Mine", "status": "PUBLISHED"})
    assert r.status_code == 201
    asset_id = r.json()["data"]["id"]

    grant = session.exec(
        select(AssetPermission).where(
            AssetPermission.asset == asset_id,
            AssetPermission.target_type == "USER",
            AssetPermission.target_code == "7",
            AssetPermission.access_level == "MANAGE",
            AssetPermission.is_active == True,  # noqa: E712
        )
    ).first()
    assert grant is not None
    # The creator can immediately edit and sees it in his repo listing.
    assert client.put(f"/api/assets/{asset_id}",
                      json={"description": "mine"}).status_code == 200
    listed = {row["id"] for row in client.get(
        "/api/assets/with-access").json()["data"]}
    assert asset_id in listed
