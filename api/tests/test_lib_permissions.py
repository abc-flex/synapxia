"""Permission-scope tests (asset privileges/permisos filter) — Principle II/III.

`permissions_service` computes, per asset, which scope-types (USER/ROLE/TEAM/UNIT/
PROJECT/PUBLIC) grant the *current user* access — the data behind the asset list's
privileges filter. The scope logic is pure selects (SQLite-safe) and is covered
directly here. The `/api/assets/with-access` route that surfaces it uses Postgres-only
aggregates (array_agg/bool_or), so only its auth-gating + OpenAPI presence are checked
here (query behavior is verified against Postgres).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from sqlmodel import select

from app.lib.internal import permissions_service as svc
from app.lib.internal.models import Asset, AssetPermission
from app.collab.internal.models import Assignment, Project


NOW = datetime.utcnow()
PAST = NOW - timedelta(days=1)
FUTURE = NOW + timedelta(days=1)


def _user(id=1, unit="GEN_AI"):
    return SimpleNamespace(id=id, unit=unit)


def _mk_asset(session, name="A"):
    a = Asset(name=name, status="PUBLISHED")
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _mk_perm(session, asset, target_type, target_code, *, is_active=True,
             valid_from=None, valid_to=None, access_level="VIEW"):
    p = AssetPermission(
        asset=asset, target_type=target_type, target_code=target_code,
        access_level=access_level, is_active=is_active,
        valid_from=valid_from or NOW, valid_to=valid_to,
    )
    session.add(p)
    session.commit()
    return p


def _mk_assignment(session, user_id, *, role=None, team=None, is_active=True,
                   valid_from=None, valid_to=None):
    a = Assignment(
        user_id=user_id, role=role or "MEMBER", team=team, is_active=is_active,
        valid_from=valid_from or NOW, valid_to=valid_to,
    )
    session.add(a)
    session.commit()
    return a


def _mk_project(session, code, team, is_active=True):
    p = Project(code=code, name=code, team=team, status="ACTIVE", is_active=is_active)
    session.add(p)
    session.commit()
    return p


# --- resolve_user_scopes ---------------------------------------------------

def test_resolve_scopes_user_and_unit_direct(session):
    scopes = svc.resolve_user_scopes(session, _user(7, "ENG"))
    assert scopes["USER"] == {"7"}
    assert scopes["UNIT"] == {"ENG"}
    assert scopes["ROLE"] == set() and scopes["TEAM"] == set() and scopes["PROJECT"] == set()


def test_resolve_scopes_roles_and_teams_from_assignments(session):
    _mk_assignment(session, 7, role="TL", team="CORE")
    _mk_assignment(session, 7, role="QA", team="OPS")
    _mk_assignment(session, 99, role="OTHER", team="OTHER")  # another user — excluded
    scopes = svc.resolve_user_scopes(session, _user(7))
    assert scopes["ROLE"] == {"TL", "QA"}
    assert scopes["TEAM"] == {"CORE", "OPS"}


def test_resolve_scopes_projects_from_user_teams(session):
    _mk_assignment(session, 7, role="TL", team="CORE")
    _mk_project(session, "PROJ_A", "CORE")
    _mk_project(session, "PROJ_B", "CORE", is_active=False)  # inactive — excluded
    _mk_project(session, "PROJ_C", "OTHER")                   # other team — excluded
    scopes = svc.resolve_user_scopes(session, _user(7))
    assert scopes["PROJECT"] == {"PROJ_A"}


def test_resolve_scopes_excludes_inactive_and_expired_assignments(session):
    _mk_assignment(session, 7, role="ACTIVE_R", team="ACTIVE_T")
    _mk_assignment(session, 7, role="INACTIVE_R", team="INACTIVE_T", is_active=False)
    _mk_assignment(session, 7, role="EXPIRED_R", team="EXPIRED_T", valid_to=PAST)
    _mk_assignment(session, 7, role="FUTURE_R", team="FUTURE_T", valid_from=FUTURE)
    scopes = svc.resolve_user_scopes(session, _user(7))
    assert scopes["ROLE"] == {"ACTIVE_R"}
    assert scopes["TEAM"] == {"ACTIVE_T"}


# --- assets_user_scopes ----------------------------------------------------

def test_assets_scopes_public_always_matches(session):
    a = _mk_asset(session)
    _mk_perm(session, a.id, "PUBLIC", "PUBLIC")
    out = svc.assets_user_scopes(session, _user(7), [a.id])
    assert out[a.id] == ["PUBLIC"]


def test_assets_scopes_user_and_unit_match(session):
    a = _mk_asset(session)
    _mk_perm(session, a.id, "USER", "7")
    _mk_perm(session, a.id, "UNIT", "ENG")
    _mk_perm(session, a.id, "USER", "999")   # different user — no match
    out = svc.assets_user_scopes(session, _user(7, "ENG"), [a.id])
    assert out[a.id] == ["UNIT", "USER"]  # sorted


def test_assets_scopes_role_team_project_via_assignments(session):
    a = _mk_asset(session)
    _mk_assignment(session, 7, role="TL", team="CORE")
    _mk_project(session, "PROJ_A", "CORE")
    _mk_perm(session, a.id, "ROLE", "TL")
    _mk_perm(session, a.id, "TEAM", "CORE")
    _mk_perm(session, a.id, "PROJECT", "PROJ_A")
    _mk_perm(session, a.id, "ROLE", "NOPE")  # role the user doesn't have — no match
    out = svc.assets_user_scopes(session, _user(7), [a.id])
    assert out[a.id] == ["PROJECT", "ROLE", "TEAM"]


def test_assets_scopes_excludes_inactive_and_expired_permissions(session):
    a = _mk_asset(session)
    _mk_perm(session, a.id, "USER", "7", is_active=False)     # inactive
    _mk_perm(session, a.id, "UNIT", "GEN_AI", valid_to=PAST)  # expired
    out = svc.assets_user_scopes(session, _user(7, "GEN_AI"), [a.id])
    assert a.id not in out  # no granting permission → asset absent


def test_assets_scopes_empty_for_no_ids(session):
    assert svc.assets_user_scopes(session, _user(7), []) == {}


def test_assets_scopes_per_user_isolation(session):
    a = _mk_asset(session)
    _mk_perm(session, a.id, "USER", "7")
    # User 8 has no matching permission on this asset.
    assert svc.assets_user_scopes(session, _user(8), [a.id]) == {}
    assert svc.assets_user_scopes(session, _user(7), [a.id])[a.id] == ["USER"]


# --- Route contract (auth + OpenAPI only; query is Postgres-only) ----------

def test_with_access_requires_auth(client):
    assert client.get("/api/assets/with-access").status_code in (401, 403)


def test_with_access_in_openapi_with_permission_scopes(client):
    spec = client.get("/openapi.json").json()
    assert "/api/assets/with-access" in spec["paths"]
    # The response schema advertises the new field.
    assert "permission_scopes" in spec["components"]["schemas"]["AssetWithAccessLevels"]["properties"]
