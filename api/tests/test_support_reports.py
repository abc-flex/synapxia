"""Bug report tests (Support module) — Constitution Principle II/III.

Any active user may submit a bug report; only superusers may list/read them.
Server-side caps bound description/screenshot/attachment size (never trust
the client) and map to 400, not a bare pydantic 422.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.main import app
from app.auth.routes import current_active_user, current_superuser
from app.admin.internal.models import User
from app.support.internal.models import MAX_DESCRIPTION_LENGTH, MAX_ATTACHMENTS


def _mk_user(session, id=1, username="reporter", is_superuser=False):
    u = User(
        id=id, username=username, email=f"{username}@x.co",
        password_hash="x", first_name="Rep", last_name="Orter",
        profile="COLLABORATOR", unit="HQ", is_active=True, is_superuser=is_superuser,
    )
    session.add(u)
    session.commit()
    return u


def _user(uid=1, is_superuser=False):
    return SimpleNamespace(
        id=uid, username="reporter", profile="COLLABORATOR",
        is_superuser=is_superuser, is_active=True,
    )


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


# --- Auth gating -------------------------------------------------------

def test_create_requires_auth(client):
    r = client.post("/api/support/reports", json={"description": "It broke"})
    assert r.status_code in (401, 403)


def test_list_requires_auth(client):
    r = client.get("/api/support/reports")
    assert r.status_code in (401, 403)


def test_list_requires_superuser(client, session):
    _mk_user(session, id=1, is_superuser=False)
    app.dependency_overrides[current_superuser] = lambda: (
        _raise_forbidden()
    )
    r = client.get("/api/support/reports")
    assert r.status_code == 403


def _raise_forbidden():
    raise HTTPException(status_code=403, detail="Forbidden")


# --- Create round-trip ---------------------------------------------------

def test_create_round_trip(client, session):
    _mk_user(session, id=1)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    payload = {
        "description": "The export button does nothing on Firefox.",
        "page_url": "https://app.synapxia.local/admin/users",
        "user_agent": "Mozilla/5.0",
        "screenshot": "data:image/png;base64,aaaa",
        "attachments": ["data:image/png;base64,bbbb"],
    }
    r = client.post("/api/support/reports", json=payload)
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["description"] == payload["description"]
    assert body["user_id"] == 1
    assert body["status"] == "OPEN"
    assert body["screenshot"] == payload["screenshot"]
    assert body["attachments"] == payload["attachments"]


def test_create_minimal(client, session):
    _mk_user(session, id=1)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post("/api/support/reports", json={"description": "Broken"})
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["screenshot"] is None
    assert body["attachments"] is None


# --- Caps -----------------------------------------------------------------

def test_description_over_cap_is_400(client, session):
    _mk_user(session, id=1)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post(
        "/api/support/reports",
        json={"description": "x" * (MAX_DESCRIPTION_LENGTH + 1)},
    )
    assert r.status_code == 400


def test_too_many_attachments_is_400(client, session):
    _mk_user(session, id=1)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post(
        "/api/support/reports",
        json={
            "description": "Broken",
            "attachments": ["data:image/png;base64,x"] * (MAX_ATTACHMENTS + 1),
        },
    )
    assert r.status_code == 400


def test_oversized_screenshot_is_400(client, session):
    _mk_user(session, id=1)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post(
        "/api/support/reports",
        json={"description": "Broken", "screenshot": "data:image/png;base64," + "a" * 3_000_000},
    )
    assert r.status_code == 400


# --- List / pagination ------------------------------------------------------

def test_list_as_superuser(client, session):
    _mk_user(session, id=1, is_superuser=True)
    app.dependency_overrides[current_active_user] = lambda: _user(1)
    app.dependency_overrides[current_superuser] = lambda: _user(1, is_superuser=True)

    for i in range(3):
        client.post("/api/support/reports", json={"description": f"Bug {i}"})

    r = client.get("/api/support/reports?skip=0&limit=2")
    assert r.status_code == 200
    body = r.json()["data"]
    assert len(body) == 2
    # Newest first, and the listing shape omits the heavy blob fields.
    assert "screenshot" not in body[0]
    assert "attachments" not in body[0]
    assert body[0]["description"] == "Bug 2"
