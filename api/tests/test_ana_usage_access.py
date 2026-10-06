"""Usage Metrics — gate, scope, validation and no-leak
(specs/008-usage-metrics, FR-001/FR-002/FR-004/FR-015, research R4)."""
from datetime import datetime, timedelta

from tests.usage_helpers import (
    URL, admin, analyst, data, mk_assignment, mk_dashboard, mk_grant, mk_team, mk_unit,
    mk_user, override, period, run, seed_privileges, seed_usage, superuser, today, user,
)


def metrics(client, qs=None):
    return client.get(f"{URL}?{qs or period()}")


def test_requires_token(client, session):
    seed_usage(session)  # no override(): the real JWT dependency answers
    assert metrics(client).status_code == 401


def test_requires_usage_privilege(client, session):
    seed_usage(session)
    seed_privileges(session, profile="COLLABORATOR", options=("CATALOG",), can_edit=False)
    override(user(id=7, profile="COLLABORATOR"))
    assert metrics(client).status_code == 403


def test_administrator_and_superuser_see_everything(client, session):
    seed_usage(session)
    d1 = mk_dashboard(session, name="A", status="PUBLISHED")
    d2 = mk_dashboard(session, name="B", status="PUBLISHED")
    run(session, d1.id, user_id=2)
    run(session, d2.id, user_id=3)
    for who in (admin(), superuser()):
        override(who)
        r = metrics(client)
        assert r.status_code == 200, r.text
        body = data(r)
        assert body["scope"] == {"restricted": False, "dashboards": None}
        assert body["summary"]["current"]["runs"] == 2


def test_administrative_sees_only_managed_dashboards(client, session):
    seed_usage(session)
    mk_team(session, "ALPHA")
    mk_assignment(session, 1, "ALPHA", datetime.utcnow() - timedelta(days=30), role="TL")
    by_user = mk_dashboard(session, name="User", status="PUBLISHED")
    by_role = mk_dashboard(session, name="Role", status="PUBLISHED")
    by_team = mk_dashboard(session, name="Team", status="PUBLISHED")
    by_unit = mk_dashboard(session, name="Unit", status="PUBLISHED")
    view_only = mk_dashboard(session, name="View", status="PUBLISHED")
    revoked = mk_dashboard(session, name="Revoked", status="PUBLISHED")
    ungranted = mk_dashboard(session, name="None", status="PUBLISHED")
    mk_grant(session, by_user.id, "USER", "1", "MANAGE")
    mk_grant(session, by_role.id, "ROLE", "TL", "MANAGE")
    mk_grant(session, by_team.id, "TEAM", "ALPHA", "MANAGE")
    mk_grant(session, by_unit.id, "UNIT", "ENG", "MANAGE")
    mk_grant(session, view_only.id, "PUBLIC", "ALL", "VIEW")
    mk_grant(session, revoked.id, "USER", "1", "MANAGE",
             valid_to=datetime.utcnow() - timedelta(hours=1))
    for d in (by_user, by_role, by_team, by_unit, view_only, revoked, ungranted):
        run(session, d.id, user_id=9)

    override(analyst())
    body = data(metrics(client))
    assert body["scope"] == {"restricted": True, "dashboards": 4}
    assert body["summary"]["current"]["runs"] == 4
    assert body["summary"]["current"]["dashboards"] == 4


def test_administrative_without_manage_gets_empty_figures(client, session):
    seed_usage(session)
    d = mk_dashboard(session, status="PUBLISHED")
    mk_grant(session, d.id, "USER", "1", "VIEW")
    run(session, d.id, user_id=1)
    override(analyst())
    r = metrics(client)
    assert r.status_code == 200
    body = data(r)
    assert body["scope"] == {"restricted": True, "dashboards": 0}
    assert body["summary"]["current"]["runs"] == 0
    assert body["summary"]["current"]["success_rate"] is None


def test_period_validation(client, session):
    seed_usage(session)
    mk_unit(session, "ENG")
    mk_team(session, "ALPHA")
    override(admin())
    t = today()
    bad = [
        "date_from=2026-01-01",                                        # missing date_to
        "date_from=2026-13-01&date_to=2026-12-31",                     # malformed
        f"date_from={t}&date_to={t - timedelta(days=1)}",              # inverted
        f"date_from={t - timedelta(days=732)}&date_to={t}",            # > 24 months
        f"date_from={t}&date_to={t + timedelta(days=2)}",              # beyond tomorrow
        f"{period()}&unit=ENG&team=ALPHA",                             # both filters
        f"{period()}&unit=NOPE",                                       # unknown unit
        f"{period()}&team=NOPE",                                       # unknown team
    ]
    for qs in bad:
        r = metrics(client, qs)
        assert r.status_code in (400, 422), (qs, r.status_code)
        if "date_to" in qs and "date_from" in qs:
            assert r.status_code == 400, (qs, r.text)
    assert metrics(client, f"date_from={t - timedelta(days=731)}&date_to={t}").status_code == 200
    assert metrics(client, f"{period()}&unit=ENG").status_code == 200
    assert metrics(client, f"{period()}&team=__none__").status_code == 200


def _keys(obj, found):
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k)
            _keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _keys(v, found)
    return found


def test_no_individual_data_leaks(client, session):
    seed_usage(session)
    mk_unit(session, "ENG")
    mk_user(session, 2)
    d = mk_dashboard(session, status="PUBLISHED")
    run(session, d.id, user_id=2, status="FAILED", error="Popup blocked")
    override(admin())
    keys = _keys(data(metrics(client)), set())
    assert not keys & {"user_id", "payload", "error_message"}
