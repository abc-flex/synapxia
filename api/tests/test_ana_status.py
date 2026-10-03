"""Dashboard Management — status lifecycle through `PUT /api/dashboards/{id}`
(specs/006-dashboard-management, US2 / FR-012)."""
import pytest

from app.insights.internal.models import Dashboard
from tests.ana_helpers import data, override, setup_owner, user

STATUSES = ["DRAFT", "PUBLISHED", "ARCHIVED", "RETIRED"]
ALLOWED = {
    ("DRAFT", "PUBLISHED"),
    ("PUBLISHED", "ARCHIVED"), ("PUBLISHED", "RETIRED"),
    ("ARCHIVED", "PUBLISHED"), ("ARCHIVED", "RETIRED"),
}
EXPECTED_ALLOWED = {
    "DRAFT": ["DRAFT", "PUBLISHED"],
    "PUBLISHED": ["PUBLISHED", "ARCHIVED", "RETIRED"],
    "ARCHIVED": ["ARCHIVED", "PUBLISHED", "RETIRED"],
    "RETIRED": ["RETIRED"],
}


def _put(client, d, **body):
    return client.put(f"/api/dashboards/{d.id}", json=body)


@pytest.mark.parametrize("current", STATUSES)
@pytest.mark.parametrize("new", STATUSES)
def test_transition_matrix_over_http(client, session, current, new):
    if current == new:
        return
    d = setup_owner(session, status=current, name="Before")
    override(user(1))
    r = _put(client, d, status=new, name="After")
    session.expire_all()
    row = session.get(Dashboard, d.id)
    if (current, new) in ALLOWED:
        assert r.status_code == 200
        assert data(r)["status"] == new
        assert data(r)["allowed_statuses"] == EXPECTED_ALLOWED[new]
        assert row.status == new and row.name == "After"
    else:
        assert r.status_code == 400
        # Nothing applied — not even the other field sent alongside.
        assert row.status == current and row.name == "Before"


def test_unchanged_status_is_a_noop(client, session):
    d = setup_owner(session, status="PUBLISHED")
    override(user(1))
    r = _put(client, d, status="PUBLISHED", name="Renamed")
    assert r.status_code == 200
    assert data(r)["status"] == "PUBLISHED" and data(r)["name"] == "Renamed"


def test_legacy_status_is_locked(client, session):
    d = setup_owner(session, status="LEGACY")
    override(user(1))
    r = client.get(f"/api/dashboards/{d.id}")
    assert data(r)["allowed_statuses"] == ["LEGACY"]
    assert _put(client, d, status="PUBLISHED").status_code == 400


def test_prefixed_status_is_normalised(client, session):
    d = setup_owner(session, status="2-PUBLISHED")
    override(user(1))
    r = _put(client, d, status="ARCHIVED")
    assert r.status_code == 200 and data(r)["status"] == "ARCHIVED"


def test_second_request_is_evaluated_against_the_new_status(client, session):
    d = setup_owner(session, status="PUBLISHED")
    override(user(1))
    assert _put(client, d, status="RETIRED").status_code == 200
    assert _put(client, d, status="ARCHIVED").status_code == 400
    assert _put(client, d, status="PUBLISHED").status_code == 400


def test_view_holder_cannot_change_status(client, session):
    d = setup_owner(session, access="VIEW", status="DRAFT")
    override(user(1))
    assert _put(client, d, status="PUBLISHED").status_code == 403
