"""Process Management — Related assets / Related inits
(specs/009-process-management, US3 / US4). Typed links over the shared
RELATION_TYPE list, replaced atomically per tab."""
import pytest
from sqlmodel import select

from app.workflows.internal.models import ProcessAsset, ProcessInit
from tests.proc_helpers import (
    BASE, data, initiative, mk_asset, mk_asset_link, mk_init_link, mk_process, setup,
)

KINDS = {
    "assets": {"model": ProcessAsset, "id": "asset", "name": "asset_name", "active": "asset_active"},
    "inits": {"model": ProcessInit, "id": "init", "name": "init_name", "active": "init_active"},
}


def _seed(session):
    setup(session)
    mk_process(session, "P1")
    mk_asset(session, id=1, name="Prompt A", category="PROMPTS")
    mk_asset(session, id=2, name="Agent B", category="AGENTS")
    mk_asset(session, id=9, name="Gone", active=False)
    initiative(session, 1, name="Init A")
    initiative(session, 2, name="Init B")
    initiative(session, 9, name="Gone", active=False)


def _put(client, kind, *items):
    return client.put(f"{BASE}/P1/{kind}", json={kind: list(items)})


def _item(kind, id_, type_="RELATED_TO", rationale=None):
    return {KINDS[kind]["id"]: id_, "type": type_, "rationale": rationale}


def _link(kind, session, id_, type_="RELATED_TO", active=True):
    fn = mk_asset_link if kind == "assets" else mk_init_link
    return fn(session, "P1", id_, type_, active=active)


def _rows(kind, session):
    session.expire_all()
    model = KINDS[kind]["model"]
    return session.exec(select(model).where(model.process == "P1")).all()


@pytest.mark.parametrize("kind", list(KINDS))
def test_get_shape(client, session, kind):
    _seed(session)
    _link(kind, session, 1)
    _link(kind, session, 2, active=False)
    rows = data(client.get(f"{BASE}/P1/{kind}"))
    assert len(rows) == 1
    row = rows[0]
    assert row[KINDS[kind]["id"]] == 1 and row[KINDS[kind]["active"]] is True
    assert row[KINDS[kind]["name"]] in ("Prompt A", "Init A")
    if kind == "assets":
        assert row["category"] == "PROMPTS"


@pytest.mark.parametrize("kind", list(KINDS))
def test_replace_semantics(client, session, kind):
    _seed(session)
    _link(kind, session, 1, "RELATED_TO")
    _link(kind, session, 2, "USED_BY", active=False)
    created = {getattr(r, KINDS[kind]["id"]): r.created_at for r in _rows(kind, session)}
    r = _put(client, kind,
             _item(kind, 2, "USED_BY", "back"),
             _item(kind, 2, "DEPENDS_ON"))
    assert r.status_code == 200, r.text
    by = {(getattr(x, KINDS[kind]["id"]), x.type): x for x in _rows(kind, session)}
    assert by[(1, "RELATED_TO")].is_active is False
    assert by[(2, "USED_BY")].is_active is True and by[(2, "USED_BY")].rationale == "back"
    assert by[(2, "USED_BY")].created_at == created[2]
    assert by[(2, "DEPENDS_ON")].is_active is True
    assert len(data(r)) == 2


@pytest.mark.parametrize("kind", list(KINDS))
@pytest.mark.parametrize("bad", ["inactive", "unknown", "wrong_list", "duplicate", "no_type"])
def test_invalid_refused_atomically(client, session, kind, bad):
    _seed(session)
    _link(kind, session, 1)
    items = {
        "inactive": [_item(kind, 9)],
        "unknown": [_item(kind, 404)],
        "wrong_list": [_item(kind, 2, "PRECEDES")],
        "duplicate": [_item(kind, 2), _item(kind, 2)],
        "no_type": [_item(kind, 2, "")],
    }[bad]
    r = _put(client, kind, _item(kind, 1), *items)
    assert r.status_code == 400, r.text
    rows = _rows(kind, session)
    assert [(getattr(x, KINDS[kind]["id"]), x.type, x.is_active) for x in rows] == [
        (1, "RELATED_TO", True)]


@pytest.mark.parametrize("kind", list(KINDS))
def test_unknown_process_404(client, session, kind):
    _seed(session)
    assert client.get(f"{BASE}/NOPE/{kind}").status_code == 404
    assert client.put(f"{BASE}/NOPE/{kind}", json={kind: []}).status_code == 404
