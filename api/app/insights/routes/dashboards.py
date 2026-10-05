"""Dashboards (Dashboard Management — specs/006-dashboard-management, HU-AN01).

Grant-scoped inventory of dashboards. Creating one lands it in DRAFT and grants
the creator MANAGE; every other write needs MANAGE on the dashboard. Status
changes follow insights/internal/status_service.py and are enforced here, not
only by the UI's status control.
"""
import logging
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..internal import catalog_service, permissions_service, status_service
from ..internal.dependencies import get_db_session
from ..internal.list_validation import REQUIRED_FIELDS, validate_core_fields
from ..internal.models import (
    Dashboard, DashboardCreate, DashboardFavoriteState, DashboardPermission, DashboardUpdate,
    DashboardWithAccess, FavoriteDashboard, ListOption,
)
from ..internal.source_validation import validate_source_url
from ...admin.internal.models import List as ListModel, User
from ...auth.routes import current_active_user
from ...internal.permissions import check_any_privilege, require_privilege
from ...internal.status import normalize

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])

LIST_OF_VALUES = "LIST_OF_VALUES"


def _ensure_manage(session: Session, user: User, dashboard_id: int) -> None:
    try:
        permissions_service.require_dashboard_manage(session, user, dashboard_id)
    except permissions_service.DashboardAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def _ensure_view(session: Session, user: User, dashboard_id: int) -> None:
    try:
        permissions_service.require_dashboard_view(session, user, dashboard_id)
    except permissions_service.DashboardAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def _with_access(
    dashboard: Dashboard, access: str, scopes: List[str] | None = None, favorite: bool = False,
) -> DashboardWithAccess:
    return DashboardWithAccess(
        **dashboard.model_dump(),
        my_access=access,
        is_favorite=favorite,
        allowed_statuses=status_service.allowed_statuses_for(dashboard.status),
        permission_scopes=scopes or [],
    )


# One definition of "the caller's favorites", shared with the Dashboard Catalog.
_favorite_ids = catalog_service.favorite_ids


def _projection(session: Session, user: User, dashboard: Dashboard) -> DashboardWithAccess:
    """The single-row read projection, with the caller's own access, scopes and favorite."""
    access = permissions_service.user_dashboard_access(session, user, dashboard.id)
    scopes = permissions_service.dashboards_user_scopes(session, user, [dashboard.id])
    favorite = dashboard.id in _favorite_ids(session, user, [dashboard.id])
    return _with_access(dashboard, access, scopes.get(dashboard.id, []), favorite)


def _get_active(session: Session, dashboard_id: int, for_update: bool = False) -> Dashboard:
    query = select(Dashboard).where(Dashboard.id == dashboard_id)
    if for_update:
        query = query.with_for_update()
    dashboard = session.exec(query).first()
    if not dashboard or not dashboard.is_active:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard


# Static paths first, so they are not captured by `/{dashboard_id}`.


@router.get("/with-access", response_model=List[DashboardWithAccess])
def get_all_with_access(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=False)),
) -> List[DashboardWithAccess]:
    """
    Active dashboards the caller can access (Dashboard Management list).

    Non-superusers only see dashboards with a live `dashboard_permissions` grant
    reaching them; the access filter is applied BEFORE `skip`/`limit` so pages
    stay full. Each row carries the caller's `my_access` (MANAGE/VIEW),
    `is_favorite`, `allowed_statuses` (current status + allowed moves) and
    `permission_scopes`.
    """
    query = select(Dashboard).where(Dashboard.is_active == True)  # noqa: E712
    access_map: Dict[int, str] = {}
    if not current.is_superuser:
        access_map = permissions_service.accessible_dashboards(session, current)
        if not access_map:
            return []
        query = query.where(Dashboard.id.in_(list(access_map)))

    rows = session.exec(
        query.order_by(Dashboard.name, Dashboard.id).offset(skip).limit(limit)
    ).all()
    ids = [r.id for r in rows]
    scopes = permissions_service.dashboards_user_scopes(session, current, ids)
    favorites = _favorite_ids(session, current, ids)
    return [
        _with_access(
            r,
            permissions_service.ACCESS_MANAGE if current.is_superuser else access_map[r.id],
            scopes.get(r.id, []),
            r.id in favorites,
        )
        for r in rows
    ]


@router.get("/parameter-lists", response_model=List[ListOption])
def get_parameter_lists(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=False)),
) -> List[ListOption]:
    """
    The lists an analyst may attach to a parameter as its allowed values: active
    `lists` of type LIST_OF_VALUES, by name. Its own endpoint because
    `/api/lists/*` is gated `ADMIN/LISTS`, which analysts do not hold.
    """
    rows = session.exec(
        select(ListModel)
        .where(ListModel.type == LIST_OF_VALUES, ListModel.is_active == True)  # noqa: E712
        .order_by(ListModel.name)
    ).all()
    return [ListOption(value=r.code, label=r.name) for r in rows]


@router.get("/{dashboard_id}", response_model=DashboardWithAccess)
def get(
    dashboard_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=False)),
) -> DashboardWithAccess:
    """One dashboard with the caller's access. Requires VIEW on it."""
    dashboard = _get_active(session, dashboard_id)
    _ensure_view(session, current, dashboard_id)
    return _projection(session, current, dashboard)


@router.post("/", response_model=DashboardWithAccess, status_code=201)
def create(
    payload: DashboardCreate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=True)),
) -> DashboardWithAccess:
    """
    Register a dashboard. It always starts in DRAFT (any other `status` → 400)
    and the creator is granted USER/MANAGE in the same transaction, so a new
    dashboard never drops out of its creator's list.
    """
    fields = payload.model_dump(exclude_unset=True)
    try:
        validate_core_fields(session, fields, required=REQUIRED_FIELDS)
        status = status_service.validate_create_status(fields.pop("status", None))
        validate_source_url(payload.sources_types, payload.source_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    dashboard = Dashboard(**fields, status=status)
    dashboard.name = dashboard.name.strip()
    dashboard.source_url = dashboard.source_url.strip()
    session.add(dashboard)
    session.flush()
    session.add(DashboardPermission(
        dashboard=dashboard.id, target_type="USER", target_code=str(current.id),
        access_level=permissions_service.ACCESS_MANAGE,
    ))
    session.commit()
    session.refresh(dashboard)
    logger.info("Dashboard created: id=%s name=%r by user=%s",
                dashboard.id, dashboard.name, current.id)
    return _with_access(dashboard, permissions_service.ACCESS_MANAGE,
                        ["USER"] if not current.is_superuser else [])


@router.put("/{dashboard_id}", response_model=DashboardWithAccess)
def update(
    dashboard_id: int,
    payload: DashboardUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=True)),
) -> DashboardWithAccess:
    """
    Update a dashboard's core fields (Dashboard Management → Core Fields).

    Only sent keys are applied, and only if ALL of them validate — a refused
    request changes nothing. Requires MANAGE. A status change must be one of
    DRAFT → PUBLISHED, PUBLISHED → ARCHIVED/RETIRED, ARCHIVED → PUBLISHED/RETIRED
    (→ 400 otherwise). `source_url` is re-checked whenever it or the source changes.
    """
    dashboard = _get_active(session, dashboard_id, for_update=True)
    _ensure_manage(session, current, dashboard_id)

    updates = payload.model_dump(exclude_unset=True)
    previous_status = dashboard.status
    try:
        if "status" in updates:
            if status_service.validate_transition(dashboard.status, updates["status"]):
                updates["status"] = normalize(updates["status"])
            else:
                updates.pop("status")
        validate_core_fields(session, updates, required=REQUIRED_FIELDS)
        if "source_url" in updates or "sources_types" in updates:
            validate_source_url(
                updates.get("sources_types", dashboard.sources_types),
                updates.get("source_url", dashboard.source_url),
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    for key, value in updates.items():
        setattr(dashboard, key, value.strip() if key in ("name", "source_url") else value)
    dashboard.updated_at = datetime.utcnow()
    session.add(dashboard)
    session.commit()
    session.refresh(dashboard)
    if "status" in updates:
        logger.info("Dashboard status changed: id=%s %s → %s by user=%s",
                    dashboard.id, previous_status, dashboard.status, current.id)
    return _projection(session, current, dashboard)


@router.delete("/{dashboard_id}", response_model=Dashboard)
def delete(
    dashboard_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=True)),
) -> Dashboard:
    """Logically remove a dashboard (`is_active` = false). Its parameters and
    grants are retained. Requires MANAGE."""
    dashboard = _get_active(session, dashboard_id)
    _ensure_manage(session, current, dashboard_id)
    dashboard.is_active = False
    dashboard.updated_at = datetime.utcnow()
    session.add(dashboard)
    session.commit()
    session.refresh(dashboard)
    logger.info("Dashboard removed: id=%s by user=%s", dashboard_id, current.id)
    return dashboard


# ── Favorites (same behaviour as Asset / Initiative Management) ──────────────


def _ensure_favorite_module(session: Session, user: User) -> None:
    """Favorites are personal and shared by Management and the Catalog, so
    either module option at read level opens them."""
    check_any_privilege(session, user, "ANA", ["DASHBOARDS", "CATALOG"], can_edit=False)


def _set_favorite(
    session: Session, user: User, dashboard_id: int, on: bool,
) -> DashboardFavoriteState:
    """Mark / clear the caller's favorite. Favoriting is personal, not an edit:
    read-level module access + VIEW on the dashboard suffice. Idempotent; a
    removal is logical and marking again restores the row."""
    _get_active(session, dashboard_id)
    _ensure_view(session, user, dashboard_id)
    row = session.get(FavoriteDashboard, (user.id, dashboard_id))
    if row is None and on:
        session.add(FavoriteDashboard(user_id=user.id, dashboard=dashboard_id))
    elif row is not None and row.is_active != on:
        row.is_active = on
        row.updated_at = datetime.utcnow()
        session.add(row)
    session.commit()
    return DashboardFavoriteState(dashboard=dashboard_id, is_favorite=on)


@router.put("/{dashboard_id}/favorite", response_model=DashboardFavoriteState)
def add_favorite(
    dashboard_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> DashboardFavoriteState:
    """Mark the dashboard as one of the caller's favorites. Requires VIEW on it
    and read access to Dashboard Management OR the Dashboard Catalog (the same
    favorites show in both — specs/007-dashboard-catalog R2)."""
    _ensure_favorite_module(session, current)
    return _set_favorite(session, current, dashboard_id, True)


@router.delete("/{dashboard_id}/favorite", response_model=DashboardFavoriteState)
def remove_favorite(
    dashboard_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> DashboardFavoriteState:
    """Remove the dashboard from the caller's favorites. Same rules as marking."""
    _ensure_favorite_module(session, current)
    return _set_favorite(session, current, dashboard_id, False)
