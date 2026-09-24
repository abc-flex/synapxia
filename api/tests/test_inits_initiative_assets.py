"""Related Assets from the initiative side — `/api/initiatives/{id}/assets`."""
from app.lib.internal.models import Asset, AssetInit, AssetPermission
from app.admin.internal.models import Privilege
from tests.inits_helpers import (
    NOW, data, mk_init, mk_perm, override, seed_core_lists, seed_privileges,
    superuser, user,
)


def _asset(session, name="Asset", visible_to=1, active=True):
    a = Asset(name=name, status="PUBLISHED", category="PROMPTS", is_active=active)
    session.add(a)
    session.commit()
    session.refresh(a)
    if visible_to is not None:
        session.add(AssetPermission(asset=a.id, target_type="USER",
                                    target_code=str(visible_to),
                                    access_level="VIEW", valid_from=NOW))
        session.commit()
    return a


def _setup(session, access="MANAGE"):
    seed_privileges(session)
    seed_core_lists(session)
    init = mk_init(session)
    mk_perm(session, init.id, "USER", "1", access_level=access)
    return init


def _url(init_id, asset_id=None, type_=None):
    base = f"/api/initiatives/{init_id}/assets"
    return f"{base}/{asset_id}/{type_}" if asset_id is not None else base


def test_add_list_remove(client, session):
    init = _setup(session)
    a = _asset(session, "Filesystem MCP")
    override(user(1))

    r = client.post(_url(init.id), json={"asset": a.id, "type": "USED_BY", "rationale": "files"})
    assert r.status_code == 201
    assert data(r)["asset_name"] == "Filesystem MCP"

    rows = data(client.get(_url(init.id)))
    assert [(x["asset"], x["type"], x["category"], x["asset_status"]) for x in rows] == [
        (a.id, "USED_BY", "PROMPTS", "PUBLISHED")]

    assert client.delete(_url(init.id, a.id, "USED_BY")).status_code == 200
    assert data(client.get(_url(init.id))) == []
    assert client.delete(_url(init.id, a.id, "USED_BY")).status_code == 400
    assert client.delete(_url(init.id, 999, "USED_BY")).status_code == 404
    assert client.delete(_url(init.id, a.id, "CONTAINS")).status_code == 404


def test_same_asset_once_per_relation_type(client, session):
    init = _setup(session)
    a = _asset(session)
    override(user(1))
    assert client.post(_url(init.id), json={"asset": a.id, "type": "USED_BY"}).status_code == 201
    assert client.post(_url(init.id), json={"asset": a.id, "type": "CONTAINS"}).status_code == 201
    assert client.post(_url(init.id), json={"asset": a.id, "type": "USED_BY"}).status_code == 409
    assert sorted(x["type"] for x in data(client.get(_url(init.id)))) == ["CONTAINS", "USED_BY"]

    # Removing one type leaves the other link untouched.
    assert client.delete(_url(init.id, a.id, "USED_BY")).status_code == 200
    assert [x["type"] for x in data(client.get(_url(init.id)))] == ["CONTAINS"]


def test_readding_removed_link_restores_it(client, session):
    init = _setup(session)
    a = _asset(session)
    override(user(1))
    client.post(_url(init.id), json={"asset": a.id, "type": "USED_BY", "rationale": "first"})
    client.delete(_url(init.id, a.id, "USED_BY"))
    r = client.post(_url(init.id), json={"asset": a.id, "type": "USED_BY", "rationale": "again"})
    assert r.status_code == 201
    rows = data(client.get(_url(init.id)))
    assert len(rows) == 1 and rows[0]["type"] == "USED_BY" and rows[0]["rationale"] == "again"
    assert len(session.exec(AssetInit.__table__.select()).all()) == 1  # restored, not duplicated


def test_validation(client, session):
    init = _setup(session)
    a = _asset(session)
    gone = _asset(session, "Gone", active=False)
    override(user(1))
    assert client.post(_url(init.id), json={"asset": 999, "type": "USED_BY"}).status_code == 400
    assert client.post(_url(init.id), json={"asset": gone.id, "type": "USED_BY"}).status_code == 400
    assert client.post(_url(init.id), json={"asset": a.id, "type": "NOPE"}).status_code == 400


def test_view_holder_cannot_write(client, session):
    init = _setup(session, access="VIEW")
    a = _asset(session)
    override(user(1))
    assert client.get(_url(init.id)).status_code == 200
    assert client.post(_url(init.id), json={"asset": a.id, "type": "USED_BY"}).status_code == 403


def test_cannot_link_an_invisible_asset(client, session):
    init = _setup(session)
    hidden = _asset(session, visible_to=None)
    override(user(1))
    assert client.post(_url(init.id), json={"asset": hidden.id, "type": "USED_BY"}).status_code == 403
    override(superuser())
    assert client.post(_url(init.id), json={"asset": hidden.id, "type": "USED_BY"}).status_code == 201


def test_link_is_the_shared_asset_inits_record(client, session):
    init = _setup(session)
    a = _asset(session)
    session.add(Privilege(profile="ADMINISTRATIVE", module="LIB", option="ASSETS",
                          can_edit=False, is_active=True))
    session.commit()
    override(user(1))
    client.post(_url(init.id), json={"asset": a.id, "type": "USED_BY"})
    r = client.get(f"/api/asset_inits/asset/{a.id}")
    assert r.status_code == 200
    assert [x["init"] for x in data(r)] == [init.id]
