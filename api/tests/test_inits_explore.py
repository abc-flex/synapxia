"""Explore Initiatives listing (HU-IN04) — specs/005-explore-initiatives US3."""
from datetime import timedelta

from app.lib.internal.models import AssetInit
from tests.inits_helpers import (
    COLLAB, NOW, data, mk_asset, mk_collab, mk_fav, mk_init, mk_perm, override,
    seed_privileges, superuser, user,
)


def _explore(client, **params):
    resp = client.get("/api/initiatives/explore", params=params)
    assert resp.status_code == 200, resp.text
    return data(resp)


def test_only_living_portfolio_statuses(session, client):
    seed_privileges(session, profile=COLLAB, options=("EXPLORE",), can_edit=False)
    for i, status in enumerate(["ACCEPTED", "IN_PROGRESS", "DELIVERED",
                                "ACTIVATED", "FEEDBACK", "REJECTED", "ARCHIVED"]):
        init = mk_init(session, name=status, status=status)
        mk_perm(session, init.id, "PUBLIC", "ALL", access_level="VIEW")
    inactive = mk_init(session, name="GONE", status="ACCEPTED", is_active=False)
    mk_perm(session, inactive.id, "PUBLIC", "ALL", access_level="VIEW")
    override(user(1, profile=COLLAB))
    assert {i["name"] for i in _explore(client)} == {"ACCEPTED", "IN_PROGRESS", "DELIVERED"}


def test_scoped_to_grants_and_superuser_sees_all(session, client):
    seed_privileges(session, profile=COLLAB, options=("EXPLORE",))
    mine = mk_init(session, name="Mine")
    mk_perm(session, mine.id, "USER", "1", access_level="VIEW")
    mk_init(session, name="Hidden")
    override(user(1, profile=COLLAB))
    rows = _explore(client)
    assert [r["name"] for r in rows] == ["Mine"]
    assert rows[0]["my_access"] == "VIEW" and rows[0]["permission_scopes"] == ["USER"]
    override(superuser())
    assert {r["name"] for r in _explore(client)} == {"Mine", "Hidden"}


def test_filter_applies_before_pagination(session, client):
    seed_privileges(session, profile=COLLAB, options=("EXPLORE",))
    for i in range(3):
        mk_init(session, name=f"hidden{i}", created_at=NOW + timedelta(minutes=10 + i))
    for i in range(3):
        init = mk_init(session, name=f"mine{i}", created_at=NOW + timedelta(minutes=i))
        mk_perm(session, init.id, "USER", "1", access_level="VIEW")
    override(user(1, profile=COLLAB))
    assert [r["name"] for r in _explore(client, skip=0, limit=2)] == ["mine2", "mine1"]
    assert [r["name"] for r in _explore(client, skip=2, limit=2)] == ["mine0"]


def test_counters_and_favorite(session, client):
    seed_privileges(session, profile=COLLAB, options=("EXPLORE",))
    init = mk_init(session, name="Counted")
    mk_perm(session, init.id, "PUBLIC", "ALL", access_level="VIEW")
    mk_fav(session, 1, init.id)
    mk_collab(session, init.id, 1, "VOTE", content="POSITIVE")
    mk_collab(session, init.id, 2, "VOTE", content="NEGATIVE")
    mk_collab(session, init.id, 3, "VOTE", content="POSITIVE", active=False)
    q = mk_collab(session, init.id, 2, "QUESTION", content="?")
    mk_collab(session, init.id, 1, "ANSWER", content="!", parent=q.id)
    mk_collab(session, init.id, 3, "COMMENT", content="old", active=False)
    mk_collab(session, init.id, 1, "ACTIVATION", "HANDLED")  # not discussion
    mk_asset(session, 5)
    mk_asset(session, 6)
    session.add(AssetInit(asset=5, init=init.id, type="USED_BY"))
    session.add(AssetInit(asset=6, init=init.id, type="USED_BY", is_active=False))
    session.commit()

    override(user(1, profile=COLLAB))
    row = _explore(client)[0]
    assert row["is_favorite"] is True
    assert (row["votes"]["positive"], row["votes"]["negative"], row["votes"]["my_vote"]) == (1, 1, "POSITIVE")
    assert row["discussion_count"] == 2
    assert row["related_assets_count"] == 1


def test_newest_first(session, client):
    seed_privileges(session, profile=COLLAB, options=("EXPLORE",))
    for i, name in enumerate(["old", "new"]):
        init = mk_init(session, name=name, created_at=NOW + timedelta(minutes=i))
        mk_perm(session, init.id, "PUBLIC", "ALL", access_level="VIEW")
    override(user(1, profile=COLLAB))
    assert [r["name"] for r in _explore(client)] == ["new", "old"]


def test_needs_an_inits_privilege(session, client):
    override(user(1, profile=COLLAB))
    assert client.get("/api/initiatives/explore").status_code == 403
