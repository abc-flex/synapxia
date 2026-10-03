"""Dashboard permissions — `/api/dashboard_permissions` grant / update / revoke
(specs/006-dashboard-management, US4 / FR-019–FR-022)."""
from datetime import datetime

from app.insights.internal.models import DashboardPermission
from tests.ana_helpers import (
    FUTURE, PAST, data, mk_dashboard, mk_grant, mk_param, override, setup_owner, user,
)

BASE = "/api/dashboard_permissions"


def _grant(client, dashboard_id, **kw):
    body = {"dashboard": dashboard_id, "target_type": "TEAM", "target_code": "LAB",
            "access_level": "VIEW", **kw}
    return client.post(f"{BASE}/", json=body)


def test_grant_and_live_duplicate(client, session):
    d = setup_owner(session)
    override(user(1))
    assert _grant(client, d.id).status_code == 201
    assert _grant(client, d.id).status_code == 409


def test_public_grant_stores_all(client, session):
    d = setup_owner(session)
    override(user(1))
    r = _grant(client, d.id, target_type="PUBLIC", target_code="whatever")
    assert r.status_code == 201 and data(r)["target_code"] == "ALL"


def test_list_values_and_dashboard_are_validated(client, session):
    d = setup_owner(session)
    override(user(1))
    assert _grant(client, d.id, target_type="GALAXY").status_code == 400
    assert _grant(client, d.id, access_level="OWNER").status_code == 400
    assert _grant(client, 999).status_code == 400


def test_revoked_duplicate_does_not_block(client, session):
    d = setup_owner(session)
    mk_grant(session, d.id, "TEAM", "LAB", access_level="VIEW", valid_to=PAST)
    override(user(1))
    assert _grant(client, d.id).status_code == 201


def test_window_rules(client, session):
    d = setup_owner(session)
    override(user(1))
    r = _grant(client, d.id, valid_from=FUTURE.isoformat(), valid_to=PAST.isoformat())
    assert r.status_code == 400
    r = _grant(client, d.id, target_type="USER", target_code="5", valid_from=FUTURE.isoformat())
    assert r.status_code == 201
    # Listed (not revoked) but not yet in effect for user 5.
    codes = {p["target_code"] for p in data(client.get(f"{BASE}/dashboard/{d.id}"))}
    assert "5" in codes
    override(user(5))
    assert client.get(f"/api/dashboards/{d.id}").status_code == 403


def test_update(client, session):
    d = setup_owner(session)
    override(user(1))
    pid = data(_grant(client, d.id))["id"]
    r = client.put(f"{BASE}/{pid}", json={"access_level": "MANAGE"})
    assert r.status_code == 200 and data(r)["access_level"] == "MANAGE"
    assert client.put(f"{BASE}/{pid}", json={"access_level": "BOSS"}).status_code == 400
    assert client.put(f"{BASE}/{pid}", json={"valid_to": PAST.isoformat()}).status_code == 400
    assert client.put(f"{BASE}/999", json={"access_level": "VIEW"}).status_code == 404


def test_revoke_keeps_the_row_and_reports_bound_parameters(client, session):
    d = setup_owner(session)
    override(user(1))
    pid = data(_grant(client, d.id, valid_to=FUTURE.isoformat()))["id"]
    mk_param(session, d.id, "team", context_binding=pid)
    mk_param(session, d.id, "area", context_binding=pid)
    mk_param(session, d.id, "old", context_binding=pid, is_active=False)

    r = client.delete(f"{BASE}/{pid}")
    assert r.status_code == 200
    assert data(r)["bound_parameters"] == ["area", "team"]
    session.expire_all()
    row = session.get(DashboardPermission, pid)
    assert row is not None  # retained, not deleted
    assert row.valid_to is not None and row.valid_to <= datetime.utcnow()  # future valid_to overwritten
    # The binding is kept; it simply stops applying.
    params = data(client.get(f"/api/dashboards/{d.id}/parameters"))
    assert {p["name"]: p["context_binding"] for p in params} == {"team": pid, "area": pid}

    assert client.delete(f"{BASE}/{pid}").status_code == 400
    assert client.put(f"{BASE}/{pid}", json={"access_level": "VIEW"}).status_code == 400
    assert client.delete(f"{BASE}/999").status_code == 404


def test_revoke_removes_access_immediately(client, session):
    d = setup_owner(session)
    other = mk_grant(session, d.id, "USER", "2", access_level="VIEW")
    override(user(2))
    assert client.get(f"/api/dashboards/{d.id}").status_code == 200
    override(user(1))
    assert client.delete(f"{BASE}/{other.id}").status_code == 200
    override(user(2))
    assert client.get(f"/api/dashboards/{d.id}").status_code == 403
    assert data(client.get("/api/dashboards/with-access")) == []


def test_view_holder_cannot_self_escalate(client, session):
    d = setup_owner(session, access="VIEW")
    override(user(1))
    r = _grant(client, d.id, target_type="USER", target_code="1", access_level="MANAGE")
    assert r.status_code == 403
    [g] = data(client.get(f"{BASE}/dashboard/{d.id}"))
    assert client.delete(f"{BASE}/{g['id']}").status_code == 403
    assert client.put(f"{BASE}/{g['id']}", json={"access_level": "MANAGE"}).status_code == 403


def test_manage_beats_view_and_self_revoke(client, session):
    d = setup_owner(session)  # USER/1/MANAGE
    mk_grant(session, d.id, "PUBLIC", "ALL", access_level="VIEW")
    override(user(1))
    assert data(client.get(f"/api/dashboards/{d.id}"))["my_access"] == "MANAGE"
    mine = next(g for g in data(client.get(f"{BASE}/dashboard/{d.id}")) if g["target_code"] == "1")
    assert client.delete(f"{BASE}/{mine['id']}").status_code == 200
    # Still visible through the public grant, but read-only now.
    assert data(client.get(f"/api/dashboards/{d.id}"))["my_access"] == "VIEW"
    assert client.put(f"/api/dashboards/{d.id}", json={"name": "X"}).status_code == 403


def test_grants_of_another_dashboard_are_independent(client, session):
    d = setup_owner(session)
    other = mk_dashboard(session, name="Other")
    override(user(1))
    assert _grant(client, other.id).status_code == 403
