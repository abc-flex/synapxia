"""Last values — `GET /api/dashboards/{id}/executions/last-values`
(specs/007-dashboard-catalog FR-009a)."""
from datetime import datetime, timedelta

from tests.catalog_helpers import (
    data, mk_dashboard, mk_execution, mk_grant, mk_param, override, setup_catalog, viewer,
)


def url(d):
    return f"/api/dashboards/{d.id}/executions/last-values"


def test_empty_without_history(client, session):
    d = setup_catalog(session)
    override(viewer())
    assert data(client.get(url(d))) == {"values": {}, "executed_at": None}


def test_newest_success_of_the_caller_only(client, session):
    d = setup_catalog(session)
    mk_param(session, d.id, "q")
    old = datetime.utcnow() - timedelta(days=2)
    mk_execution(session, d.id, 1, "SUCCESS", {"values": {"q": "old"}}, executed_at=old)
    mk_execution(session, d.id, 1, "SUCCESS", {"values": {"q": "mine"}},
                 executed_at=old + timedelta(days=1))
    mk_execution(session, d.id, 1, "FAILED", {"values": {"q": "failed"}})
    mk_execution(session, d.id, 1, "CANCELLED", {"values": {"q": "cancel"}})
    mk_execution(session, d.id, 1, None, {"values": {"q": "running"}})
    mk_execution(session, d.id, 2, "SUCCESS", {"values": {"q": "theirs"}})
    override(viewer())
    body = data(client.get(url(d)))
    assert body["values"] == {"q": "mine"} and body["executed_at"]


def test_rules_against_current_parameters(client, session):
    d = setup_catalog(session, grant=("PUBLIC", "ALL"))
    unit = mk_grant(session, d.id, "UNIT", "ENG", access_level="VIEW")
    mk_param(session, d.id, "unit", context_binding=unit.id)
    mk_param(session, d.id, "gran", list="GRANULARITY")
    mk_param(session, d.id, "top", data_type="NUMBER")
    mk_param(session, d.id, "removed", is_active=False)
    mk_param(session, d.id, "added_later", default_value="x")
    mk_execution(session, d.id, 1, "SUCCESS", {"values": {
        "unit": "OPS", "gran": "YEAR", "top": "10", "removed": "r", "gone": "g"}})
    override(viewer(unit="ENG"))
    # GRANT excluded, list value no longer valid excluded, removed/unknown skipped.
    assert data(client.get(url(d)))["values"] == {"top": "10"}


def test_legacy_flat_payload(client, session):
    d = setup_catalog(session)
    mk_param(session, d.id, "date_from", data_type="DATE")
    mk_execution(session, d.id, 1, "SUCCESS", {"date_from": "2026-04-01", "granularity": "WEEK"})
    override(viewer())
    assert data(client.get(url(d)))["values"] == {"date_from": "2026-04-01"}


def test_guards(client, session):
    setup_catalog(session)
    hidden = mk_dashboard(session, name="Hidden", status="PUBLISHED")
    override(viewer())
    assert client.get(url(hidden)).status_code == 403
    assert client.get("/api/dashboards/999999/executions/last-values").status_code == 404
