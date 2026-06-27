"""Standardized response envelope (PR: refactor/api-response-envelope).

Every JSON response under ``/api/`` except ``/api/auth/*`` is wrapped as
``{data, error, meta}`` (success) or ``{data:null, error:{code,message,details},
meta}`` (error). Auth, ``/health`` and ``/`` keep their native shapes.

These run through the routes against the in-memory SQLite fixtures, overriding
``current_active_user`` with a superuser to clear the ``require_privilege`` gate
(mirrors test_lib_relations).
"""

from types import SimpleNamespace

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal.models import Asset


def _superuser():
    return SimpleNamespace(
        id=1, username="tester", profile="ADMINISTRATOR",
        is_superuser=True, is_active=True,
    )


def _mk_asset(session, name="Asset"):
    a = Asset(name=name, status="PUBLISHED", is_active=True)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


# --- Success envelope -------------------------------------------------------

def test_success_list_is_enveloped_with_meta(session, client):
    _mk_asset(session, "A")
    app.dependency_overrides[current_active_user] = _superuser
    try:
        r = client.get("/api/assets/?skip=0&limit=5")
        assert r.status_code == 200
        body = r.json()
        # One predictable shape.
        assert set(body.keys()) == {"data", "error", "meta"}
        assert body["error"] is None
        assert isinstance(body["data"], list)
        # meta echoes pagination + list count (no grand total).
        assert body["meta"]["skip"] == 0
        assert body["meta"]["limit"] == 5
        assert body["meta"]["count"] == len(body["data"])
    finally:
        app.dependency_overrides.pop(current_active_user, None)


def test_success_object_is_enveloped(session, client):
    a = _mk_asset(session, "Solo")
    app.dependency_overrides[current_active_user] = _superuser
    try:
        r = client.get(f"/api/assets/{a.id}")
        assert r.status_code == 200
        body = r.json()
        assert body["error"] is None
        assert body["data"]["id"] == a.id
        assert body["data"]["name"] == "Solo"
    finally:
        app.dependency_overrides.pop(current_active_user, None)


# --- Error envelope ---------------------------------------------------------

def test_not_found_is_enveloped(session, client):
    app.dependency_overrides[current_active_user] = _superuser
    try:
        r = client.get("/api/assets/999999")
        assert r.status_code == 404
        body = r.json()
        assert body["data"] is None
        assert body["error"]["code"] == 404
        assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    finally:
        app.dependency_overrides.pop(current_active_user, None)


def test_validation_error_is_enveloped(session, client):
    app.dependency_overrides[current_active_user] = _superuser
    try:
        r = client.post("/api/asset_relations/", json={})  # missing required fields
        assert r.status_code == 422
        body = r.json()
        assert body["data"] is None
        assert body["error"]["code"] == 422
        assert isinstance(body["error"]["details"], list)
    finally:
        app.dependency_overrides.pop(current_active_user, None)


# --- Exclusions (native shapes preserved) -----------------------------------

def test_auth_routes_not_enveloped(client):
    # fastapi-users + ui/src/lib/auth.ts rely on the native {detail} / raw bodies.
    r = client.get("/api/auth/me")  # no token → 401, native shape
    assert r.status_code == 401
    body = r.json()
    assert "detail" in body
    assert "data" not in body and "error" not in body


def test_root_not_enveloped(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "name" in body  # the inventory dict, not the envelope
    assert "data" not in body
