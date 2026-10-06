"""Usage Metrics — dashboards table and top errors
(specs/008-usage-metrics US3: FR-011/FR-012)."""
from datetime import timedelta

from tests.usage_helpers import (
    URL, admin, analyst, at, data, mk_dashboard, mk_grant, override, period, run,
    seed_usage, today,
)


def rows(client, qs=None):
    r = client.get(f"{URL}?{qs or period()}")
    assert r.status_code == 200, r.text
    return data(r)["dashboards"]


def errors(client, dashboard_id, extra=""):
    return client.get(f"/api/usage/dashboards/{dashboard_id}/errors?{period()}{extra}")


def test_rows_figures_order_and_current_status(client, session):
    seed_usage(session)
    override(admin())
    a = mk_dashboard(session, name="Alpha", status="PUBLISHED", type="REPORT",
                     sources_types="LOOKER_STUDIO")
    b = mk_dashboard(session, name="Beta", status="ARCHIVED")
    for ms in (100, 200, 300):
        run(session, a.id, user_id=1, status="SUCCESS", duration_ms=ms)
    run(session, a.id, user_id=2, status="FAILED")
    run(session, a.id, user_id=3, status="CANCELLED")
    run(session, b.id, user_id=1, status="SUCCESS", when=at(today() - timedelta(days=3)))
    out = rows(client)
    assert [r["name"] for r in out] == ["Alpha", "Beta"]
    alpha = out[0]
    assert alpha == {**alpha, "type": "REPORT", "source": "LOOKER_STUDIO", "status": "PUBLISHED",
                     "runs": 4, "attempts": 1, "users": 2, "success_rate": 0.75,
                     "median_ms": 200, "unused": False}
    assert out[1]["status"] == "ARCHIVED" and out[1]["runs"] == 1
    assert out[1]["last_run_at"].startswith((today() - timedelta(days=3)).isoformat()[:8])


def test_attempt_only_dashboard_and_unused_rows(client, session):
    seed_usage(session)
    override(admin())
    used = mk_dashboard(session, name="Used", status="PUBLISHED")
    refused = mk_dashboard(session, name="Refused", status="PUBLISHED")
    mk_dashboard(session, name="Idle", status="PUBLISHED")
    mk_dashboard(session, name="Draft", status="DRAFT")
    mk_dashboard(session, name="Gone", status="PUBLISHED", is_active=False)
    run(session, used.id)
    run(session, refused.id, status="UNAUTHORIZED")
    out = rows(client)
    by_name = {r["name"]: r for r in out}
    assert by_name["Refused"]["runs"] == 0 and by_name["Refused"]["unused"] is False
    assert by_name["Refused"]["last_run_at"] is None
    assert by_name["Idle"]["unused"] is True and by_name["Idle"]["runs"] == 0
    assert "Draft" not in by_name and "Gone" not in by_name
    assert [r["name"] for r in out] == ["Used", "Refused", "Idle"]


def test_rows_follow_scope(client, session):
    seed_usage(session)
    mine = mk_dashboard(session, name="Mine", status="PUBLISHED")
    mine_idle = mk_dashboard(session, name="Mine idle", status="PUBLISHED")
    other = mk_dashboard(session, name="Other", status="PUBLISHED")
    mk_dashboard(session, name="Other idle", status="PUBLISHED")
    for d in (mine, mine_idle):
        mk_grant(session, d.id, "USER", "1", "MANAGE")
    run(session, mine.id, user_id=5)
    run(session, other.id, user_id=5)
    override(analyst())
    assert [r["name"] for r in rows(client)] == ["Mine", "Mine idle"]


def test_errors_ranked_with_statuses(client, session):
    seed_usage(session)
    override(admin())
    d = mk_dashboard(session, status="PUBLISHED")
    for _ in range(3):
        run(session, d.id, status="FAILED", error="Popup blocked")
    run(session, d.id, status="TIMEOUT", error="Did not load within 30 s")
    run(session, d.id, status="UNAUTHORIZED", error="Access to dashboard 1 is not granted.")
    run(session, d.id, status="FAILED", error="   ")                       # blank: ignored
    run(session, d.id, status="FAILED", error="Popup blocked",
        when=at(today() - timedelta(days=60)))                             # outside period
    r = errors(client, d.id)
    assert r.status_code == 200, r.text
    b = data(r)
    assert b["total_with_error"] == 5
    assert b["items"][0] == {"message": "Popup blocked", "count": 3, "statuses": ["FAILED"]}
    assert [i["message"] for i in b["items"][1:]] == [
        "Access to dashboard 1 is not granted.", "Did not load within 30 s"]
    assert len(data(errors(client, d.id, "&limit=1"))["items"]) == 1
    assert errors(client, d.id, "&limit=0").status_code == 422
    assert errors(client, d.id, "&limit=51").status_code == 422


def test_errors_not_found_outside_scope(client, session):
    seed_usage(session)
    hidden = mk_dashboard(session, status="PUBLISHED")
    mk_grant(session, hidden.id, "USER", "1", "VIEW")
    run(session, hidden.id, status="FAILED", error="Popup blocked")
    override(analyst())
    outside = errors(client, hidden.id)
    missing = errors(client, 9999)
    assert outside.status_code == missing.status_code == 404
    assert outside.json() == missing.json()
