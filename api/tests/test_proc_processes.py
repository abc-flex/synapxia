"""Process Management — `/api/processes` core CRUD, hierarchy and removal
(specs/009-process-management, US1) plus the all-or-nothing create (US5)."""
from sqlmodel import select

from app.workflows.internal.models import Process, ProcessAsset, ProcessInit, RelatedProcess
from tests.proc_helpers import (
    BASE, data, initiative, mk_asset, mk_process, mk_unit, setup,
)

BODY = {"code": "oper-qa", "name": "Quality Assurance", "type": "PRIMARY", "unit": "ENG"}


# ── List ────────────────────────────────────────────────────────────────────

def test_list_active_ordered_with_names(client, session):
    setup(session)
    mk_process(session, "OPER", name="Operations", unit="ENG")
    mk_process(session, "OPER-DEV", parent="OPER", name="Development")
    mk_process(session, "GONE", active=False)
    r = client.get(f"{BASE}/")
    assert r.status_code == 200
    rows = data(r)
    assert [p["code"] for p in rows] == ["OPER", "OPER-DEV"]
    assert rows[0]["unit_name"] == "Engineering"
    assert rows[1]["parent_name"] == "Operations"
    assert rows[0]["owner_name"] == "F L"


def test_list_filters_and_pagination(client, session):
    setup(session)
    mk_process(session, "A1", type="PRIMARY", status="DRAFT", description="alpha flow")
    mk_process(session, "B1", type="SUPPORT", status="PUBLISHED")
    mk_process(session, "C1", type="SUPPORT", status="DRAFT", unit="ENG")
    codes = lambda q: [p["code"] for p in data(client.get(f"{BASE}/{q}"))]  # noqa: E731
    assert codes("?type=SUPPORT") == ["B1", "C1"]
    assert codes("?type=SUPPORT&status=DRAFT") == ["C1"]
    assert codes("?unit=ENG") == ["C1"]
    assert codes("?q=ALPHA") == ["A1"]
    assert codes("?skip=1&limit=1") == ["B1"]
    assert client.get(f"{BASE}/?limit=501").status_code == 422


# ── Detail ──────────────────────────────────────────────────────────────────

def test_detail_has_allowed_statuses_and_404s(client, session):
    setup(session)
    mk_process(session, "R1", status="REVIEW")
    mk_process(session, "GONE", active=False)
    body = data(client.get(f"{BASE}/R1"))
    assert body["allowed_statuses"] == ["REVIEW", "PUBLISHED", "DRAFT"]
    assert client.get(f"{BASE}/NOPE").status_code == 404
    assert client.get(f"{BASE}/GONE").status_code == 404


# ── Create (core) ───────────────────────────────────────────────────────────

def test_create_draft_uppercased_owner_defaults_to_caller(client, session):
    setup(session)
    r = client.post(f"{BASE}/", json=BODY)
    assert r.status_code == 201, r.text
    body = data(r)
    assert body["code"] == "OPER-QA" and body["status"] == "DRAFT"
    assert body["owner"] == 1
    assert body["allowed_statuses"] == ["DRAFT", "REVIEW"]


def test_create_code_rules_and_duplicates(client, session):
    setup(session)
    mk_process(session, "OLD", active=False)
    for bad in ("", "  ", "has space", "-LEAD", "x" * 51, "ÑU"):
        assert client.post(f"{BASE}/", json={**BODY, "code": bad}).status_code == 400, bad
    assert client.post(f"{BASE}/", json=BODY).status_code == 201
    assert client.post(f"{BASE}/", json=BODY).status_code == 409
    # Codes are never reused, not even a removed one's.
    assert client.post(f"{BASE}/", json={**BODY, "code": "old"}).status_code == 409


def test_create_field_validation(client, session):
    setup(session)
    mk_process(session, "GONE", active=False)
    mk_unit(session, "OLDU", active=False)
    cases = [
        {"name": " "}, {"name": "x" * 101}, {"description": "x" * 501},
        {"type": "NOPE"}, {"unit": "NOPE"}, {"unit": "OLDU"}, {"owner": 999},
        {"parent": "NOPE"}, {"parent": "GONE"}, {"tags": ["ok", " "]},
    ]
    for case in cases:
        r = client.post(f"{BASE}/", json={**BODY, **case})
        assert r.status_code == 400, (case, r.text)


# ── Update ──────────────────────────────────────────────────────────────────

def test_update_partial_ignores_code(client, session):
    setup(session)
    mk_process(session, "P1", name="Old", description="keep")
    r = client.put(f"{BASE}/P1", json={"name": "New", "code": "OTHER"})
    assert r.status_code == 200, r.text
    body = data(r)
    assert body["code"] == "P1" and body["name"] == "New" and body["description"] == "keep"
    assert body["updated_at"] is not None


def test_update_parent_cycle_refused(client, session):
    setup(session)
    mk_process(session, "A")
    mk_process(session, "B", parent="A")
    mk_process(session, "C", parent="B")
    assert client.put(f"{BASE}/A", json={"parent": "A"}).status_code == 400
    assert client.put(f"{BASE}/A", json={"parent": "C"}).status_code == 400
    assert client.put(f"{BASE}/C", json={"parent": "A"}).status_code == 200
    assert client.put(f"{BASE}/C", json={"parent": None}).status_code == 200
    assert session.get(Process, "C").parent is None


def test_update_unknown_is_404(client, session):
    setup(session)
    assert client.put(f"{BASE}/NOPE", json={"name": "x"}).status_code == 404


# ── Delete ──────────────────────────────────────────────────────────────────

def test_delete_logical_blocked_by_active_children(client, session):
    setup(session)
    mk_process(session, "PARENT")
    mk_process(session, "CHILD", parent="PARENT")
    assert client.delete(f"{BASE}/PARENT").status_code == 409
    assert client.delete(f"{BASE}/CHILD").status_code == 200
    assert client.delete(f"{BASE}/PARENT").status_code == 200
    row = session.get(Process, "PARENT")
    session.refresh(row)
    assert row is not None and row.is_active is False
    assert client.delete(f"{BASE}/PARENT").status_code == 404


# ── Create with links (US5) ─────────────────────────────────────────────────

def _links_count(session, code):
    rel = session.exec(select(RelatedProcess).where(RelatedProcess.source == code)).all()
    ast = session.exec(select(ProcessAsset).where(ProcessAsset.process == code)).all()
    ini = session.exec(select(ProcessInit).where(ProcessInit.process == code)).all()
    return len(rel), len(ast), len(ini)


def test_create_with_links_in_one_pass(client, session):
    setup(session)
    mk_process(session, "OPER-DEV")
    mk_asset(session, id=1)
    initiative(session, 3)
    body = {**BODY,
            "relations": [{"target": "OPER-DEV", "type": "PRECEDES", "rationale": "first"}],
            "assets": [{"asset": 1, "type": "RELATED_TO"}],
            "inits": [{"init": 3, "type": "RELATED_TO", "rationale": "why"}]}
    r = client.post(f"{BASE}/", json=body)
    assert r.status_code == 201, r.text
    assert _links_count(session, "OPER-QA") == (1, 1, 1)


def test_create_with_an_invalid_link_writes_nothing(client, session):
    setup(session)
    mk_process(session, "SUP", type="SUPPORT")
    mk_asset(session, id=1)
    mk_asset(session, id=2, active=False)
    bad_sets = [
        {"relations": [{"target": "SUP", "type": "SIMILAR_TO"}]},
        {"relations": [{"target": "SUP", "type": "SUPPORTS"}]},   # Primary → Support
        {"assets": [{"asset": 2, "type": "RELATED_TO"}]},
        {"inits": [{"init": 77, "type": "RELATED_TO"}]},
    ]
    for extra in bad_sets:
        r = client.post(f"{BASE}/", json={**BODY, **extra})
        assert r.status_code == 400, (extra, r.text)
        assert session.get(Process, "OPER-QA") is None
        assert _links_count(session, "OPER-QA") == (0, 0, 0)


def test_create_duplicate_code_with_links_writes_no_links(client, session):
    setup(session)
    mk_process(session, "OPER-QA")
    mk_asset(session, id=1)
    r = client.post(f"{BASE}/", json={**BODY, "assets": [{"asset": 1, "type": "RELATED_TO"}]})
    assert r.status_code == 409
    assert _links_count(session, "OPER-QA") == (0, 0, 0)
