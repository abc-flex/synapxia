"""Dashboard Management foundations — status rules, per-dashboard access
resolution and the grants read route (specs/006-dashboard-management)."""
import pytest

from app.collab.internal.models import Assignment
from app.insights.internal import permissions_service as ps
from app.insights.internal import status_service as ss
from tests.ana_helpers import (
    FUTURE, PAST, data, mk_dashboard, mk_grant, override, seed_privileges, setup_owner,
    superuser, user,
)

STATUSES = ["DRAFT", "PUBLISHED", "ARCHIVED", "RETIRED"]
ALLOWED = {
    ("DRAFT", "PUBLISHED"),
    ("PUBLISHED", "ARCHIVED"), ("PUBLISHED", "RETIRED"),
    ("ARCHIVED", "PUBLISHED"), ("ARCHIVED", "RETIRED"),
}


# ── status_service ──────────────────────────────────────────────────────────

def test_allowed_statuses_per_status():
    assert ss.allowed_statuses_for("DRAFT") == ["DRAFT", "PUBLISHED"]
    assert ss.allowed_statuses_for("PUBLISHED") == ["PUBLISHED", "ARCHIVED", "RETIRED"]
    assert ss.allowed_statuses_for("ARCHIVED") == ["ARCHIVED", "PUBLISHED", "RETIRED"]
    assert ss.allowed_statuses_for("RETIRED") == ["RETIRED"]
    assert ss.allowed_statuses_for("LEGACY") == ["LEGACY"]
    assert ss.allowed_statuses_for("2-published") == ["PUBLISHED", "ARCHIVED", "RETIRED"]


def test_validate_create_status():
    assert ss.validate_create_status(None) == "DRAFT"
    assert ss.validate_create_status("") == "DRAFT"
    assert ss.validate_create_status("draft") == "DRAFT"
    with pytest.raises(ss.StatusTransitionForbidden):
        ss.validate_create_status("PUBLISHED")


@pytest.mark.parametrize("current", STATUSES)
@pytest.mark.parametrize("new", STATUSES)
def test_transition_matrix(current, new):
    if current == new:
        assert ss.validate_transition(current, new) is False
    elif (current, new) in ALLOWED:
        assert ss.validate_transition(current, new) is True
    else:
        with pytest.raises(ss.StatusTransitionForbidden):
            ss.validate_transition(current, new)


def test_blank_new_status_is_noop():
    assert ss.validate_transition("PUBLISHED", None) is False
    assert ss.validate_transition("PUBLISHED", "") is False


# ── permissions_service ─────────────────────────────────────────────────────

def test_public_grant_gives_view(session):
    d = mk_dashboard(session)
    mk_grant(session, d.id, "PUBLIC", "ALL", access_level="VIEW")
    assert ps.user_dashboard_access(session, user(5), d.id) == "VIEW"


def test_team_grant_through_assignment(session):
    d = mk_dashboard(session)
    mk_grant(session, d.id, "TEAM", "ANALYTICS", access_level="MANAGE")
    session.add(Assignment(team="ANALYTICS", user_id=7, role="TL", is_active=True))
    session.commit()
    assert ps.user_dashboard_access(session, user(7), d.id) == "MANAGE"
    assert ps.user_dashboard_access(session, user(8), d.id) is None


def test_manage_beats_view(session):
    d = mk_dashboard(session)
    mk_grant(session, d.id, "PUBLIC", "ALL", access_level="VIEW")
    mk_grant(session, d.id, "USER", "3", access_level="MANAGE")
    assert ps.user_dashboard_access(session, user(3), d.id) == "MANAGE"


def test_expired_and_future_grants_do_not_apply(session):
    d = mk_dashboard(session)
    mk_grant(session, d.id, "USER", "3", valid_to=PAST)
    mk_grant(session, d.id, "USER", "4", valid_from=FUTURE)
    assert ps.user_dashboard_access(session, user(3), d.id) is None
    assert ps.user_dashboard_access(session, user(4), d.id) is None


def test_superuser_is_manage(session):
    d = mk_dashboard(session)
    assert ps.user_dashboard_access(session, superuser(), d.id) == "MANAGE"
    with pytest.raises(ps.DashboardAccessForbidden):
        ps.require_dashboard_view(session, user(1), d.id)


# ── GET /api/dashboard_permissions/dashboard/{id} ───────────────────────────

BASE = "/api/dashboard_permissions/dashboard"


def test_grants_read_requires_token(client, session):
    d = mk_dashboard(session)
    assert client.get(f"{BASE}/{d.id}").status_code == 401


def test_grants_read_requires_rbac(client, session):
    d = mk_dashboard(session)
    mk_grant(session, d.id, "USER", "1", access_level="MANAGE")
    override(user(1))
    assert client.get(f"{BASE}/{d.id}").status_code == 403


def test_grants_read_requires_view(client, session):
    seed_privileges(session)
    d = mk_dashboard(session)
    override(user(1))
    assert client.get(f"{BASE}/{d.id}").status_code == 403
    assert client.get(f"{BASE}/999").status_code == 404


def test_grants_read_excludes_revoked_includes_future(client, session):
    d = setup_owner(session, access="VIEW")
    mk_grant(session, d.id, "TEAM", "A", access_level="VIEW", valid_from=FUTURE)
    mk_grant(session, d.id, "TEAM", "B", access_level="VIEW", valid_to=PAST)
    override(user(1))
    r = client.get(f"{BASE}/{d.id}")
    assert r.status_code == 200
    assert {p["target_code"] for p in data(r)} == {"1", "A"}
