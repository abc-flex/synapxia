"""Executions — start / finish / cancelled (specs/007-dashboard-catalog US2/US3).

Every attempt past the module gate leaves exactly one `executions` row."""
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, urlsplit

from app.main import app
from tests.catalog_helpers import (
    data, executions, mk_dashboard, mk_grant, mk_list_def, mk_param, override,
    seed_ana_lists, setup_catalog, user, viewer,
)
from app.insights.internal.models import Execution


def start_url(d):
    return f"/api/dashboards/{d.id}/executions"


def finish_url(exec_id):
    return f"/api/executions/{exec_id}/finish"


def query(url):
    return dict(parse_qsl(urlsplit(url).query))


# ── Start: success ───────────────────────────────────────────────────────────

def test_start_records_in_progress_row_for_session_user(client, session):
    d = setup_catalog(session, source_url="https://bi.example/r?r=abc")
    mk_param(session, d.id, "date_from", data_type="DATE", default_value="2026-01-01", is_required=True)
    mk_param(session, d.id, "q", label="Query")
    override(viewer(id=1))
    r = client.post(start_url(d), json={"values": {"q": "a b&c", "user_id": 7}})
    assert r.status_code == 201
    body = data(r)
    assert body["mode"] == "TAB"
    assert body["launch_url"].startswith("https://bi.example/r?")
    assert query(body["launch_url"]) == {"r": "abc", "date_from": "2026-01-01", "q": "a b&c"}
    [row] = executions(session, d.id)
    assert row.id == body["execution_id"] and row.user_id == 1 and row.status is None
    assert row.payload == {
        "values": {"date_from": "2026-01-01", "q": "a b&c"},
        "sources": {"date_from": "DEFAULT", "q": "INPUT"},
        "mode": "TAB",
    }


def test_internal_page_gets_embed_and_viewer_mode(client, session):
    d = setup_catalog(session, sources_types="INTERNAL_PAGE", source_url="/support")
    mk_param(session, d.id, "top", data_type="NUMBER")
    override(viewer())
    body = data(client.post(start_url(d), json={"values": {"top": "10"}}))
    assert body["mode"] == "VIEWER"
    assert urlsplit(body["launch_url"]).path == "/support"
    assert query(body["launch_url"]) == {"top": "10", "embed": "1"}


def test_grant_value_is_forced_and_list_source(client, session):
    d = setup_catalog(session, grant=("PUBLIC", "ALL"))
    unit = mk_grant(session, d.id, "UNIT", "ENG", access_level="VIEW")
    mk_param(session, d.id, "unit", context_binding=unit.id)
    mk_param(session, d.id, "gran", list="GRANULARITY", default_value="WEEK")
    mk_param(session, d.id, "unknown_is_ignored_here")
    override(viewer(unit="ENG"))
    body = data(client.post(start_url(d), json={"values": {"unit": "OPS", "gran": "DAY", "nope": "x"}}))
    assert query(body["launch_url"]) == {"unit": "ENG", "gran": "DAY"}
    row = executions(session, d.id)[0]
    assert row.payload["sources"] == {"unit": "GRANT", "gran": "LIST"}


# ── Start: refusals (US3) ────────────────────────────────────────────────────

def test_unauthorized_records_row_and_403(client, session):
    seed_ana_lists(session)
    from tests.catalog_helpers import seed_privileges
    seed_privileges(session, profile="COLLABORATOR", options=("CATALOG",), can_edit=False)
    hidden = mk_dashboard(session, status="PUBLISHED")
    archived = mk_dashboard(session, name="Arch", status="ARCHIVED")
    mk_grant(session, archived.id, "USER", "1", access_level="VIEW")
    mk_param(session, hidden.id, "p")
    override(viewer())
    r = client.post(start_url(hidden), json={"values": {"p": "v", "zzz": "w"}})
    assert r.status_code == 403
    [row] = executions(session, hidden.id)
    assert row.status == "UNAUTHORIZED" and row.error_message
    assert row.payload == {"values": {"p": "v"}}
    assert client.post(start_url(archived), json={}).status_code == 403
    assert executions(session, archived.id)[0].status == "UNAUTHORIZED"


def test_no_catalog_privilege_writes_no_row(client, session):
    seed_ana_lists(session)
    d = mk_dashboard(session, status="PUBLISHED")
    mk_grant(session, d.id, "PUBLIC", "ALL", access_level="VIEW")
    override(viewer())
    assert client.post(start_url(d), json={}).status_code == 403
    assert executions(session) == []


def test_invalid_values_record_failed_and_400(client, session):
    d = setup_catalog(session)
    mk_list_def(session, "EMPTY", name="Empty")
    mk_param(session, d.id, "n", label="Top", data_type="NUMBER", is_required=True)
    mk_param(session, d.id, "b", label="Flag", data_type="BOOLEAN")
    mk_param(session, d.id, "dt", label="Day", data_type="DATE")
    mk_param(session, d.id, "g", label="Gran", list="GRANULARITY")
    override(viewer())
    cases = [
        ({}, "'Top' is required"),
        ({"n": "x"}, "'Top' must be a number"),
        ({"n": "1", "b": "maybe"}, "'Flag' must be 'true' or 'false'"),
        ({"n": "1", "dt": "2026-13-01"}, "'Day' must be a date"),
        ({"n": "1", "g": "YEAR"}, "'Gran' must be one of its list's values"),
        ({"n": "1" * 1001}, "at most 1000"),
    ]
    for values, message in cases:
        r = client.post(start_url(d), json={"values": values})
        assert r.status_code == 400, values
        assert message in r.json()["error"]["message"]
        row = executions(session, d.id)[-1]
        assert row.status == "FAILED" and message in row.error_message
    assert len(executions(session, d.id)) == len(cases)


def test_required_list_without_values_cannot_run(client, session):
    d = setup_catalog(session)
    mk_list_def(session, "EMPTY", name="Empty")
    mk_param(session, d.id, "e", label="Empty", list="EMPTY", is_required=True, default_value="X")
    override(viewer())
    r = client.post(start_url(d), json={})
    assert r.status_code == 400 and "cannot be run" in r.json()["error"]["message"]
    assert executions(session, d.id)[0].status == "FAILED"


# ── Finish (US3) ─────────────────────────────────────────────────────────────

def _started(client, session, d):
    return data(client.post(start_url(d), json={}))["execution_id"]


def test_finish_once_by_owner(client, session):
    d = setup_catalog(session)
    mk_grant(session, d.id, "USER", "2", access_level="VIEW")
    override(viewer(id=1))
    exec_id = _started(client, session, d)

    override(viewer(id=2))
    assert client.post(finish_url(exec_id), json={"status": "SUCCESS"}).status_code == 403

    override(viewer(id=1))
    assert client.post(finish_url(exec_id), json={"status": "DONE"}).status_code == 400
    assert client.post(finish_url(exec_id), json={"status": "UNAUTHORIZED"}).status_code == 400
    r = client.post(finish_url(exec_id), json={"status": "timeout", "error_message": "x" * 2000})
    assert r.status_code == 200
    body = data(r)
    assert body["status"] == "TIMEOUT" and body["duration_ms"] >= 0
    assert len(body["error_message"]) == 1000
    assert client.post(finish_url(exec_id), json={"status": "SUCCESS"}).status_code == 409
    assert client.post(finish_url(999999), json={"status": "SUCCESS"}).status_code == 404


def test_duration_is_computed_by_the_server(client, session):
    d = setup_catalog(session)
    row = Execution(dashboard=d.id, user_id=1, status=None,
                    executed_at=datetime.utcnow() - timedelta(seconds=5))
    session.add(row)
    session.commit()
    override(viewer())
    body = data(client.post(finish_url(row.id), json={"status": "SUCCESS"}))
    assert 4500 <= body["duration_ms"] < 60_000


# ── Cancelled window (US3) ───────────────────────────────────────────────────

def test_cancelled_window(client, session):
    d = setup_catalog(session)
    mk_param(session, d.id, "p")
    override(viewer())
    url = f"/api/dashboards/{d.id}/executions/cancelled"
    r = client.post(url, json={"values": {"p": "v", "other": "x"}, "duration_ms": 8400})
    assert r.status_code == 201
    body = data(r)
    assert body["status"] == "CANCELLED" and body["duration_ms"] == 8400
    assert body["payload"] == {"values": {"p": "v"}}
    assert data(client.post(url, json={"duration_ms": -5}))["duration_ms"] == 0
    assert data(client.post(url, json={"duration_ms": 10**12}))["duration_ms"] == 86_400_000


def test_cancelled_without_grant_is_unauthorized(client, session):
    d = setup_catalog(session, grant=None)
    override(viewer())
    r = client.post(f"/api/dashboards/{d.id}/executions/cancelled", json={})
    assert r.status_code == 403
    assert executions(session, d.id)[0].status == "UNAUTHORIZED"


def test_no_update_or_delete_routes():
    paths = {(m, r.path) for r in app.routes for m in getattr(r, "methods", set())}
    assert not any(p.startswith("/api/executions/{execution_id}") and m in ("PUT", "PATCH", "DELETE")
                   for m, p in paths)
    assert ("POST", "/api/executions/{execution_id}/finish") in paths


def test_superuser_can_run_ungranted_published(client, session):
    seed_ana_lists(session)
    d = mk_dashboard(session, status="PUBLISHED")
    override(user(99, superuser=True, profile="ADMINISTRATOR"))
    assert client.post(start_url(d), json={}).status_code == 201
