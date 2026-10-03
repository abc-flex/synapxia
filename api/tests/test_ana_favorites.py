"""Dashboard Management — favorites (`PUT`/`DELETE /api/dashboards/{id}/favorite`
and `is_favorite` on the list; specs/006-dashboard-management, amended FR-004a)."""
from app.insights.internal.models import FavoriteDashboard
from tests.ana_helpers import (
    data, mk_dashboard, mk_grant, override, seed_ana_lists, seed_privileges, setup_owner, user,
)


def fav_url(d):
    return f"/api/dashboards/{d.id}/favorite"


def test_mark_and_clear_favorite(client, session):
    d = setup_owner(session, access="VIEW")  # VIEW suffices: favoriting is not an edit
    override(user(1))
    r = client.put(fav_url(d))
    assert r.status_code == 200 and data(r) == {"dashboard": d.id, "is_favorite": True}
    assert data(client.get("/api/dashboards/with-access"))[0]["is_favorite"] is True
    assert data(client.get(f"/api/dashboards/{d.id}"))["is_favorite"] is True

    r = client.delete(fav_url(d))
    assert r.status_code == 200 and data(r)["is_favorite"] is False
    assert data(client.get("/api/dashboards/with-access"))[0]["is_favorite"] is False
    session.expire_all()
    row = session.get(FavoriteDashboard, (1, d.id))
    assert row is not None and row.is_active is False  # logical removal

    # Marking again restores the same row.
    assert client.put(fav_url(d)).status_code == 200
    session.expire_all()
    assert session.get(FavoriteDashboard, (1, d.id)).is_active is True


def test_favorite_is_idempotent(client, session):
    d = setup_owner(session)
    override(user(1))
    assert client.put(fav_url(d)).status_code == 200
    assert client.put(fav_url(d)).status_code == 200
    assert client.delete(fav_url(d)).status_code == 200
    assert client.delete(fav_url(d)).status_code == 200


def test_favorites_are_personal(client, session):
    d = setup_owner(session)
    mk_grant(session, d.id, "USER", "2", access_level="VIEW")
    override(user(1))
    client.put(fav_url(d))
    override(user(2))
    assert data(client.get("/api/dashboards/with-access"))[0]["is_favorite"] is False


def test_favorite_requires_view_and_an_active_dashboard(client, session):
    seed_privileges(session)
    seed_ana_lists(session)
    hidden = mk_dashboard(session, name="Hidden")
    gone = mk_dashboard(session, name="Gone", is_active=False)
    mk_grant(session, gone.id, "USER", "1")
    override(user(1))
    assert client.put(fav_url(hidden)).status_code == 403
    assert client.put(fav_url(gone)).status_code == 404
    assert client.put("/api/dashboards/999/favorite").status_code == 404


def test_favorite_requires_rbac(client, session):
    d = mk_dashboard(session)
    mk_grant(session, d.id, "USER", "1")
    override(user(1))
    assert client.put(fav_url(d)).status_code == 403
