"""Dashboard executions (specs/007-dashboard-catalog, HU-AN05 — research R4/R5/R8).

Every run attempt that passes the module gate leaves exactly ONE `executions`
row, in two steps:

1. ``start_execution`` checks access (→ UNAUTHORIZED row + raise), then the
   values (→ FAILED row + raise); a valid run is inserted with status NULL
   ("in progress") and the server-built launch address is returned.
2. ``finish_execution`` sets the outcome ONCE (SUCCESS / FAILED / TIMEOUT /
   CANCELLED) — only the outcome is known in the browser (tab opened, popup
   blocked, viewer loaded, timed out, closed early). A second finish is a
   conflict, so the record is append-only in practice.

A parameters window closed without running is ``record_cancelled``. The actor
is always the session user; grant-bound values are always computed here and a
submitted one is ignored.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlmodel import Session, select

from . import catalog_service
from . import parameter_validation as pv
from . import permissions_service
from .models import (
    EXEC_CANCELLED, EXEC_FAILED, EXEC_UNAUTHORIZED, FINISH_STATUSES, MODE_VIEWER,
    SOURCE_DEFAULT, Dashboard, Execution, ExecutionRead, ExecutionStarted,
)
from ...admin.internal.models import User
from ...internal.resource_permissions import as_naive_utc

logger = logging.getLogger(__name__)

MAX_DURATION_MS = 86_400_000


class ExecutionUnauthorized(Exception):
    """No live grant, or the dashboard is not active and Published (→ 403)."""


class ExecutionInvalid(ValueError):
    """A submitted value does not validate (→ 400)."""


class ExecutionForbidden(Exception):
    """The execution belongs to another user (→ 403)."""


class ExecutionConflict(Exception):
    """The execution's outcome is already set (→ 409)."""


def _get_dashboard(session: Session, dashboard_id: int) -> Dashboard:
    dashboard = session.get(Dashboard, dashboard_id)
    if dashboard is None:
        raise LookupError("Dashboard not found")
    return dashboard


def check_runnable(session: Session, user: User, dashboard: Dashboard) -> None:
    if not catalog_service.is_catalog_visible(dashboard):
        raise ExecutionUnauthorized("This dashboard is not available in the catalog.")
    if user.is_superuser:
        return
    if permissions_service.user_dashboard_access(session, user, dashboard.id) is None:
        raise ExecutionUnauthorized(f"Access to dashboard {dashboard.id} is not granted.")


def as_text(value: Any) -> str:
    """A submitted JSON scalar as the string form parameters use ("" = none).
    Booleans become "true"/"false"; objects and arrays are not values."""
    if value is None or isinstance(value, (dict, list)):
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def _sanitised(session: Session, dashboard_id: int, submitted: Dict[str, Any]) -> Dict[str, str]:
    """Submitted values restricted to active parameter names, truncated."""
    names = {p.name for p in catalog_service.active_parameters(session, dashboard_id)}
    out = {}
    for k, v in (submitted or {}).items():
        text = as_text(v)
        if k in names and text:
            out[k] = text[:pv.MAX_VALUE_LENGTH]
    return out


def resolve_values(
    effective: List[catalog_service.EffectiveParam], submitted: Dict[str, Any],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Apply bindings and defaults, then validate. Returns (values, sources);
    raises ExecutionInvalid with the first violation."""
    submitted = submitted or {}
    values: Dict[str, str] = {}
    sources: Dict[str, str] = {}
    for e in effective:
        p = e.param
        if e.source == pv.SOURCE_GRANT:
            values[p.name], sources[p.name] = e.bound_value, pv.SOURCE_GRANT
            continue
        value = as_text(submitted.get(p.name))
        if value == "":
            value = (p.default_value or "").strip()
        if value == "":
            if p.is_required:
                raise ExecutionInvalid(f"'{p.label}' is required")
            continue
        if e.list_unavailable:
            raise ExecutionInvalid(
                f"This dashboard cannot be run: the list of '{p.label}' has no values")
        try:
            pv.validate_run_value(
                p.label, p.data_type, value, e.allowed if e.source == pv.SOURCE_LIST else None)
        except ValueError as exc:
            raise ExecutionInvalid(str(exc))
        values[p.name] = value
        sources[p.name] = SOURCE_DEFAULT if value == (p.default_value or "").strip() else e.source
    return values, sources


def build_launch_url(dashboard: Dashboard, values: Dict[str, str]) -> Tuple[str, str]:
    """``source_url`` + one ``name=value`` per value (existing query kept);
    Internal Page also gets ``embed=1`` so it renders without the app shell."""
    mode = catalog_service.launch_mode(dashboard)
    parts = urlsplit((dashboard.source_url or "").strip())
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(values.items())
    if mode == MODE_VIEWER:
        query.append(("embed", "1"))
    return urlunsplit(parts._replace(query=urlencode(query))), mode


def _insert(session: Session, **fields) -> Execution:
    row = Execution(**fields)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def start_execution(
    session: Session, user: User, dashboard_id: int, submitted: Dict[str, Any],
) -> ExecutionStarted:
    dashboard = _get_dashboard(session, dashboard_id)
    try:
        check_runnable(session, user, dashboard)
    except ExecutionUnauthorized as exc:
        _insert(session, dashboard=dashboard_id, user_id=user.id, status=EXEC_UNAUTHORIZED,
                error_message=str(exc),
                payload={"values": _sanitised(session, dashboard_id, submitted)})
        logger.info("Execution refused: dashboard=%s user=%s status=UNAUTHORIZED",
                    dashboard_id, user.id)
        raise

    effective = catalog_service.resolve_effective_parameters(session, user, dashboard_id)
    try:
        values, sources = resolve_values(effective, submitted)
    except ExecutionInvalid as exc:
        _insert(session, dashboard=dashboard_id, user_id=user.id, status=EXEC_FAILED,
                error_message=str(exc)[:pv.MAX_VALUE_LENGTH],
                payload={"values": _sanitised(session, dashboard_id, submitted)})
        logger.info("Execution refused: dashboard=%s user=%s status=FAILED reason=%r",
                    dashboard_id, user.id, str(exc))
        raise

    launch_url, mode = build_launch_url(dashboard, values)
    row = _insert(session, dashboard=dashboard_id, user_id=user.id, status=None,
                  payload={"values": values, "sources": sources, "mode": mode})
    logger.info("Execution started: id=%s dashboard=%s user=%s mode=%s",
                row.id, dashboard_id, user.id, mode)
    return ExecutionStarted(execution_id=row.id, launch_url=launch_url, mode=mode)


def finish_execution(
    session: Session, user: User, execution_id: int, status: str, error_message: Optional[str],
) -> ExecutionRead:
    row = session.exec(
        select(Execution).where(Execution.id == execution_id).with_for_update()
    ).first()
    if row is None:
        raise LookupError("Execution not found")
    if row.user_id != user.id:
        raise ExecutionForbidden("This execution belongs to another user.")
    status = (status or "").strip().upper()
    if status not in FINISH_STATUSES:
        raise ValueError(f"'status' must be one of {', '.join(FINISH_STATUSES)}")
    if row.status is not None:
        raise ExecutionConflict("This execution's outcome is already recorded.")
    elapsed = datetime.utcnow() - as_naive_utc(row.executed_at)
    row.status = status
    row.duration_ms = max(0, min(MAX_DURATION_MS, int(elapsed.total_seconds() * 1000)))
    row.error_message = (error_message or None) and error_message[:pv.MAX_VALUE_LENGTH]
    session.add(row)
    session.commit()
    session.refresh(row)
    logger.info("Execution finished: id=%s dashboard=%s user=%s status=%s duration_ms=%s",
                row.id, row.dashboard, user.id, row.status, row.duration_ms)
    return ExecutionRead(**row.model_dump())


def record_cancelled(
    session: Session, user: User, dashboard_id: int,
    submitted: Dict[str, Any], duration_ms: Optional[int],
) -> ExecutionRead:
    dashboard = _get_dashboard(session, dashboard_id)
    values = _sanitised(session, dashboard_id, submitted)
    try:
        check_runnable(session, user, dashboard)
    except ExecutionUnauthorized as exc:
        _insert(session, dashboard=dashboard_id, user_id=user.id, status=EXEC_UNAUTHORIZED,
                error_message=str(exc), payload={"values": values})
        raise
    duration = None if duration_ms is None else max(0, min(MAX_DURATION_MS, int(duration_ms)))
    row = _insert(session, dashboard=dashboard_id, user_id=user.id, status=EXEC_CANCELLED,
                  duration_ms=duration, payload={"values": values})
    logger.info("Execution cancelled: id=%s dashboard=%s user=%s", row.id, dashboard_id, user.id)
    return ExecutionRead(**row.model_dump())
