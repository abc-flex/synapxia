"""Process Management — access (specs/009-process-management, FR-018).

Every route needs a token and PROC/PROCESSES: read for GETs, edit for writes.
"""
from app.auth.routes import current_active_user
from app.main import app
from tests.proc_helpers import (
    BASE, data, mk_process, mk_user_row, override, seed_proc_lists, seed_privileges,
    setup, superuser, user,
)

GETS = [f"{BASE}/", f"{BASE}/form-options", f"{BASE}/P1",
        f"{BASE}/P1/relations", f"{BASE}/P1/assets", f"{BASE}/P1/inits"]
WRITES = [
    ("post", f"{BASE}/", {"code": "NEW", "name": "N", "type": "PRIMARY"}),
    ("put", f"{BASE}/P1", {"name": "x"}),
    ("delete", f"{BASE}/P1", None),
    ("put", f"{BASE}/P1/relations", {"relations": []}),
    ("put", f"{BASE}/P1/assets", {"assets": []}),
    ("put", f"{BASE}/P1/inits", {"inits": []}),
]


def _call(client, method, url, body):
    if body is None:
        return getattr(client, method)(url)
    return getattr(client, method)(url, json=body)


def test_no_token_is_401(client, session):
    app.dependency_overrides.pop(current_active_user, None)
    for url in GETS:
        assert client.get(url).status_code == 401, url
    for method, url, body in WRITES:
        assert _call(client, method, url, body).status_code == 401, url


def test_profile_without_privilege_is_403(client, session):
    seed_privileges(session)          # ADMINISTRATIVE only
    seed_proc_lists(session)
    mk_process(session, "P1")
    override(user(5, profile="COLLABORATOR"))
    for url in GETS:
        assert client.get(url).status_code == 403, url
    for method, url, body in WRITES:
        assert _call(client, method, url, body).status_code == 403, url


def test_read_only_privilege(client, session):
    setup(session, can_edit=False)
    mk_process(session, "P1")
    for url in GETS:
        assert client.get(url).status_code == 200, url
    assert data(client.get(f"{BASE}/form-options"))["can_edit"] is False
    for method, url, body in WRITES:
        assert _call(client, method, url, body).status_code == 403, url


def test_edit_privilege_and_superuser(client, session):
    setup(session)
    mk_process(session, "P1")
    assert data(client.get(f"{BASE}/form-options"))["can_edit"] is True
    mk_user_row(session, 99, is_superuser=True)
    override(superuser(99))
    opts = data(client.get(f"{BASE}/form-options"))
    assert opts["can_edit"] is True
    assert opts["relation_rules"]["SUPPORTS"] == {"source": ["SUPPORT"], "target": ["PRIMARY"]}
    assert client.put(f"{BASE}/P1", json={"name": "y"}).status_code == 200
