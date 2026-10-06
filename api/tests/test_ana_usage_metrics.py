"""Usage Metrics — headline figures and timeline
(specs/008-usage-metrics US1/US2: FR-006/FR-007/FR-007a/FR-008/FR-010, research R3/R5/R9)."""
from datetime import date, datetime, time, timedelta

from tests.usage_helpers import (
    URL, admin, at, data, mk_dashboard, override, period, run, seed_usage, today, utc,
)
from app.insights.internal import usage_service


def body(client, qs=None):
    r = client.get(f"{URL}?{qs or period()}")
    assert r.status_code == 200, r.text
    return data(r)


def setup(session):
    seed_usage(session)
    override(admin())
    return mk_dashboard(session, name="D", status="PUBLISHED")


# ── US1: headline ────────────────────────────────────────────────────────────


def test_runs_exclude_cancelled_and_unauthorized(client, session):
    d = setup(session)
    for status in ("SUCCESS", "FAILED", "TIMEOUT", None, "CANCELLED", "UNAUTHORIZED"):
        run(session, d.id, user_id=1, status=status)
    run(session, d.id, user_id=2, status="CANCELLED")      # attempt only: not a user
    cur = body(client)["summary"]["current"]
    assert cur["runs"] == 4
    assert cur["attempts"] == 3
    assert cur["users"] == 1
    assert cur["incomplete"] == 1
    assert cur["outcomes"] == {"SUCCESS": 1, "FAILED": 1, "TIMEOUT": 1, "INCOMPLETE": 1,
                               "CANCELLED": 2, "UNAUTHORIZED": 1}


def test_success_rate_denominator(client, session):
    d = setup(session)
    for status in ("SUCCESS", "SUCCESS", "SUCCESS", "FAILED", "CANCELLED", None, "UNAUTHORIZED"):
        run(session, d.id, status=status)
    assert body(client)["summary"]["current"]["success_rate"] == 0.75


def test_success_rate_null_without_real_outcomes(client, session):
    d = setup(session)
    run(session, d.id, status="CANCELLED")
    run(session, d.id, status=None)
    assert body(client)["summary"]["current"]["success_rate"] is None


def test_durations_use_successes_only(client, session):
    d = setup(session)
    for ms in (100, 300, 900):
        run(session, d.id, status="SUCCESS", duration_ms=ms)
    run(session, d.id, status="SUCCESS")                       # no duration: ignored
    run(session, d.id, status="TIMEOUT", duration_ms=30000)
    run(session, d.id, status="CANCELLED", duration_ms=50000)
    cur = body(client)["summary"]["current"]
    assert cur["median_ms"] == 300
    assert cur["avg_ms"] == 433
    run(session, d.id, status="SUCCESS", duration_ms=500)       # even count
    assert body(client)["summary"]["current"]["median_ms"] == 400


def test_distinct_users_and_dashboards(client, session):
    d = setup(session)
    d2 = mk_dashboard(session, name="E", status="PUBLISHED")
    run(session, d.id, user_id=1)
    run(session, d.id, user_id=1)
    run(session, d2.id, user_id=2)
    mk = mk_dashboard(session, name="F", status="PUBLISHED")
    run(session, mk.id, user_id=3, status="UNAUTHORIZED")       # not a run
    cur = body(client)["summary"]["current"]
    assert (cur["users"], cur["dashboards"]) == (2, 2)


def test_previous_period_and_change(client, session):
    d = setup(session)
    t = today()
    for _ in range(4):
        run(session, d.id, when=at(t), duration_ms=1000)
    for _ in range(2):
        run(session, d.id, when=at(t - timedelta(days=7)), status="FAILED")
    run(session, d.id, when=at(t - timedelta(days=7)), duration_ms=1200)
    # 7-day period: today-6..today. Previous: today-13..today-7.
    b = body(client, period(days=7))
    assert b["period"]["previous_to"] == (t - timedelta(days=7)).isoformat()
    s = b["summary"]
    assert (s["current"]["runs"], s["previous"]["runs"]) == (4, 3)
    assert s["change"]["runs"] == round(1 / 3, 4)
    assert s["change"]["success_rate"] == round(1.0 - 1 / 3, 4)
    assert s["change"]["median_ms"] == -200
    assert s["change"]["incomplete"] is None                   # previous 0


def test_local_day_boundaries(client, session):
    d = setup(session)
    t = today() - timedelta(days=1)
    run(session, d.id, when=utc(datetime.combine(t, time(23, 30))))            # inside
    run(session, d.id, when=utc(datetime.combine(t + timedelta(days=1), time(0, 10))))
    run(session, d.id, when=utc(datetime.combine(t - timedelta(days=1), time(23, 59))))
    b = body(client, f"date_from={t}&date_to={t}")
    assert b["summary"]["current"]["runs"] == 1
    assert b["summary"]["previous"]["runs"] == 1


def test_empty_period(client, session):
    setup(session)
    cur = body(client)["summary"]["current"]
    assert cur["runs"] == cur["attempts"] == cur["users"] == 0
    assert cur["success_rate"] is None and cur["median_ms"] is None


# ── US2: timeline ────────────────────────────────────────────────────────────


def test_bucket_thresholds():
    t = date(2026, 6, 30)
    def bucket(days):
        return usage_service.parse_period(
            (t - timedelta(days=days - 1)).isoformat(), t.isoformat(), today=t).bucket
    assert [bucket(31), bucket(32), bucket(183), bucket(184)] == ["day", "week", "week", "month"]


def test_week_and_month_ranges():
    p = usage_service.parse_period("2026-06-03", "2026-07-20", today=date(2026, 7, 20))
    ranges = usage_service.bucket_ranges(p)
    assert ranges[0] == (date(2026, 6, 3), date(2026, 6, 7))       # Wed..Sun, partial
    assert ranges[1] == (date(2026, 6, 8), date(2026, 6, 14))      # Monday start
    assert ranges[-1] == (date(2026, 7, 20), date(2026, 7, 20))
    m = usage_service.parse_period("2025-11-15", "2026-06-30", today=date(2026, 6, 30))
    months = usage_service.bucket_ranges(m)
    assert months[0] == (date(2025, 11, 15), date(2025, 11, 30))
    assert months[1] == (date(2025, 12, 1), date(2025, 12, 31))
    assert len(months) == 8


def test_timeline_buckets_are_complete_and_local(client, session):
    d = setup(session)
    t = today()
    start = t - timedelta(days=9)
    run(session, d.id, when=at(start, 20), status="SUCCESS")       # 20:00 local, stays on day
    run(session, d.id, when=at(t), status="CANCELLED")
    run(session, d.id, when=at(t), status=None)
    tl = body(client, f"date_from={start}&date_to={t}")["timeline"]
    assert len(tl) == 10
    assert tl[0]["start"] == start.isoformat() and tl[0]["outcomes"]["SUCCESS"] == 1
    assert all(sum(b["outcomes"].values()) == 0 for b in tl[1:-1])   # empty buckets → zeros
    assert tl[-1]["outcomes"]["CANCELLED"] == 1 and tl[-1]["outcomes"]["INCOMPLETE"] == 1


def test_timeline_month_placement_uses_local_time(client, session):
    d = setup(session)
    end = today()
    start = end - timedelta(days=300)
    last_of_month = (end.replace(day=1) - timedelta(days=1))
    run(session, d.id, when=at(last_of_month, 20))                  # 20:00 local on the 31st/30th
    tl = body(client, f"date_from={start}&date_to={end}")["timeline"]
    bucket = next(b for b in tl if b["start"] <= last_of_month.isoformat() <= b["end"])
    assert bucket["outcomes"]["SUCCESS"] == 1
    total = sum(sum(b["outcomes"].values()) for b in tl)
    assert total == 1
