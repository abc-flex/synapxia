"""Related-assets tests (HU-LI07) — Constitution Principle II/III.

Phase 3 of the lib roadmap surfaces the existing ``related_assets`` table on the
galleries. The only new backend surface is additive:

* ``GET /api/asset_relations/target/{asset_id}`` — reverse lookup (counterpart
  to the existing ``/source/{asset_id}``).
* ``GET /api/asset_relations/related/{asset_id}`` — resolved related **assets**
  in both directions, de-duplicated by the other asset id (outgoing wins),
  excluding inactive/missing assets, via one batched ``IN`` query (no N+1).

Tests run through the routes against the in-memory SQLite ``session``/``client``
fixtures, overriding ``current_active_user`` with a superuser to clear the
``require_privilege("LIB","ASSETS")`` gate (superusers bypass the table).
"""

from types import SimpleNamespace

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal.models import Asset, AssetRelation


def _mk_asset(session, name="Asset", status="PUBLISHED", is_active=True):
    asset = Asset(name=name, status=status, is_active=is_active)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _mk_rel(session, source, target, type="RELATED_TO", is_active=True):
    rel = AssetRelation(source=source, target=target, type=type, is_active=is_active)
    session.add(rel)
    session.commit()
    return rel


def _superuser():
    return SimpleNamespace(
        id=1, username="tester", profile="ADMINISTRATOR",
        is_superuser=True, is_active=True,
    )


# --- Auth gating + OpenAPI --------------------------------------------------

def test_related_routes_require_auth(client):
    assert client.get("/api/asset_relations/related/1").status_code in (401, 403)
    assert client.get("/api/asset_relations/target/1").status_code in (401, 403)


def test_relation_routes_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/asset_relations/target/{asset_id}" in paths
    assert "/api/asset_relations/related/{asset_id}" in paths


# --- Reverse lookup ---------------------------------------------------------

def test_get_by_target_returns_incoming_relations(session, client):
    a = _mk_asset(session, "A")
    b = _mk_asset(session, "B")
    _mk_rel(session, b.id, a.id, "USED_BY")  # b -> a, so a is the target
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get(f"/api/asset_relations/target/{a.id}")
    assert r.status_code == 200
    body = r.json()["data"]
    assert len(body) == 1
    assert body[0]["source"] == b.id and body[0]["target"] == a.id


def test_get_by_target_excludes_inactive_relation(session, client):
    a = _mk_asset(session, "A")
    b = _mk_asset(session, "B")
    _mk_rel(session, b.id, a.id, "USED_BY", is_active=False)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get(f"/api/asset_relations/target/{a.id}")
    assert r.status_code == 200
    assert r.json()["data"] == []


# --- Resolved related assets (both directions) ------------------------------

def test_get_related_resolves_both_directions(session, client):
    a = _mk_asset(session, "A")
    b = _mk_asset(session, "B")
    c = _mk_asset(session, "C")
    _mk_rel(session, a.id, b.id, "DEPENDS_ON")  # a -> b  → outgoing for a
    _mk_rel(session, c.id, a.id, "USED_BY")     # c -> a  → incoming for a
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get(f"/api/asset_relations/related/{a.id}")
    assert r.status_code == 200
    by_id = {item["id"]: item for item in r.json()["data"]}

    assert by_id[b.id]["direction"] == "outgoing"
    assert by_id[b.id]["relation_type"] == "DEPENDS_ON"
    assert by_id[b.id]["name"] == "B"
    assert by_id[c.id]["direction"] == "incoming"
    assert by_id[c.id]["relation_type"] == "USED_BY"


def test_get_related_dedupes_bidirectional_outgoing_wins(session, client):
    a = _mk_asset(session, "A")
    b = _mk_asset(session, "B")
    _mk_rel(session, a.id, b.id, "DEPENDS_ON")  # outgoing
    _mk_rel(session, b.id, a.id, "USED_BY")     # incoming — same other asset (b)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get(f"/api/asset_relations/related/{a.id}")
    matches = [i for i in r.json()["data"] if i["id"] == b.id]
    assert len(matches) == 1  # de-duplicated by other-asset id
    assert matches[0]["direction"] == "outgoing"  # outgoing wins the tie
    assert matches[0]["relation_type"] == "DEPENDS_ON"


def test_get_related_excludes_inactive_target_asset(session, client):
    a = _mk_asset(session, "A")
    b = _mk_asset(session, "B", is_active=False)
    _mk_rel(session, a.id, b.id, "RELATED_TO")
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get(f"/api/asset_relations/related/{a.id}")
    assert r.status_code == 200
    assert all(i["id"] != b.id for i in r.json()["data"])


def test_get_related_excludes_inactive_relation(session, client):
    a = _mk_asset(session, "A")
    b = _mk_asset(session, "B")
    _mk_rel(session, a.id, b.id, "RELATED_TO", is_active=False)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get(f"/api/asset_relations/related/{a.id}")
    assert r.status_code == 200
    assert r.json()["data"] == []


def test_get_related_empty_when_no_relations(session, client):
    a = _mk_asset(session, "A")
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get(f"/api/asset_relations/related/{a.id}")
    assert r.status_code == 200
    assert r.json()["data"] == []


# --- Self-relation guard (existing create contract) -------------------------

def test_self_relation_rejected(session, client):
    a = _mk_asset(session, "A")
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post(
        "/api/asset_relations/",
        json={"source": a.id, "target": a.id, "type": "RELATED_TO"},
    )
    assert r.status_code == 400
