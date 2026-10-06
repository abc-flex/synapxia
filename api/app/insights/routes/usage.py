"""Usage Metrics (specs/008-usage-metrics, HU-AN07).

Read-only manager view over ``executions``, gated on ``ANA/USAGE`` at read
level. Inside the gate the scope is resolved per caller: superusers and
Administrators see every execution, anyone else only executions of the
dashboards they MANAGE (``usage_service.scope_for``). Responses are aggregates
only — no user id, payload or individual execution is ever returned.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..internal import usage_service
from ..internal.dependencies import get_db_session
from ..internal.models import UsageErrors, UsageMetrics
from ...admin.internal.models import User
from ...internal.permissions import require_privilege

router = APIRouter(prefix="/api/usage", tags=["usage_metrics"])


@router.get("/metrics", response_model=UsageMetrics)
def get_metrics(
    date_from: Optional[str] = Query(None, description="Local date YYYY-MM-DD, inclusive"),
    date_to: Optional[str] = Query(None, description="Local date YYYY-MM-DD, inclusive"),
    unit: Optional[str] = Query(None, description="Business-unit code (includes sub-units)"),
    team: Optional[str] = Query(None, description="Team code, or __none__ for 'No team'"),
    project: Optional[str] = Query(None, description="Project code, or __none__ for 'No project'"),
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "USAGE", can_edit=False)),
) -> UsageMetrics:
    """
    One aggregate document for the period: headline figures (with change
    against the preceding period of equal length), timeline buckets, the
    dashboards table (used + unused rows), the unit tree, team rows and project
    rows. The `unit`/`team`/`project` filter (one at a time) narrows the
    headline, timeline and dashboards table, not the adoption sections.
    """
    try:
        return usage_service.build_metrics(
            session, current, date_from, date_to, unit, team, project)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/dashboards/{dashboard_id}/errors", response_model=UsageErrors)
def get_dashboard_errors(
    dashboard_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    unit: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "USAGE", can_edit=False)),
) -> UsageErrors:
    """The most frequent error messages of one dashboard in the period. 404
    when the dashboard does not exist or is outside the caller's scope (the
    same answer, so existence is not revealed)."""
    try:
        return usage_service.dashboard_errors(
            session, current, dashboard_id, date_from, date_to, unit, team, limit, project)
    except usage_service.UsageNotFound:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
