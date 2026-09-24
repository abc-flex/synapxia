"""Initiative permissions — `/api/init_permissions` (grant / update / revoke)."""
from datetime import datetime

from app.inits.internal.models import InitPermission
from tests.inits_helpers import (
    FUTURE, PAST, data, mk_init, mk_perm, override, seed_privileges, user,
)

BASE = "/api/init_permissions"


def _setup(session, access="MANAGE"):
    seed_privileges(session)
    init = mk_init(session)
    mk_perm(session, init.id, "USER", "1", access_level=access)
    return init


def _grant(client, init_id, **kw):
    body = {"init": init_id, "target_type": "TEAM", "target_code": "LAB",
            "access_level": "VIEW", **kw}
    return client.post(f"{BASE}/", json=body)


def test_list_live_grants_including_future(client, session):
    init = _setup(session)
    mk_perm(session, init.id, "TEAM", "A", access_level="VIEW", valid_from=FUTURE)
    mk_perm(session, init.id, "TEAM", "B", access_level="VIEW", valid_from=PAST, valid_to=PAST)
    override(user(1))
    codes = {p["target_code"] for p in data(client.get(f"{BASE}/init/{init.id}"))}
    assert codes == {"1", "A"}


def test_grant_and_duplicates(client, session):
    init = _setup(session)
    override(user(1))
    assert _grant(client, init.id).status_code == 201
    assert _grant(client, init.id).status_code == 409


def test_revoked_grant_does_not_block_regrant(client, session):
    init = _setup(session)
    mk_perm(session, init.id, "TEAM", "LAB", access_level="VIEW", valid_from=PAST, valid_to=PAST)
    override(user(1))
    assert _grant(client, init.id).status_code == 201


def test_invalid_window(client, session):
    init = _setup(session)
    override(user(1))
    r = _grant(client, init.id, valid_from=FUTURE.isoformat(), valid_to=PAST.isoformat())
    assert r.status_code == 400
    assert _grant(client, 999).status_code == 400


def test_update_and_revoke(client, session):
    init = _setup(session)
    override(user(1))
    pid = data(_grant(client, init.id, valid_to=FUTURE.isoformat()))["id"]

    r = client.put(f"{BASE}/{pid}", json={"access_level": "MANAGE"})
    assert r.status_code == 200 and data(r)["access_level"] == "MANAGE"

    r = client.delete(f"{BASE}/{pid}")
    assert r.status_code == 200
    session.expire_all()
    row = session.get(InitPermission, pid)
    assert row is not None  # retained, not deleted
    assert row.valid_to is not None and row.valid_to <= datetime.utcnow()  # future valid_to overwritten

    assert client.delete(f"{BASE}/{pid}").status_code == 400
    assert client.put(f"{BASE}/{pid}", json={"access_level": "VIEW"}).status_code == 400
    assert client.delete(f"{BASE}/999").status_code == 404


def test_view_holder_cannot_self_escalate(client, session):
    init = _setup(session, access="VIEW")
    override(user(1))
    r = _grant(client, init.id, target_type="USER", target_code="1", access_level="MANAGE")
    assert r.status_code == 403
    pid = session.exec(InitPermission.__table__.select()).first().id
    assert client.delete(f"{BASE}/{pid}").status_code == 403


def test_reads_require_view(client, session):
    init = _setup(session)
    override(user(2))
    assert client.get(f"{BASE}/init/{init.id}").status_code == 403
    assert client.get(f"{BASE}/init/999").status_code == 404
