"""Process Management — Related processes (specs/009-process-management, US2).

PROCESS_RELATION_TYPE values, the SUPPORTS / PRECEDES compatibility rules,
undirected Interacts With, atomic replace and the type-change guard.
"""
import pytest
from sqlmodel import select

from app.workflows.internal import relation_rules as rules
from app.workflows.internal.models import RelatedProcess
from tests.proc_helpers import BASE, data, mk_process, mk_relation, setup


def _seed_chain(session):
    for code in ("INBL", "OPER", "OUTL", "MKTS", "SERV"):
        mk_process(session, code, type="PRIMARY")
    for code in ("TECH", "HRMG"):
        mk_process(session, code, type="SUPPORT")


def _put(client, code, *items):
    return client.put(f"{BASE}/{code}/relations", json={"relations": list(items)})


def _rows(session, source):
    session.expire_all()
    return session.exec(select(RelatedProcess).where(RelatedProcess.source == source)).all()


# ── Rules (pure) ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("rel,src,tgt,ok", [
    ("SUPPORTS", "SUPPORT", "PRIMARY", True),
    ("SUPPORTS", "SUPPORT", "SUPPORT", False),
    ("SUPPORTS", "PRIMARY", "PRIMARY", False),
    ("SUPPORTS", "PRIMARY", "SUPPORT", False),
    ("PRECEDES", "PRIMARY", "PRIMARY", True),
    ("PRECEDES", "SUPPORT", "SUPPORT", True),
    ("PRECEDES", "PRIMARY", "SUPPORT", False),
    ("GOVERNS", "PRIMARY", "SUPPORT", True),
    ("CALLS", "SUPPORT", "PRIMARY", True),
])
def test_compatibility(rel, src, tgt, ok):
    assert rules.is_compatible(rel, src, tgt) is ok
    if not ok:
        with pytest.raises(ValueError):
            rules.check_compatible(rel, src, tgt)


def test_pair_key_unordered_only_for_interacts_with():
    assert rules.pair_key("A", "B", "INTERACTS_WITH") == rules.pair_key("B", "A", "INTERACTS_WITH")
    assert rules.pair_key("A", "B", "PRECEDES") != rules.pair_key("B", "A", "PRECEDES")


# ── GET ─────────────────────────────────────────────────────────────────────

def test_get_outgoing_and_incoming_interacts(client, session):
    setup(session)
    _seed_chain(session)
    mk_process(session, "OLD", active=False)
    mk_relation(session, "OUTL", "MKTS", "PRECEDES", rationale="flow")
    mk_relation(session, "SERV", "OUTL", "INTERACTS_WITH")
    mk_relation(session, "OPER", "OUTL", "PRECEDES")          # incoming directed: not shown
    mk_relation(session, "OUTL", "OLD", "GOVERNS")
    mk_relation(session, "OUTL", "SERV", "CALLS", active=False)
    rows = data(client.get(f"{BASE}/OUTL/relations"))
    got = {(r["target"], r["type"], r["direction"]) for r in rows}
    assert got == {("MKTS", "PRECEDES", "outgoing"), ("SERV", "INTERACTS_WITH", "incoming"),
                   ("OLD", "GOVERNS", "outgoing")}
    old = next(r for r in rows if r["target"] == "OLD")
    assert old["target_active"] is False
    mkts = next(r for r in rows if r["target"] == "MKTS")
    assert mkts["target_name"] == "MKTS" and mkts["target_type"] == "PRIMARY"


# ── PUT replace ─────────────────────────────────────────────────────────────

def test_replace_inserts_updates_deactivates_and_reactivates(client, session):
    setup(session)
    _seed_chain(session)
    mk_relation(session, "OUTL", "MKTS", "PRECEDES", rationale="old")
    mk_relation(session, "OUTL", "SERV", "CALLS")
    mk_relation(session, "OUTL", "OPER", "FEEDS_INTO", active=False)
    created = {r.target: r.created_at for r in _rows(session, "OUTL")}

    r = _put(client, "OUTL",
             {"target": "MKTS", "type": "PRECEDES", "rationale": "new"},
             {"target": "OPER", "type": "FEEDS_INTO"},
             {"target": "INBL", "type": "TRIGGERS"})
    assert r.status_code == 200, r.text
    by = {(x.target, x.type): x for x in _rows(session, "OUTL")}
    assert by[("MKTS", "PRECEDES")].rationale == "new"
    assert by[("SERV", "CALLS")].is_active is False
    assert by[("OPER", "FEEDS_INTO")].is_active is True
    assert by[("OPER", "FEEDS_INTO")].created_at == created["OPER"]   # same row
    assert by[("INBL", "TRIGGERS")].is_active is True
    assert {(x["target"], x["type"]) for x in data(r)} == {
        ("MKTS", "PRECEDES"), ("OPER", "FEEDS_INTO"), ("INBL", "TRIGGERS")}


def test_same_pair_with_different_types_allowed(client, session):
    setup(session)
    _seed_chain(session)
    r = _put(client, "OUTL", {"target": "MKTS", "type": "PRECEDES"},
             {"target": "MKTS", "type": "FEEDS_INTO"})
    assert r.status_code == 200 and len(data(r)) == 2


@pytest.mark.parametrize("item", [
    {"target": "OUTL", "type": "CALLS"},              # self
    {"target": "NOPE", "type": "CALLS"},              # unknown
    {"target": "OLD", "type": "CALLS"},               # removed
    {"target": "MKTS", "type": "SIMILAR_TO"},         # shared list only
    {"target": "MKTS", "type": ""},                   # missing type
    {"target": "TECH", "type": "SUPPORTS"},           # Primary → Support
    {"target": "MKTS", "type": "SUPPORTS"},           # Primary → Primary
    {"target": "TECH", "type": "PRECEDES"},           # Primary → Support
])
def test_invalid_item_refused_atomically(client, session, item):
    setup(session)
    _seed_chain(session)
    mk_process(session, "OLD", active=False)
    mk_relation(session, "OUTL", "MKTS", "PRECEDES")
    r = _put(client, "OUTL", {"target": "SERV", "type": "CALLS"}, item)
    assert r.status_code == 400, r.text
    rows = _rows(session, "OUTL")
    assert [(x.target, x.type, x.is_active) for x in rows] == [("MKTS", "PRECEDES", True)]


def test_supports_from_support_to_primary_ok(client, session):
    setup(session)
    _seed_chain(session)
    assert _put(client, "TECH", {"target": "OPER", "type": "SUPPORTS"}).status_code == 200
    assert _put(client, "TECH", {"target": "HRMG", "type": "SUPPORTS"}).status_code == 400
    assert _put(client, "TECH", {"target": "HRMG", "type": "PRECEDES"}).status_code == 200


def test_duplicate_in_set_refused(client, session):
    setup(session)
    _seed_chain(session)
    assert _put(client, "OUTL", {"target": "MKTS", "type": "PRECEDES"},
                {"target": "mkts", "type": "PRECEDES"}).status_code == 400


def test_interacts_with_is_undirected(client, session):
    setup(session)
    _seed_chain(session)
    assert _put(client, "OUTL", {"target": "SERV", "type": "INTERACTS_WITH"}).status_code == 200
    incoming = data(client.get(f"{BASE}/SERV/relations"))
    assert [(r["target"], r["direction"]) for r in incoming] == [("OUTL", "incoming")]
    # SERV saving its set with the incoming link keeps the stored row as is.
    assert _put(client, "SERV", {"target": "OUTL", "type": "INTERACTS_WITH",
                                 "rationale": "both ways"}).status_code == 200
    session.expire_all()
    rows = session.exec(select(RelatedProcess)).all()
    assert [(r.source, r.target, r.rationale) for r in rows] == [("OUTL", "SERV", "both ways")]
    # Both orientations in one set are the same link → duplicate.
    assert _put(client, "OUTL", {"target": "SERV", "type": "INTERACTS_WITH"},
                {"target": "SERV", "type": "INTERACTS_WITH"}).status_code == 400
    # Removing it from the target side deactivates it.
    assert _put(client, "SERV").status_code == 200
    assert data(client.get(f"{BASE}/OUTL/relations")) == []


def test_unknown_process_is_404(client, session):
    setup(session)
    assert client.get(f"{BASE}/NOPE/relations").status_code == 404
    assert _put(client, "NOPE").status_code == 404


# ── Type-change guard ───────────────────────────────────────────────────────

def test_type_change_blocked_by_incompatible_links(client, session):
    setup(session)
    _seed_chain(session)
    mk_relation(session, "TECH", "OPER", "SUPPORTS")
    mk_relation(session, "TECH", "MKTS", "GOVERNS")
    r = client.put(f"{BASE}/TECH", json={"type": "PRIMARY"})
    assert r.status_code == 400
    assert "TECH SUPPORTS OPER" in r.json()["error"]["message"]
    assert "GOVERNS" not in r.json()["error"]["message"]
    assert _put(client, "TECH", {"target": "MKTS", "type": "GOVERNS"}).status_code == 200
    assert client.put(f"{BASE}/TECH", json={"type": "PRIMARY"}).status_code == 200


def test_type_change_checks_incoming_precedes(client, session):
    setup(session)
    _seed_chain(session)
    mk_relation(session, "INBL", "OPER", "PRECEDES")
    assert client.put(f"{BASE}/OPER", json={"type": "SUPPORT"}).status_code == 400
