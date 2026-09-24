"""Several links per pair — `related_assets` (source, target, type) and
`asset_inits` (asset, init, type) are keyed by the full triple, as in the DDL.

* The same pair may be linked once per relation type.
* Typed routes (`…/{a}/{b}/{type}`) address one link exactly.
* Legacy pair routes (`…/{a}/{b}`) keep working for single-link pairs and
  answer 409 when a pair holds several links.
* POST: an active identical triple → 409; an inactive one is reactivated.
* `/related/{id}` keeps "outgoing wins" per other asset but lists every type.
"""
from types import SimpleNamespace

from app.auth.routes import current_active_user
from app.inits.internal.models import Initiative
from app.lib.internal.models import Asset, AssetInit, AssetRelation
from app.main import app


def _superuser():
    return SimpleNamespace(id=1, username="root", profile="ADMINISTRATOR",
                           is_superuser=True, is_active=True, unit=None)


def _asset(session, name):
    a = Asset(name=name, status="PUBLISHED", category="PROMPTS")
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _init(session):
    i = Initiative(name="I", expected_impact="OTHER", priority_level="LOW", status="ACCEPTED")
    session.add(i)
    session.commit()
    session.refresh(i)
    return i


def _data(r):
    return r.json()["data"]


# --- related_assets ----------------------------------------------------------

def test_relation_pair_once_per_type(session, client):
    a, b = _asset(session, "A"), _asset(session, "B")
    app.dependency_overrides[current_active_user] = _superuser
    post = lambda t: client.post("/api/asset_relations/", json={"source": a.id, "target": b.id, "type": t})

    assert post("DEPENDS_ON").status_code == 201
    assert post("EXTENDS").status_code == 201
    assert post("DEPENDS_ON").status_code == 409
    types = sorted(r["type"] for r in _data(client.get(f"/api/asset_relations/source/{a.id}")))
    assert types == ["DEPENDS_ON", "EXTENDS"]


def test_relation_typed_routes(session, client):
    a, b = _asset(session, "A"), _asset(session, "B")
    app.dependency_overrides[current_active_user] = _superuser
    for t in ("DEPENDS_ON", "EXTENDS"):
        client.post("/api/asset_relations/", json={"source": a.id, "target": b.id, "type": t})

    base = f"/api/asset_relations/{a.id}/{b.id}"
    assert _data(client.get(f"{base}/EXTENDS"))["type"] == "EXTENDS"
    r = client.put(f"{base}/EXTENDS", json={"rationale": "why"})
    assert r.status_code == 200 and _data(r)["rationale"] == "why"
    assert client.put(f"{base}/EXTENDS", json={"type": "SIMILAR_TO"}).status_code == 400

    assert client.delete(f"{base}/EXTENDS").status_code == 200
    assert client.delete(f"{base}/EXTENDS").status_code == 400
    assert client.get(f"{base}/MISSING").status_code == 404
    remaining = [r["type"] for r in _data(client.get(f"/api/asset_relations/source/{a.id}"))]
    assert remaining == ["DEPENDS_ON"]


def test_relation_pair_routes_ambiguous_then_single(session, client):
    a, b = _asset(session, "A"), _asset(session, "B")
    app.dependency_overrides[current_active_user] = _superuser
    for t in ("DEPENDS_ON", "EXTENDS"):
        client.post("/api/asset_relations/", json={"source": a.id, "target": b.id, "type": t})

    pair = f"/api/asset_relations/{a.id}/{b.id}"
    assert client.get(pair).status_code == 409
    assert client.put(pair, json={"rationale": "x"}).status_code == 409
    assert client.delete(pair).status_code == 409

    client.delete(f"{pair}/EXTENDS")  # back to a single active link
    assert _data(client.get(pair))["type"] == "DEPENDS_ON"
    # Legacy PUT may still change the type while the pair has one link...
    assert _data(client.put(pair, json={"type": "SIMILAR_TO"}))["type"] == "SIMILAR_TO"
    # ...but not onto a triple that already exists (the inactive EXTENDS row).
    assert client.put(pair, json={"type": "EXTENDS"}).status_code == 409


def test_relation_post_reactivates_inactive_triple(session, client):
    a, b = _asset(session, "A"), _asset(session, "B")
    session.add(AssetRelation(source=a.id, target=b.id, type="EXTENDS",
                              rationale="old", is_active=False))
    session.commit()
    app.dependency_overrides[current_active_user] = _superuser
    r = client.post("/api/asset_relations/",
                    json={"source": a.id, "target": b.id, "type": "EXTENDS", "rationale": "new"})
    assert r.status_code == 201
    assert _data(r)["is_active"] is True and _data(r)["rationale"] == "new"
    assert len(session.exec(AssetRelation.__table__.select()).all()) == 1


def test_related_lists_every_outgoing_type(session, client):
    a, b, c = _asset(session, "A"), _asset(session, "B"), _asset(session, "C")
    for src, tgt, t in [(a.id, b.id, "DEPENDS_ON"), (a.id, b.id, "EXTENDS"),
                        (b.id, a.id, "USED_BY"),     # incoming from b — outgoing wins
                        (c.id, a.id, "USED_BY"), (c.id, a.id, "CONTAINS")]:
        session.add(AssetRelation(source=src, target=tgt, type=t))
    session.commit()
    app.dependency_overrides[current_active_user] = _superuser

    rows = _data(client.get(f"/api/asset_relations/related/{a.id}"))
    got = sorted((r["id"], r["relation_type"], r["direction"]) for r in rows)
    assert got == sorted([
        (b.id, "DEPENDS_ON", "outgoing"), (b.id, "EXTENDS", "outgoing"),
        (c.id, "CONTAINS", "incoming"), (c.id, "USED_BY", "incoming"),
    ])


# --- asset_inits (asset side) -----------------------------------------------

def test_asset_init_pair_once_per_type(session, client):
    a, i = _asset(session, "A"), _init(session)
    app.dependency_overrides[current_active_user] = _superuser
    post = lambda t: client.post("/api/asset_inits/", json={"asset": a.id, "init": i.id, "type": t})

    assert post("USED_BY").status_code == 201
    assert post("CONTAINS").status_code == 201
    assert post("USED_BY").status_code == 409

    pair = f"/api/asset_inits/{a.id}/{i.id}"
    assert client.get(pair).status_code == 409
    assert client.delete(f"{pair}/USED_BY").status_code == 200
    assert _data(client.get(pair))["type"] == "CONTAINS"
    assert client.put(f"{pair}/CONTAINS", json={"type": "USED_BY"}).status_code == 400

    r = client.post("/api/asset_inits/", json={"asset": a.id, "init": i.id, "type": "USED_BY",
                                              "rationale": "back"})
    assert r.status_code == 201 and _data(r)["rationale"] == "back"
    assert len(session.exec(AssetInit.__table__.select()).all()) == 2
