"""Shared fixtures-as-functions for the Dashboard Management test modules
(specs/006-dashboard-management). Same style as inits_helpers.py, whose generic
helpers are reused rather than copied."""
from app.admin.internal.models import List as ListModel, Privilege
from app.insights.internal.models import Dashboard, DashboardPermission, Parameter
from tests.inits_helpers import (  # noqa: F401 — re-exported for the test modules
    FUTURE, NOW, PAST, data, mk_list, mk_user_row, override, superuser, user,
)

ANALYST = "ADMINISTRATIVE"


def seed_privileges(session, profile=ANALYST, options=("DASHBOARDS",), can_edit=True):
    for option in options:
        session.add(Privilege(
            profile=profile, module="ANA", option=option,
            can_edit=can_edit, is_active=True))
    session.commit()


def mk_list_def(session, code, type="LIST_OF_VALUES", name=None, active=True):
    """A `lists` row (the parameter `list` FK target)."""
    row = ListModel(code=code, name=name or code, description=None,
                    type=type, module=None, is_active=active)
    session.add(row)
    session.commit()
    return row


def seed_ana_lists(session):
    """The list values Dashboard Management validates against, plus two
    selectable lists: GRANULARITY (LIST_OF_VALUES) and TREE (not LoV)."""
    mk_list(session, "DASHBOARD_TYPE", [("DASHBOARD", "Dashboard"), ("REPORT", "Report")])
    mk_list(session, "SOURCE_TYPE", [
        ("INTERNAL_PAGE", "Internal Page"), ("POWER_BI", "Power BI"),
        ("LOOKER_STUDIO", "Looker Studio")])
    mk_list(session, "DASHBOARD_STATUS", [
        ("DRAFT", "Draft"), ("PUBLISHED", "Published"),
        ("ARCHIVED", "Archived"), ("RETIRED", "Retired")])
    mk_list(session, "PARAM_TYPE", [
        ("STRING", "String"), ("NUMBER", "Number"),
        ("BOOLEAN", "Boolean"), ("DATE", "Date")])
    mk_list(session, "TARGET_TYPE", [
        ("USER", "Users"), ("ROLE", "Roles"), ("PROJECT", "Projects"),
        ("TEAM", "Teams"), ("UNIT", "Units"), ("PUBLIC", "Public")])
    mk_list(session, "ACCESS_LEVEL", [("VIEW", "View"), ("MANAGE", "Manage")])
    mk_list_def(session, "GRANULARITY", name="Granularity")
    mk_list(session, "GRANULARITY", [("DAY", "Day"), ("WEEK", "Week"), ("MONTH", "Month")])
    mk_list_def(session, "TREE", type="HIERARCHY", name="Tree")


def mk_dashboard(session, id=None, name="Dash", status="DRAFT", type="DASHBOARD",
                 sources_types="POWER_BI", source_url="https://x.example/d", **kw):
    row = Dashboard(id=id, name=name, status=status, type=type,
                    sources_types=sources_types, source_url=source_url, **kw)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def mk_grant(session, dashboard, target_type="USER", target_code="1",
             access_level="MANAGE", valid_from=None, valid_to=None):
    row = DashboardPermission(
        dashboard=dashboard, target_type=target_type, target_code=target_code,
        access_level=access_level, valid_from=valid_from or PAST, valid_to=valid_to)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def mk_param(session, dashboard, name, label=None, data_type="STRING", **kw):
    row = Parameter(dashboard=dashboard, name=name, label=label or name,
                    data_type=data_type, **kw)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def setup_owner(session, access="MANAGE", status="DRAFT", **kw):
    """RBAC for the analyst profile + lists + one dashboard granted to user 1."""
    seed_privileges(session)
    seed_ana_lists(session)
    dash = mk_dashboard(session, status=status, **kw)
    mk_grant(session, dash.id, "USER", "1", access_level=access)
    return dash
