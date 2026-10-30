"""Dashboard Catalog (specs/007-dashboard-catalog, HU-AN04 / HU-AN05).

Consumer-facing reads, gated on ``ANA/CATALOG`` at read level — Collaborator
and Reviewer hold it without edit rights and do not hold ``ANA/DASHBOARDS``, so
the Management reads would answer them 403. Only active PUBLISHED dashboards
reached by a live grant appear here.

Registered before the dashboards router so ``/catalog`` is not captured by
``GET /api/dashboards/{dashboard_id}``.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..internal import catalog_service, execution_service
from ..internal.dependencies import get_db_session
from ..internal.models import CatalogDashboard, Dashboard, RunForm
from ...admin.internal.models import User
from ...internal.permissions import require_privilege

router = APIRouter(prefix="/api/dashboards", tags=["dashboard_catalog"])


def runnable_dashboard(session: Session, user: User, dashboard_id: int) -> Dashboard:
    """404 when missing/inactive; 403 when not Published or not granted. A read
    — nothing is recorded."""
    dashboard = session.get(Dashboard, dashboard_id)
    if not dashboard or not dashboard.is_active:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    try:
        execution_service.check_runnable(session, user, dashboard)
    except execution_service.ExecutionUnauthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return dashboard


@router.get("/catalog", response_model=List[CatalogDashboard])
def get_catalog(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "CATALOG", can_edit=False)),
) -> List[CatalogDashboard]:
    """
    Published, active dashboards the caller can access (superusers: all of
    them), ordered by name. Visibility is applied BEFORE `skip`/`limit`. Each
    row carries `is_favorite`, `permission_scopes` (drives the privileges
    filter) and `parameter_count`. `source_url` is not exposed.
    """
    return catalog_service.list_catalog(session, current, skip, limit)


@router.get("/{dashboard_id}/run-form", response_model=RunForm)
def get_run_form(
    dashboard_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "CATALOG", can_edit=False)),
) -> RunForm:
    """
    What the detail and the parameters window need, resolved for the caller:
    each active parameter's effective source (GRANT with its fixed value, LIST
    with every language's options, or INPUT), the launch `mode` (VIEWER for
    Internal Page, TAB otherwise) and `has_last_values`.
    """
    dashboard = runnable_dashboard(session, current, dashboard_id)
    return catalog_service.build_run_form(session, current, dashboard)
