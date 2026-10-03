"""Dashboard Management — `/api/dashboards` core CRUD and the grant-scoped list
(specs/006-dashboard-management, US1)."""
from app.insights.internal.models import Dashboard, DashboardPermission
from sqlmodel import select
from tests.ana_helpers import (
    data, mk_dashboard, mk_grant, override, seed_ana_lists, seed_privileges, setup_owner,
    superuser, user,
)

BASE = "/api/dashboards"
BODY = {
    "name": "Adoption", "type": "DASHBOARD", "sources_types": "POWER_BI",
    "source_url": "https://app.powerbi.com/view?r=abc", "tags": ["genai"],
}


def _seed(session, can_edit=True):
    seed_privileges(session, can_edit=can_edit)
    seed_ana_lists(session)


# ── POST ────────────────────────────────────────────────────────────────────

def test_create_starts_draft_and_grants_creator_manage(client, session):
    _seed(session)
    override(user(1))
    r = client.post(f"{BASE}/", json=BODY)
    assert r.status_code == 201
    body = data(r)
    assert body["status"] == "DRAFT" and body["my_access"] == "MANAGE"
    assert body["allowed_statuses"] == ["DRAFT", "PUBLISHED"]
    grants = session.exec(
        select(DashboardPermission).where(DashboardPermission.dashboard == body["id"])
    ).all()
    assert [(g.target_type, g.target_code, g.access_level) for g in grants] == [
        ("USER", "1", "MANAGE")]


def test_create_rejects_non_draft_status(client, session):
    _seed(session)
    override(user(1))
    assert client.post(f"{BASE}/", json={**BODY, "status": "PUBLISHED"}).status_code == 400
    assert client.post(f"{BASE}/", json={**BODY, "status": "DRAFT"}).status_code == 201


def test_create_required_and_list_fields(client, session):
    _seed(session)
    override(user(1))
    for field in ("name", "type", "sources_types", "source_url"):
        assert client.post(f"{BASE}/", json={**BODY, field: "  "}).status_code == 400, field
    assert client.post(f"{BASE}/", json={**BODY, "type": "NOPE"}).status_code == 400
    assert client.post(f"{BASE}/", json={**BODY, "sources_types": "NOPE"}).status_code == 400


def test_create_source_url_rules(client, session):
    _seed(session)
    override(user(1))
    assert client.post(f"{BASE}/", json={**BODY, "source_url": "http://x.com/d"}).status_code == 400
    assert client.post(f"{BASE}/", json={**BODY, "source_url": "/ana/usage"}).status_code == 400
    assert client.post(f"{BASE}/", json={**BODY, "source_url": "https://"}).status_code == 400
    internal = {**BODY, "sources_types": "INTERNAL_PAGE"}
    assert client.post(f"{BASE}/", json={**internal, "source_url": "/ana/usage"}).status_code == 201
    assert client.post(f"{BASE}/", json={**internal, "source_url": "https://x.com"}).status_code == 400
    assert client.post(f"{BASE}/", json={**internal, "source_url": "//evil.com"}).status_code == 400


def test_create_requires_edit_privilege(client, session):
    _seed(session, can_edit=False)
    override(user(1))
    assert client.post(f"{BASE}/", json=BODY).status_code == 403


def test_create_requires_token(client, session):
    _seed(session)
    assert client.post(f"{BASE}/", json=BODY).status_code == 401


# ── GET /with-access ────────────────────────────────────────────────────────

def test_list_is_scoped_before_pagination(client, session):
    _seed(session)
    granted = []
    for i in range(6):
        d = mk_dashboard(session, name=f"D{i}")
        if i % 2 == 0:
            mk_grant(session, d.id, "USER", "1", access_level="VIEW")
            granted.append(d.name)
    mk_grant(session, mk_dashboard(session, name="Gone", is_active=False).id, "USER", "1")
    override(user(1))
    page1 = data(client.get(f"{BASE}/with-access?skip=0&limit=2"))
    page2 = data(client.get(f"{BASE}/with-access?skip=2&limit=2"))
    assert [d["name"] for d in page1 + page2] == granted


def test_list_access_and_scopes(client, session):
    _seed(session)
    d = mk_dashboard(session)
    mk_grant(session, d.id, "PUBLIC", "ALL", access_level="VIEW")
    mk_grant(session, d.id, "USER", "1", access_level="MANAGE")
    override(user(1))
    [row] = data(client.get(f"{BASE}/with-access"))
    assert row["my_access"] == "MANAGE"
    assert row["permission_scopes"] == ["PUBLIC", "USER"]


def test_list_empty_without_grants(client, session):
    _seed(session)
    mk_dashboard(session)
    override(user(1))
    assert data(client.get(f"{BASE}/with-access")) == []


def test_superuser_sees_all(client, session):
    _seed(session)
    mk_dashboard(session, name="A")
    mk_dashboard(session, name="B")
    override(superuser())
    rows = data(client.get(f"{BASE}/with-access"))
    assert [r["name"] for r in rows] == ["A", "B"]
    assert {r["my_access"] for r in rows} == {"MANAGE"}


# ── GET /{id} ───────────────────────────────────────────────────────────────

def test_get_one(client, session):
    d = setup_owner(session, access="VIEW")
    other = mk_dashboard(session, name="Other")
    gone = mk_dashboard(session, name="Gone", is_active=False)
    mk_grant(session, gone.id, "USER", "1")
    override(user(1))
    r = client.get(f"{BASE}/{d.id}")
    assert r.status_code == 200 and data(r)["my_access"] == "VIEW"
    assert client.get(f"{BASE}/{other.id}").status_code == 403
    assert client.get(f"{BASE}/{gone.id}").status_code == 404
    assert client.get(f"{BASE}/999").status_code == 404


# ── PUT /{id} ───────────────────────────────────────────────────────────────

def test_update_applies_only_sent_keys(client, session):
    d = setup_owner(session, description="keep")
    override(user(1))
    r = client.put(f"{BASE}/{d.id}", json={"name": "Renamed"})
    assert r.status_code == 200
    body = data(r)
    assert body["name"] == "Renamed" and body["description"] == "keep"
    assert body["updated_at"] is not None


def test_update_requires_manage(client, session):
    d = setup_owner(session, access="VIEW")
    override(user(1))
    assert client.put(f"{BASE}/{d.id}", json={"name": "X"}).status_code == 403


def test_update_revalidates_source_url_on_source_change(client, session):
    d = setup_owner(session)  # POWER_BI + https URL
    override(user(1))
    assert client.put(f"{BASE}/{d.id}", json={"sources_types": "INTERNAL_PAGE"}).status_code == 400
    r = client.put(f"{BASE}/{d.id}", json={"sources_types": "INTERNAL_PAGE", "source_url": "/ana/x"})
    assert r.status_code == 200
    assert client.put(f"{BASE}/{d.id}", json={"name": "  "}).status_code == 400


# ── DELETE /{id} ────────────────────────────────────────────────────────────

def test_delete_is_logical(client, session):
    d = setup_owner(session)
    override(user(1))
    assert client.delete(f"{BASE}/{d.id}").status_code == 200
    session.expire_all()
    assert session.get(Dashboard, d.id).is_active is False
    assert data(client.get(f"{BASE}/with-access")) == []


def test_delete_requires_manage(client, session):
    d = setup_owner(session, access="VIEW")
    override(user(1))
    assert client.delete(f"{BASE}/{d.id}").status_code == 403
