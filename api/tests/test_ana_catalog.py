"""Dashboard Catalog list — `GET /api/dashboards/catalog` (specs/007-dashboard-catalog US1)."""
from tests.catalog_helpers import (
    data, mk_dashboard, mk_grant, mk_param, override, seed_ana_lists, seed_privileges,
    setup_catalog, superuser, user, viewer,
)

URL = "/api/dashboards/catalog"


def names(r):
    return [d["name"] for d in data(r)]


def test_requires_catalog_privilege(client, session):
    seed_ana_lists(session)
    d = mk_dashboard(session, status="PUBLISHED")
    mk_grant(session, d.id, "PUBLIC", "ALL", access_level="VIEW")
    override(viewer())
    assert client.get(URL).status_code == 403  # no ANA/CATALOG row at all
    seed_privileges(session, profile="COLLABORATOR", options=("CATALOG",), can_edit=False)
    assert client.get(URL).status_code == 200  # read-only CATALOG suffices


def test_only_published_active_and_granted(client, session):
    setup_catalog(session, name="Pub", grant=("PUBLIC", "ALL"))
    for status in ("DRAFT", "ARCHIVED", "RETIRED"):
        d = mk_dashboard(session, name=status.title(), status=status)
        mk_grant(session, d.id, "PUBLIC", "ALL", access_level="VIEW")
    gone = mk_dashboard(session, name="Gone", status="PUBLISHED", is_active=False)
    mk_grant(session, gone.id, "PUBLIC", "ALL", access_level="VIEW")
    mk_dashboard(session, name="Ungranted", status="PUBLISHED")
    legacy = mk_dashboard(session, name="Legacy", status="2-PUBLISHED")
    mk_grant(session, legacy.id, "USER", "1", access_level="VIEW")

    override(viewer())
    assert names(client.get(URL)) == ["Legacy", "Pub"]
    override(superuser())
    assert names(client.get(URL)) == ["Legacy", "Pub", "Ungranted"]


def test_visibility_filtered_before_pagination(client, session):
    setup_catalog(session, name="Z visible", grant=("USER", "1"))
    for i in range(3):
        mk_dashboard(session, name=f"A hidden {i}", status="PUBLISHED")
    v2 = mk_dashboard(session, name="Y visible", status="PUBLISHED")
    mk_grant(session, v2.id, "USER", "1", access_level="VIEW")
    override(viewer())
    assert names(client.get(URL + "?skip=0&limit=1")) == ["Y visible"]
    assert names(client.get(URL + "?skip=1&limit=1")) == ["Z visible"]


def test_row_projection(client, session):
    d = setup_catalog(session, name="Dash", grant=("PUBLIC", "ALL"), tags=["a"])
    mk_grant(session, d.id, "UNIT", "ENG", access_level="VIEW")
    mk_param(session, d.id, "p1")
    mk_param(session, d.id, "p2")
    mk_param(session, d.id, "old", is_active=False)
    override(viewer())
    assert client.put(f"/api/dashboards/{d.id}/favorite").status_code == 200
    row = data(client.get(URL))[0]
    assert row["permission_scopes"] == ["PUBLIC", "UNIT"]
    assert row["parameter_count"] == 2
    assert row["is_favorite"] is True
    assert row["tags"] == ["a"]
    assert "source_url" not in row and "status" not in row


def test_management_reads_stay_closed_to_catalog_only_profiles(client, session):
    setup_catalog(session)
    override(viewer())
    assert client.get("/api/dashboards/with-access").status_code == 403
    override(user(1))  # ADMINISTRATIVE without any ANA privilege row
    assert client.get(URL).status_code == 403
