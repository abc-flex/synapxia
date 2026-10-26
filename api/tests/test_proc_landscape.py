"""Process landscape — Value Chain + Process Map (specs/010-process-landscape-views).

The shared read `GET /api/processes/landscape` and the panel read
`GET /api/processes/landscape/{code}`: gated by PROC/VALUE_CHAIN or PROC/MAP
(never PROC/PROCESSES), Deprecated and removed processes hidden, distinct
rolled-up counts, chain order from PRECEDES, unit filter, cap, constant
query count.
"""
from sqlalchemy import event

from app.auth.routes import current_active_user
from app.main import app
from app.workflows.internal import landscape_service
from tests.proc_helpers import (
    BASE, data, initiative, mk_asset, mk_asset_link, mk_init_link, mk_process,
    mk_relation, mk_unit, mk_user_row, override, seed_privileges, seed_proc_lists,
    seed_view_privileges, superuser, user,
)

LANDSCAPE = f"{BASE}/landscape"
VIEWER = "COLLABORATOR"


def viewer(session, options=("VALUE_CHAIN", "MAP"), uid=5):
    """A view-only caller (no PROC/PROCESSES), with lists, a unit and an owner row."""
    seed_view_privileges(session, VIEWER, options)
    seed_proc_lists(session)
    mk_unit(session, "ENG", "Engineering")
    mk_user_row(session, 1)
    override(user(uid, profile=VIEWER))


def seed_chain(session):
    """The seed's shape: five primaries chained by PRECEDES (inserted out of
    order), two supports with SUPPORTS links, two sub-processes."""
    for code in ("SERV", "OUTL", "INBL", "MKTS", "OPER"):
        mk_process(session, code, "PRIMARY", status="PUBLISHED", unit="ENG")
    for code in ("TECH", "HRMG"):
        mk_process(session, code, "SUPPORT", status="PUBLISHED", unit="ENG")
    mk_process(session, "OPER-DEV", "PRIMARY", parent="OPER", status="PUBLISHED", unit="ENG")
    mk_process(session, "OPER-QA", "PRIMARY", parent="OPER", status="PUBLISHED", unit="ENG")
    for s, t in (("INBL", "OPER"), ("OPER", "OUTL"), ("OUTL", "MKTS"), ("MKTS", "SERV")):
        mk_relation(session, s, t, "PRECEDES", rationale=f"{s} then {t}")
    mk_relation(session, "TECH", "OPER", "SUPPORTS", rationale="tech helps ops")
    mk_relation(session, "HRMG", "OPER", "SUPPORTS")


def by_code(body):
    return {p["code"]: p for p in body["processes"]}


# ── Access (contract table) ──────────────────────────────────────────────────


def test_no_token_is_401(client, session):
    app.dependency_overrides.pop(current_active_user, None)
    assert client.get(LANDSCAPE).status_code == 401
    assert client.get(f"{LANDSCAPE}/P1").status_code == 401


def test_process_management_alone_is_403(client, session):
    seed_privileges(session, "ADMINISTRATIVE", can_edit=True)   # PROC/PROCESSES only
    seed_proc_lists(session)
    mk_process(session, "P1", status="PUBLISHED")
    override(user(1, profile="ADMINISTRATIVE"))
    assert client.get(LANDSCAPE).status_code == 403
    assert client.get(f"{LANDSCAPE}/P1").status_code == 403


def test_either_view_privilege_is_enough(client, session):
    seed_proc_lists(session)
    mk_process(session, "P1", status="PUBLISHED")
    for profile, option in (("COLLABORATOR", "VALUE_CHAIN"), ("REVIEWER", "MAP")):
        seed_view_privileges(session, profile, (option,))
        override(user(5, profile=profile))
        body = data(client.get(LANDSCAPE))
        assert body["can_value_chain"] is (option == "VALUE_CHAIN")
        assert body["can_map"] is (option == "MAP")
        assert body["can_manage"] is False
        assert client.get(f"{LANDSCAPE}/P1").status_code == 200


def test_superuser_and_manage_flag(client, session):
    seed_proc_lists(session)
    mk_process(session, "P1", status="PUBLISHED")
    override(superuser())
    body = data(client.get(LANDSCAPE))
    assert body["can_value_chain"] and body["can_map"] and body["can_manage"]


def test_manage_flag_for_view_plus_management(client, session):
    seed_privileges(session, "ADMINISTRATIVE", can_edit=False)
    seed_view_privileges(session, "ADMINISTRATIVE")
    seed_proc_lists(session)
    override(user(1, profile="ADMINISTRATIVE"))
    assert data(client.get(LANDSCAPE))["can_manage"] is True


def test_no_write_methods(client, session):
    """Nothing under /landscape writes: PUT/DELETE fall through to Process
    Management's `/{code}` routes, which refuse a view-only caller."""
    viewer(session)
    mk_process(session, "P1", status="PUBLISHED")
    for method in ("post", "put", "delete"):
        for url in (LANDSCAPE, f"{LANDSCAPE}/P1"):
            assert getattr(client, method)(url).status_code in (403, 404, 405), (method, url)
    assert data(client.get(f"{LANDSCAPE}/P1"))["name"] == "P1"


def test_landscape_is_not_captured_by_process_code_route(client, session):
    """`/api/processes/{code}` needs PROC/PROCESSES; a view-only caller must
    reach the landscape route instead (router order in main.py)."""
    viewer(session)
    assert client.get(LANDSCAPE).status_code == 200
    assert client.get(f"{BASE}/LANDSCAPE").status_code == 403


# ── Shown rule and counts ────────────────────────────────────────────────────


def test_deprecated_and_removed_are_hidden(client, session):
    viewer(session)
    mk_process(session, "A", status="DRAFT")
    mk_process(session, "B", status="REVIEW")
    mk_process(session, "C", status="PUBLISHED")
    mk_process(session, "D", status="DEPRECATED")
    mk_process(session, "E", status="PUBLISHED", active=False)
    mk_relation(session, "A", "C", "PRECEDES")
    mk_relation(session, "C", "D", "PRECEDES")
    mk_relation(session, "C", "E", "PRECEDES")
    mk_relation(session, "A", "B", "PRECEDES", active=False)
    body = data(client.get(LANDSCAPE))
    assert sorted(by_code(body)) == ["A", "B", "C"]
    assert by_code(body)["A"]["status"] == "DRAFT"
    assert [(r["source"], r["target"]) for r in body["relations"]] == [("A", "C")]


def test_rolled_up_distinct_counts(client, session):
    viewer(session)
    seed_chain(session)
    mk_asset(session, 1)
    mk_asset(session, 2)
    mk_asset(session, 3, active=False)
    initiative(session, 1)
    initiative(session, 2, active=False)
    mk_asset_link(session, "OPER", 1)
    mk_asset_link(session, "OPER-DEV", 1)                 # same asset → counted once
    mk_asset_link(session, "OPER-DEV", 1, type="USED_BY")  # same asset, other type
    mk_asset_link(session, "OPER-QA", 2)
    mk_asset_link(session, "OPER-QA", 3)                   # inactive asset
    mk_asset_link(session, "SERV", 2, active=False)        # inactive link
    mk_init_link(session, "OPER-QA", 1)
    mk_init_link(session, "TECH", 2)                       # inactive initiative
    p = by_code(data(client.get(LANDSCAPE)))
    assert (p["OPER"]["own_assets"], p["OPER"]["assets"]) == (1, 2)
    assert (p["OPER"]["own_inits"], p["OPER"]["inits"]) == (0, 1)
    assert (p["OPER-DEV"]["own_assets"], p["OPER-DEV"]["assets"]) == (1, 1)
    assert (p["OPER-QA"]["assets"], p["OPER-QA"]["inits"]) == (1, 1)
    assert p["SERV"]["assets"] == 0 and p["TECH"]["inits"] == 0
    assert p["SERV"]["is_opportunity"] is True
    assert p["TECH"]["is_opportunity"] is True
    assert p["OPER"]["is_opportunity"] is False
    assert p["OPER-DEV"]["is_opportunity"] is False


def test_deprecated_descendants_do_not_count(client, session):
    viewer(session)
    mk_process(session, "TOP", status="PUBLISHED")
    mk_process(session, "OLD", parent="TOP", status="DEPRECATED")
    mk_asset(session, 1)
    mk_asset_link(session, "OLD", 1)
    p = by_code(data(client.get(LANDSCAPE)))
    assert "OLD" not in p and p["TOP"]["assets"] == 0 and p["TOP"]["is_opportunity"]


def test_display_parent_skips_hidden_ancestors(client, session):
    viewer(session)
    mk_process(session, "ROOT", status="PUBLISHED")
    mk_process(session, "MID", parent="ROOT", status="DEPRECATED")
    mk_process(session, "LEAF", parent="MID", status="PUBLISHED")
    mk_process(session, "ORPHAN-P", status="DEPRECATED")
    mk_process(session, "ORPHAN", parent="ORPHAN-P", status="PUBLISHED")
    p = by_code(data(client.get(LANDSCAPE)))
    assert (p["LEAF"]["parent"], p["LEAF"]["display_parent"], p["LEAF"]["depth"]) == ("MID", "ROOT", 1)
    assert (p["ORPHAN"]["display_parent"], p["ORPHAN"]["depth"]) == (None, 0)
    assert p["ROOT"]["child_order"] == ["LEAF"]


# ── Chain order ──────────────────────────────────────────────────────────────


def test_chain_order_follows_precedes(client, session):
    viewer(session)
    seed_chain(session)
    body = data(client.get(LANDSCAPE))
    assert body["primary_order"] == ["INBL", "OPER", "OUTL", "MKTS", "SERV"]
    assert body["support_order"] == ["HRMG", "TECH"]


def test_chain_order_isolated_and_cycles():
    order = landscape_service.chain_order
    assert order(["Z", "A", "M"], []) == ["A", "M", "Z"]
    # connected first (flow order), isolated after by code
    assert order(["A", "B", "C", "X"], [("C", "B")]) == ["C", "B", "A", "X"]
    # cycle A→B→C→A: each once, entered at the smallest code
    assert order(["C", "B", "A"], [("A", "B"), ("B", "C"), ("C", "A")]) == ["A", "B", "C"]
    # a cycle reached from outside: D precedes B
    assert order(["A", "B", "C", "D"], [("D", "B"), ("B", "C"), ("C", "B")]) == ["D", "B", "C", "A"]
    # edges with an end outside the group are ignored
    assert order(["A", "B"], [("Q", "A"), ("B", "A")]) == ["B", "A"]


def test_child_order_uses_sibling_precedes(client, session):
    viewer(session)
    mk_process(session, "P", status="PUBLISHED")
    for code in ("P-A", "P-B", "P-C"):
        mk_process(session, code, parent="P", status="PUBLISHED")
    mk_relation(session, "P-C", "P-A", "PRECEDES")
    p = by_code(data(client.get(LANDSCAPE)))
    assert p["P"]["child_order"] == ["P-C", "P-A", "P-B"]


# ── Unit filter, cap, performance ────────────────────────────────────────────


def test_unit_filter_keeps_context_ancestors(client, session):
    viewer(session)
    mk_unit(session, "CORP", "Corporate")
    mk_process(session, "TOP", status="PUBLISHED", unit="ENG")
    mk_process(session, "TOP-HR", parent="TOP", status="PUBLISHED", unit="CORP")
    mk_process(session, "TOP-DEV", parent="TOP", status="PUBLISHED", unit="ENG")
    mk_process(session, "FIN", status="PUBLISHED", unit="CORP")
    mk_asset(session, 1)
    mk_asset_link(session, "TOP-DEV", 1)
    body = data(client.get(LANDSCAPE, params={"unit": "CORP"}))
    p = by_code(body)
    assert sorted(p) == ["FIN", "TOP", "TOP-HR"]
    assert p["TOP"]["context"] is True and p["TOP-HR"]["context"] is False
    assert p["TOP"]["assets"] == 0          # TOP-DEV is not shown
    assert p["TOP"]["unit_name"] == "Engineering"
    assert body["unit"] == "CORP"


def test_unknown_unit_is_400(client, session):
    viewer(session)
    mk_unit(session, "OLD", active=False)
    assert client.get(LANDSCAPE, params={"unit": "NOPE"}).status_code == 400
    assert client.get(LANDSCAPE, params={"unit": "OLD"}).status_code == 400


def test_cap_truncates_by_code(client, session, monkeypatch):
    viewer(session)
    monkeypatch.setattr(landscape_service, "LANDSCAPE_MAX_PROCESSES", 3)
    for code in ("E", "D", "C", "B", "A"):
        mk_process(session, code, status="PUBLISHED")
    body = data(client.get(LANDSCAPE))
    assert sorted(by_code(body)) == ["A", "B", "C"] and body["truncated"] is True


def test_constant_query_count(client, session):
    viewer(session)
    for i in range(1, 6):
        mk_asset(session, i)
        initiative(session, i)
    tops = [f"T{i:02d}" for i in range(30)]
    for i, top in enumerate(tops):
        mk_process(session, top, "PRIMARY" if i % 2 else "SUPPORT", status="PUBLISHED", unit="ENG")
        for j in range(9):
            mk_process(session, f"{top}-{j}", "PRIMARY", parent=top, status="PUBLISHED", unit="ENG")
    codes = tops + [f"{t}-{j}" for t in tops for j in range(9)]
    links = set()
    for k in range(600):
        s, t = codes[k % len(codes)], codes[(k * 7 + 3) % len(codes)]
        kind = ("TRIGGERS", "CALLS", "FEEDS_INTO", "GOVERNS")[k % 4]
        if s != t and (s, t, kind) not in links:
            links.add((s, t, kind))
            mk_relation(session, s, t, kind)
    for k, code in enumerate(codes):
        mk_asset_link(session, code, k % 5 + 1)
        mk_init_link(session, code, k % 5 + 1)

    statements = []
    engine = session.get_bind()
    listener = lambda *args: statements.append(args[2])  # noqa: E731
    event.listen(engine, "before_cursor_execute", listener)
    try:
        body = data(client.get(LANDSCAPE))
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    assert len(body["processes"]) == 300
    assert len(statements) <= 12, statements


# ── Detail panel ─────────────────────────────────────────────────────────────


def test_detail_relations_and_links(client, session):
    viewer(session)
    seed_chain(session)
    mk_process(session, "GONE", status="DEPRECATED")
    mk_relation(session, "OPER", "GONE", "FEEDS_INTO")
    mk_relation(session, "SERV", "OPER", "INTERACTS_WITH", rationale="talk")
    mk_asset(session, 1, name="Prompt", category="PROMPTS")
    mk_asset(session, 2, active=False)
    initiative(session, 1, name="Init one")
    mk_asset_link(session, "OPER", 1)
    mk_asset_link(session, "OPER-DEV", 1, type="USED_BY")
    mk_asset_link(session, "OPER-QA", 2)
    mk_init_link(session, "OPER-QA", 1)

    d = data(client.get(f"{LANDSCAPE}/OPER"))
    assert d["name"] == "OPER" and d["unit_name"] == "Engineering"
    outgoing = {(r["other"], r["type"]) for r in d["outgoing"]}
    incoming = {(r["other"], r["type"]) for r in d["incoming"]}
    assert outgoing == {("OUTL", "PRECEDES"), ("SERV", "INTERACTS_WITH")}
    assert incoming == {("INBL", "PRECEDES"), ("TECH", "SUPPORTS"), ("HRMG", "SUPPORTS")}
    inter = next(r for r in d["outgoing"] if r["type"] == "INTERACTS_WITH")
    assert inter["directed"] is False and inter["rationale"] == "talk"
    tech = next(r for r in d["incoming"] if r["other"] == "TECH")
    assert tech["other_type"] == "SUPPORT" and tech["rationale"] == "tech helps ops"
    assert sorted((a["asset"], a["type"], a["via"]) for a in d["assets"]) == [
        (1, "RELATED_TO", None), (1, "USED_BY", "OPER-DEV")]
    assert d["assets"][0]["asset_name"] == "Prompt" and d["assets"][0]["category"] == "PROMPTS"
    assert [(i["init"], i["init_name"], i["via"]) for i in d["inits"]] == [(1, "Init one", "OPER-QA")]

    # the undirected link shows once from the other end too, still in `outgoing`
    s = data(client.get(f"{LANDSCAPE}/SERV"))
    assert ("OPER", "INTERACTS_WITH") in {(r["other"], r["type"]) for r in s["outgoing"]}
    assert "INTERACTS_WITH" not in {r["type"] for r in s["incoming"]}


def test_detail_hidden_is_404(client, session):
    viewer(session)
    mk_process(session, "OLD", status="DEPRECATED")
    mk_process(session, "GONE", status="PUBLISHED", active=False)
    for code in ("OLD", "GONE", "NOPE"):
        assert client.get(f"{LANDSCAPE}/{code}").status_code == 404, code
