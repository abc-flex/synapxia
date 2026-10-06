"""Usage Metrics — unit tree, hybrid teams, filter, adoption
(specs/008-usage-metrics US4: FR-005/FR-013/FR-014, research R7/R8)."""
from datetime import datetime, timedelta

from tests.usage_helpers import (
    URL, admin, analyst, at, data, mk_assignment, mk_dashboard, mk_grant, mk_project, mk_team,
    mk_unit,
    mk_user, override, period, run, seed_usage, today,
)
from app.insights.internal import usage_service

NOW = datetime.utcnow()


def metrics(client, extra=""):
    r = client.get(f"{URL}?{period()}{extra}")
    assert r.status_code == 200, r.text
    return data(r)


def flatten(nodes, depth=0, out=None):
    out = {} if out is None else out
    for n in nodes:
        out[n["code"]] = n
        flatten(n["children"], depth + 1, out)
    return out


def org(session):
    """CORP → ENG → {BACKEND, FRONTEND}; CORP → GTM → SALES; PEOPLE (no members)."""
    seed_usage(session)
    mk_unit(session, "CORP")
    mk_unit(session, "ENG", "CORP")
    mk_unit(session, "BACKEND", "ENG")
    mk_unit(session, "FRONTEND", "ENG")
    mk_unit(session, "GTM", "CORP")
    mk_unit(session, "SALES", "GTM")
    mk_unit(session, "PEOPLE", "CORP")
    mk_user(session, 1, "ENG")          # direct member of a parent unit
    mk_user(session, 2, "BACKEND")
    mk_user(session, 3, "BACKEND")
    mk_user(session, 4, "FRONTEND")
    mk_user(session, 5, "SALES")
    mk_user(session, 6, "SALES", active=False)   # not a member
    override(admin())
    return mk_dashboard(session, name="D", status="PUBLISHED")


def test_unit_tree_rolls_up(client, session):
    d = org(session)
    run(session, d.id, user_id=1)
    run(session, d.id, user_id=2)
    run(session, d.id, user_id=2, status="FAILED")
    run(session, d.id, user_id=5)
    run(session, d.id, user_id=5, status="CANCELLED")          # attempt: not counted
    units = flatten(metrics(client)["units"])
    assert "PEOPLE" not in units                              # no members, no runs
    corp, eng, backend = units["CORP"], units["ENG"], units["BACKEND"]
    assert (corp["members"], corp["runs"], corp["users"]) == (5, 4, 3)
    assert (eng["members"], eng["direct_members"], eng["runs"], eng["users"]) == (4, 1, 3, 2)
    assert (backend["members"], backend["runs"], backend["users"]) == (2, 2, 1)
    assert backend["success_rate"] == 0.5
    assert backend["adoption_rate"] == 0.5
    assert units["FRONTEND"]["runs"] == 0 and units["FRONTEND"]["adoption_rate"] == 0.0
    assert units["SALES"]["members"] == 1 and units["SALES"]["adoption_rate"] == 1.0
    assert [c["code"] for c in units["ENG"]["children"]] == ["BACKEND", "FRONTEND"]


def test_unit_parent_cycle_does_not_hang(client, session):
    seed_usage(session)
    mk_unit(session, "A", "B")
    mk_unit(session, "B", "A")
    mk_user(session, 1, "A")
    mk_user(session, 2, "B")
    override(admin())
    tree = metrics(client)["units"]
    assert [n["code"] for n in tree] == ["A"]                 # cycle broken once, at A
    assert [c["code"] for c in tree[0]["children"]] == ["B"]
    assert tree[0]["members"] == 2


def test_hybrid_team_attribution(client, session):
    d = org(session)
    mk_team(session, "ALPHA")
    mk_team(session, "BRAVO")
    t = today()
    # user 2: ALPHA until 10 days ago, BRAVO since → old run in ALPHA, new in BRAVO
    mk_assignment(session, 2, "ALPHA", NOW - timedelta(days=100), NOW - timedelta(days=10))
    mk_assignment(session, 2, "BRAVO", NOW - timedelta(days=10))
    run(session, d.id, user_id=2, when=at(t - timedelta(days=20)))
    run(session, d.id, user_id=2, when=at(t))
    # user 3: assignment created today only → an older run falls back to the current team
    mk_assignment(session, 3, "ALPHA", NOW - timedelta(minutes=5))
    run(session, d.id, user_id=3, when=at(t - timedelta(days=5)))
    # user 4: in both teams at run time → counts in both
    mk_assignment(session, 4, "ALPHA", NOW - timedelta(days=50))
    mk_assignment(session, 4, "BRAVO", NOW - timedelta(days=50))
    run(session, d.id, user_id=4, when=at(t - timedelta(days=1)))
    # user 5: no team at all
    run(session, d.id, user_id=5, when=at(t))
    teams = {r["code"]: r for r in metrics(client)["teams"]}
    assert (teams["ALPHA"]["runs"], teams["ALPHA"]["users"]) == (3, 3)
    assert (teams["BRAVO"]["runs"], teams["BRAVO"]["users"]) == (2, 2)
    assert teams["__none__"] == {**teams["__none__"], "runs": 1, "users": 1,
                                 "members": None, "adoption_rate": None}
    assert teams["ALPHA"]["members"] == 3                     # 2 (period overlap), 3, 4
    assert teams["BRAVO"]["members"] == 2
    assert teams["ALPHA"]["adoption_rate"] == 1.0


def test_unit_filter_narrows_other_sections_only(client, session):
    d = org(session)
    other = mk_dashboard(session, name="Sales board", status="PUBLISHED")
    run(session, d.id, user_id=2)
    run(session, d.id, user_id=4)
    run(session, other.id, user_id=5)
    b = metrics(client, "&unit=ENG")
    assert b["filter"] == {"unit": "ENG", "team": None, "project": None}
    assert b["summary"]["current"]["runs"] == 2
    assert sum(sum(x["outcomes"].values()) for x in b["timeline"]) == 2
    assert [r["name"] for r in b["dashboards"] if not r["unused"]] == ["D"]
    assert flatten(b["units"])["CORP"]["runs"] == 3           # adoption section not narrowed
    assert metrics(client, "&unit=SALES")["summary"]["current"]["runs"] == 1


def test_team_filter_matches_row_attribution(client, session):
    d = org(session)
    mk_team(session, "ALPHA")
    mk_assignment(session, 2, "ALPHA", NOW - timedelta(days=100), NOW - timedelta(days=10))
    run(session, d.id, user_id=2, when=at(today() - timedelta(days=20)))   # ALPHA then
    run(session, d.id, user_id=2, when=at(today()))                        # no team now
    run(session, d.id, user_id=5)
    alpha = metrics(client, "&team=ALPHA")
    assert alpha["summary"]["current"]["runs"] == 1
    none = metrics(client, "&team=__none__")
    assert none["summary"]["current"]["runs"] == 2
    teams = {r["code"]: r["runs"] for r in alpha["teams"]}
    assert teams == {"ALPHA": 1, "__none__": 2}


def test_errors_honour_filter(client, session):
    d = org(session)
    run(session, d.id, user_id=2, status="FAILED", error="Popup blocked")
    run(session, d.id, user_id=5, status="FAILED", error="Popup blocked")
    r = client.get(f"/api/usage/dashboards/{d.id}/errors?{period()}&unit=SALES")
    assert data(r)["total_with_error"] == 1


def test_scope_limits_runs_not_members(client, session):
    d = org(session)
    other = mk_dashboard(session, name="Other", status="PUBLISHED")
    mk_grant(session, d.id, "USER", "1", "MANAGE")
    run(session, d.id, user_id=2)
    run(session, other.id, user_id=3)
    override(analyst())
    units = flatten(metrics(client)["units"])
    assert units["BACKEND"]["runs"] == 1 and units["BACKEND"]["members"] == 2


def test_teams_for_run_unit():
    """The hybrid rule on its own: then → current → none."""
    class G(usage_service.Groups):
        def __init__(self):
            self.now = NOW
            self._current = {}
            self.assignments = {
                1: [("ALPHA", NOW - timedelta(days=30), NOW - timedelta(days=10)),
                    ("BRAVO", NOW - timedelta(days=1), None)]}
    g = G()
    assert g.teams_for_run(1, NOW - timedelta(days=20)) == ["ALPHA"]
    assert g.teams_for_run(1, NOW - timedelta(days=5)) == ["BRAVO"]   # gap → current
    assert g.teams_for_run(2, NOW) == [usage_service.NO_TEAM]


# ── Projects (adoption "By project", reached through the owning team) ───────


def test_project_attribution_follows_team_and_dates(client, session):
    d = org(session)
    mk_team(session, "ALPHA")
    mk_team(session, "BRAVO")
    t = today()
    mk_project(session, "P1", "ALPHA", name="Apollo")
    mk_project(session, "P2", "ALPHA", name="Borealis", start=t - timedelta(days=3))
    mk_project(session, "P3", "BRAVO", name="Comet")
    mk_project(session, "OLD", "BRAVO", name="Gone", active=False)
    mk_assignment(session, 2, "ALPHA", NOW - timedelta(days=100))
    mk_assignment(session, 3, "BRAVO", NOW - timedelta(days=100))
    run(session, d.id, user_id=2, when=at(t - timedelta(days=10)))   # P1 only (P2 not started)
    run(session, d.id, user_id=2, when=at(t))                        # P1 and P2
    run(session, d.id, user_id=3, when=at(t))                        # P3
    run(session, d.id, user_id=5, when=at(t))                        # no team → no project
    run(session, d.id, user_id=3, status="CANCELLED")                # attempt: not counted
    rows = {r["code"]: r for r in metrics(client)["projects"]}
    assert "OLD" not in rows
    assert (rows["P1"]["runs"], rows["P1"]["users"]) == (2, 1)
    assert rows["P1"] == {**rows["P1"], "name": "Apollo", "team": "ALPHA", "team_name": "Alpha",
                          "members": 1, "adoption_rate": 1.0}
    assert rows["P2"]["runs"] == 1
    assert rows["P3"]["runs"] == 1 and rows["P3"]["members"] == 1
    assert rows["__none__"] == {**rows["__none__"], "runs": 1, "members": None,
                                "adoption_rate": None}


def test_project_filter_and_validation(client, session):
    d = org(session)
    mk_team(session, "ALPHA")
    mk_project(session, "P1", "ALPHA")
    mk_assignment(session, 2, "ALPHA", NOW - timedelta(days=100))
    run(session, d.id, user_id=2)
    run(session, d.id, user_id=5)
    b = metrics(client, "&project=P1")
    assert b["filter"]["project"] == "P1"
    assert b["summary"]["current"]["runs"] == 1
    assert metrics(client, "&project=__none__")["summary"]["current"]["runs"] == 1
    assert {r["code"]: r["runs"] for r in b["projects"]} == {"P1": 1, "__none__": 1}
    for qs in ("&project=NOPE", "&project=P1&team=ALPHA", "&project=P1&unit=ENG"):
        assert client.get(f"{URL}?{period()}{qs}").status_code == 400, qs
