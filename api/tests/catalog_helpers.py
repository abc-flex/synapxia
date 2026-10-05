"""Helpers for the Dashboard Catalog test modules (specs/007-dashboard-catalog)."""
from app.insights.internal.models import Execution
from tests.ana_helpers import (  # noqa: F401 — re-exported
    PAST, data, mk_dashboard, mk_grant, mk_list, mk_list_def, mk_param, override,
    seed_ana_lists, seed_privileges, superuser, user,
)

VIEWER = "COLLABORATOR"


def viewer(id=1, unit="ENG"):
    """A catalog consumer: COLLABORATOR, holding only ANA/CATALOG (read)."""
    return user(id=id, unit=unit, profile=VIEWER)


def setup_catalog(session, status="PUBLISHED", grant=("USER", "1"), access="VIEW", **kw):
    """CATALOG read RBAC for COLLABORATOR + lists + one dashboard granted per `grant`."""
    seed_privileges(session, profile=VIEWER, options=("CATALOG",), can_edit=False)
    seed_ana_lists(session)
    dash = mk_dashboard(session, status=status, **kw)
    if grant:
        mk_grant(session, dash.id, grant[0], grant[1], access_level=access)
    return dash


def executions(session, dashboard_id=None):
    session.expire_all()
    rows = session.query(Execution).order_by(Execution.id).all()
    return [r for r in rows if dashboard_id is None or r.dashboard == dashboard_id]


def mk_execution(session, dashboard, user_id=1, status="SUCCESS", payload=None, executed_at=None):
    row = Execution(dashboard=dashboard, user_id=user_id, status=status, payload=payload,
                    **({"executed_at": executed_at} if executed_at else {}))
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
