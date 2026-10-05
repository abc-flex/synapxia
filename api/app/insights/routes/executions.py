"""Dashboard executions (specs/007-dashboard-catalog, HU-AN05).

Running a dashboard is consumption, not editing: ``ANA/CATALOG`` at read level
plus a live grant on the dashboard. Every attempt past the module gate leaves
exactly one `executions` row — see insights/internal/execution_service.py. There
is deliberately no update or delete route: the only change is the one-time
``finish`` of an in-progress run.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..internal import catalog_service, execution_service as es
from ..internal.dependencies import get_db_session
from ..internal.models import (
    ExecutionCancelled, ExecutionFinish, ExecutionRead, ExecutionStart, ExecutionStarted, LastValues,
)
from ...admin.internal.models import User
from ...internal.permissions import require_privilege
from .catalog import runnable_dashboard

router = APIRouter(tags=["dashboard_executions"])

catalog_reader = require_privilege("ANA", "CATALOG", can_edit=False)


@router.post("/api/dashboards/{dashboard_id}/executions",
             response_model=ExecutionStarted, status_code=201)
def start(
    dashboard_id: int,
    payload: ExecutionStart,
    session: Session = Depends(get_db_session),
    current: User = Depends(catalog_reader),
) -> ExecutionStarted:
    """
    Start a run with the viewer's `values`. Always records one row: no live
    grant / not Published → UNAUTHORIZED + 403; invalid values → FAILED + 400;
    valid → in progress (status null) + 201 with the server-built `launch_url`.
    Grant-bound values are computed here; a submitted one is ignored.
    """
    try:
        return es.start_execution(session, current, dashboard_id, payload.values)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except es.ExecutionUnauthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except es.ExecutionInvalid as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/dashboards/{dashboard_id}/executions/cancelled",
             response_model=ExecutionRead, status_code=201)
def cancelled(
    dashboard_id: int,
    payload: ExecutionCancelled,
    session: Session = Depends(get_db_session),
    current: User = Depends(catalog_reader),
) -> ExecutionRead:
    """Record a parameters window closed without pressing Execute (CANCELLED,
    with the window's values; `duration_ms` clamped). No grant → UNAUTHORIZED + 403."""
    try:
        return es.record_cancelled(session, current, dashboard_id, payload.values, payload.duration_ms)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except es.ExecutionUnauthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/api/dashboards/{dashboard_id}/executions/last-values", response_model=LastValues)
def last_values(
    dashboard_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(catalog_reader),
) -> LastValues:
    """The caller's most recent SUCCESS values for this dashboard, re-checked
    against the current parameters (grant-bound, removed and no-longer-valid
    values left out). Same 404/403 rules as the run form."""
    runnable_dashboard(session, current, dashboard_id)
    return catalog_service.last_values(session, current, dashboard_id)


@router.post("/api/executions/{execution_id}/finish", response_model=ExecutionRead)
def finish(
    execution_id: int,
    payload: ExecutionFinish,
    session: Session = Depends(get_db_session),
    current: User = Depends(catalog_reader),
) -> ExecutionRead:
    """
    Report the outcome of the caller's own in-progress run, once:
    SUCCESS / FAILED / TIMEOUT / CANCELLED. The server computes `duration_ms`.
    404 missing · 403 not yours · 400 bad status · 409 already finished.
    """
    try:
        return es.finish_execution(session, current, execution_id, payload.status, payload.error_message)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except es.ExecutionForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except es.ExecutionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
