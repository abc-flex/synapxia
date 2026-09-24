"""Initiative Management — listing scope and core-field edits (US1, US2).

`GET /api/initiatives/with-access` returns only initiatives the caller holds a
live grant on (superusers: all), filtered BEFORE pagination, with the caller's
effective level, favorite flag and the statuses the status control may offer.
`PUT`/`DELETE /api/initiatives/{id}` require the edit-level module privilege
AND per-initiative MANAGE.
"""
from sqlmodel import select

from app.inits.internal.models import Collaboration, Initiative
from tests.inits_helpers import (
    COLLAB, data, mk_fav, mk_init, mk_perm, override, seed_core_lists,
    seed_privileges, superuser, user,
)

URL = "/api/initiatives/with-access"


# --- US1: listing ----------------------------------------------------------

def test_lists_only_granted_initiatives(client, session):
    seed_privileges(session, can_edit=False)
    a = mk_init(session, name="A")
    b = mk_init(session, name="B")
    mk_init(session, name="C")
    mk_perm(session, a.id, "USER", "1", access_level="MANAGE")
    mk_perm(session, b.id, "USER", "1", access_level="VIEW")
    override(user(1))

    r = client.get(URL)
    assert r.status_code == 200
    rows = {row["name"]: row for row in data(r)}
    assert set(rows) == {"A", "B"}
    assert rows["A"]["my_access"] == "MANAGE"
    assert rows["B"]["my_access"] == "VIEW"


def test_no_grants_returns_empty(client, session):
    seed_privileges(session, can_edit=False)
    mk_init(session)
    override(user(1))
    assert data(client.get(URL)) == []


def test_superuser_sees_all_active_as_manage(client, session):
    mk_init(session, name="A")
    mk_init(session, name="Gone", is_active=False)
    override(superuser())
    rows = data(client.get(URL))
    assert [r["name"] for r in rows] == ["A"]
    assert rows[0]["my_access"] == "MANAGE"


def test_inactive_initiatives_excluded(client, session):
    seed_privileges(session, can_edit=False)
    gone = mk_init(session, name="Gone", is_active=False)
    mk_perm(session, gone.id, "USER", "1")
    override(user(1))
    assert data(client.get(URL)) == []


def test_filters_before_pagination(client, session):
    seed_privileges(session, can_edit=False)
    for n in range(5):
        i = mk_init(session, name=f"A{n}")
        mk_perm(session, i.id, "USER", "1")
    for n in range(5):
        mk_init(session, name=f"0-hidden{n}")  # sorts first by name
    override(user(1))
    rows = data(client.get(URL, params={"limit": 3}))
    assert [r["name"] for r in rows] == ["A0", "A1", "A2"]


def test_favorite_flag_is_the_callers_own(client, session):
    seed_privileges(session, can_edit=False)
    a = mk_init(session, name="A")
    b = mk_init(session, name="B")
    for i in (a, b):
        mk_perm(session, i.id, "PUBLIC", "ALL", access_level="VIEW")
    mk_fav(session, 1, a.id)
    mk_fav(session, 2, b.id)
    override(user(1))
    rows = {r["name"]: r["is_favorite"] for r in data(client.get(URL))}
    assert rows == {"A": True, "B": False}


def test_allowed_statuses_shape(client, session):
    seed_privileges(session, can_edit=False)
    act = mk_init(session, name="Act", status="ACTIVATED")
    acc = mk_init(session, name="Acc", status="ACCEPTED")
    for i in (act, acc):
        mk_perm(session, i.id, "USER", "1")
    override(user(1))
    rows = {r["name"]: r["allowed_statuses"] for r in data(client.get(URL))}
    assert rows["Act"] == ["ACTIVATED"]
    assert rows["Acc"] == ["ACCEPTED", "IN_PROGRESS", "DELIVERED", "ARCHIVED"]


def test_requires_module_privilege(client, session):
    mk_init(session)
    override(user(1, profile=COLLAB))
    assert client.get(URL).status_code == 403


def test_requires_authentication(client):
    assert client.get(URL).status_code == 401


# --- US2: core-field edits and logical delete ------------------------------

def _owner_setup(session, access="MANAGE", **init_kw):
    seed_privileges(session)
    seed_core_lists(session)
    i = mk_init(session, **init_kw)
    mk_perm(session, i.id, "USER", "1", access_level=access)
    return i


def _collabs(session, init_id):
    return session.exec(select(Collaboration).where(Collaboration.init == init_id)).all()


def test_put_updates_only_sent_fields(client, session):
    i = _owner_setup(session, name="Old", description="keep")
    override(user(1))
    r = client.put(f"/api/initiatives/{i.id}", json={"name": "New", "type": "PROTOTYPING"})
    assert r.status_code == 200
    body = data(r)
    assert body["name"] == "New" and body["type"] == "PROTOTYPING"
    assert body["description"] == "keep"
    assert body["my_access"] == "MANAGE"
    session.expire_all()
    assert session.get(Initiative, i.id).updated_at is not None
    assert _collabs(session, i.id) == []


def test_put_requires_manage(client, session):
    i = _owner_setup(session, access="VIEW")
    override(user(1))
    assert client.put(f"/api/initiatives/{i.id}", json={"name": "X"}).status_code == 403
    override(user(2))
    assert client.put(f"/api/initiatives/{i.id}", json={"name": "X"}).status_code == 403


def test_put_unknown_and_inactive(client, session):
    i = _owner_setup(session, is_active=False)
    override(user(1))
    assert client.put("/api/initiatives/999", json={"name": "X"}).status_code == 404
    assert client.put(f"/api/initiatives/{i.id}", json={"name": "X"}).status_code == 400


def test_put_rejects_blank_required_fields(client, session):
    i = _owner_setup(session)
    override(user(1))
    for field in ("name", "expected_impact", "priority_level"):
        r = client.put(f"/api/initiatives/{i.id}", json={field: "  "})
        assert r.status_code == 400, field


def test_put_rejects_unknown_list_values(client, session):
    i = _owner_setup(session)
    override(user(1))
    for field in ("type", "expected_impact", "priority_level"):
        r = client.put(f"/api/initiatives/{i.id}", json={field: "NOPE"})
        assert r.status_code == 400, field


def test_put_ignores_score(client, session):
    i = _owner_setup(session, score=7)
    override(user(1))
    r = client.put(f"/api/initiatives/{i.id}", json={"score": 99, "name": "N"})
    assert r.status_code == 200
    assert data(r)["score"] == 7


def test_put_same_status_is_not_a_transition(client, session):
    i = _owner_setup(session, status="ACCEPTED")
    override(user(1))
    r = client.put(f"/api/initiatives/{i.id}", json={"status": "ACCEPTED", "name": "N"})
    assert r.status_code == 200
    assert _collabs(session, i.id) == []


def test_delete_is_logical_and_manage_only(client, session):
    i = _owner_setup(session)
    override(user(2))
    assert client.delete(f"/api/initiatives/{i.id}").status_code == 403
    override(user(1))
    r = client.delete(f"/api/initiatives/{i.id}")
    assert r.status_code == 200
    session.expire_all()
    assert session.get(Initiative, i.id).is_active is False
    assert client.delete(f"/api/initiatives/{i.id}").status_code == 400
    assert _collabs(session, i.id) == []


def test_delete_view_holder_forbidden(client, session):
    i = _owner_setup(session, access="VIEW")
    override(user(1))
    assert client.delete(f"/api/initiatives/{i.id}").status_code == 403
