"""Contract/permission tests for GET /api/assets/category/{code}/with-access
(Constitution III) — the category-scoped counterpart of `/with-access` that
backs the Explore Category page's privileges filter.

Two things distinguish it from `/with-access` and are worth locking down:
  1. Read access follows `get_by_category`'s rule (`LIB/ASSETS` OR
     `LIB/<category_code>`), NOT `/with-access`'s stricter `LIB/ASSETS`-only
     gate — a profile holding only the catalog-specific privilege (e.g.
     COLLABORATOR/REVIEWER on `LIB/PROMPTS`) must still be able to call it.
  2. The access summary (`permission_scopes`/`my_access`/hiding ungranted
     assets) matches `/with-access`, restricted to one category.
"""

from types import SimpleNamespace

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal.models import Asset, AssetPermission
from app.admin.internal.models import Privilege

COLLAB = "COLLABORATOR"


def _user(id=1, unit="GEN_AI", superuser=False, profile=COLLAB):
    return SimpleNamespace(
        id=id, username=f"u{id}", unit=unit, profile=profile,
        is_superuser=superuser, is_active=True,
    )


def _superuser(uid=99):
    return _user(id=uid, superuser=True, profile="ADMINISTRATOR")


def _mk_asset(session, name="A", category="PROMPTS"):
    a = Asset(name=name, status="PUBLISHED", category=category)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _mk_perm(session, asset, target_type, target_code, *, access_level="VIEW"):
    p = AssetPermission(
        asset=asset, target_type=target_type, target_code=target_code,
        access_level=access_level,
    )
    session.add(p)
    session.commit()
    return p


def _grant_category_privilege(session, category_code, profile=COLLAB, can_edit=False):
    """Only the catalog-specific option — deliberately NOT `LIB/ASSETS` — so
    tests exercise the `has_privilege(LIB, category_code)` branch alone."""
    session.add(Privilege(
        profile=profile, module="LIB", option=category_code,
        can_edit=can_edit, is_active=True))
    session.commit()


def _override(user):
    app.dependency_overrides[current_active_user] = lambda: user


def test_requires_auth(client):
    r = client.get("/api/assets/category/PROMPTS/with-access")
    assert r.status_code in (401, 403)


def test_category_privilege_alone_is_sufficient(session, client):
    """A profile with LIB/PROMPTS but NOT LIB/ASSETS must be let in — this is
    exactly how COLLABORATOR/REVIEWER reach Explore today."""
    _grant_category_privilege(session, "PROMPTS")
    granted = _mk_asset(session, "granted")
    _mk_perm(session, granted.id, "PUBLIC", "ALL", access_level="VIEW")
    _override(_user(id=1))

    r = client.get("/api/assets/category/PROMPTS/with-access")
    assert r.status_code == 200
    rows = {row["id"]: row for row in r.json()["data"]}
    assert granted.id in rows
    assert rows[granted.id]["permission_scopes"] == ["PUBLIC"]


def test_denies_without_any_matching_privilege(session, client):
    """Neither LIB/ASSETS nor LIB/<category> → 403, matching get_by_category."""
    _mk_asset(session, "irrelevant")
    _override(_user(id=1))

    r = client.get("/api/assets/category/PROMPTS/with-access")
    assert r.status_code == 403


def test_hides_ungranted_and_scopes_to_category(session, client):
    _grant_category_privilege(session, "PROMPTS")
    visible = _mk_asset(session, "visible-prompt", category="PROMPTS")
    hidden = _mk_asset(session, "hidden-prompt", category="PROMPTS")
    other_category = _mk_asset(session, "granted-but-wrong-category", category="MCPS")
    _mk_perm(session, visible.id, "USER", "1", access_level="MANAGE")
    _mk_perm(session, other_category.id, "USER", "1", access_level="MANAGE")
    _override(_user(id=1))

    r = client.get("/api/assets/category/PROMPTS/with-access")
    assert r.status_code == 200
    ids = {row["id"] for row in r.json()["data"]}
    assert ids == {visible.id}
    assert hidden.id not in ids
    assert other_category.id not in ids  # granted, but a different category


def test_superuser_sees_every_asset_in_category(session, client):
    a = _mk_asset(session, "no grants at all", category="PROMPTS")
    _mk_asset(session, "different category", category="MCPS")
    _override(_superuser())

    r = client.get("/api/assets/category/PROMPTS/with-access")
    assert r.status_code == 200
    rows = {row["id"]: row for row in r.json()["data"]}
    assert set(rows) == {a.id}
    assert rows[a.id]["my_access"] == "MANAGE"


def test_assets_privilege_alone_is_also_sufficient(session, client):
    """The general LIB/ASSETS privilege still works, mirroring get_by_category."""
    session.add(Privilege(profile=COLLAB, module="LIB", option="ASSETS",
                           can_edit=False, is_active=True))
    session.commit()
    a = _mk_asset(session, "asset-manager-visible", category="PROMPTS")
    _mk_perm(session, a.id, "PUBLIC", "ALL", access_level="VIEW")
    _override(_user(id=1))

    r = client.get("/api/assets/category/PROMPTS/with-access")
    assert r.status_code == 200
    assert {row["id"] for row in r.json()["data"]} == {a.id}
