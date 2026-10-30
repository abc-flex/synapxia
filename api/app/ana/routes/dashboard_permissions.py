"""Dashboard permissions (Dashboard Management → Permissions tab).

Mirrors ``inits/routes/init_permissions.py`` (Constitution "Per-resource
permissions"): module RBAC ``ANA/DASHBOARDS`` is the outer gate, MANAGE on the
dashboard the inner one for every write (so a VIEW holder cannot grant
themselves more), and a grant is revoked — ``valid_to`` set to now — never
deleted. Reads additionally require VIEW on the dashboard.
"""
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..internal import permissions_service
from ..internal.dependencies import get_db_session
from ..internal.models import (
    Dashboard, DashboardPermission, DashboardPermissionCreate, DashboardPermissionUpdate,
    Parameter, RevokedDashboardPermission,
)
from ...admin.internal.models import User
from ...internal.list_values import validate_list_value
from ...internal.permissions import require_privilege
from ...internal.resource_permissions import SCOPE_PUBLIC, as_naive_utc

PUBLIC_CODE = "ALL"

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard_permissions", tags=["dashboard_permissions"])


def _guard(check, session: Session, user: User, dashboard_id: int) -> None:
    try:
        check(session, user, dashboard_id)
    except permissions_service.DashboardAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/dashboard/{dashboard_id}", response_model=List[DashboardPermission])
def get_by_dashboard(
    dashboard_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=False)),
) -> List[DashboardPermission]:
    """Live grants of a dashboard (not revoked; future-dated included)."""
    dashboard = session.get(Dashboard, dashboard_id)
    if not dashboard or not dashboard.is_active:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    _guard(permissions_service.require_dashboard_view, session, current, dashboard_id)
    return session.exec(
        select(DashboardPermission)
        .where(DashboardPermission.dashboard == dashboard_id,
               permissions_service.not_revoked_clause())
        .order_by(DashboardPermission.id)
        .offset(skip).limit(limit)
    ).all()


def _check_window(valid_from, valid_to) -> None:
    vf, vt = as_naive_utc(valid_from), as_naive_utc(valid_to)
    if vt is not None and vt <= (vf if vf is not None else datetime.utcnow()):
        raise HTTPException(status_code=400, detail="valid_to must be later than valid_from")


def _check_lists(session: Session, target_type=None, access_level=None) -> None:
    try:
        validate_list_value(session, "TARGET_TYPE", target_type)
        validate_list_value(session, "ACCESS_LEVEL", access_level)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _live_grant(session: Session, user: User, permission_id: int) -> DashboardPermission:
    """The grant, after checking MANAGE on its dashboard; 400 if already revoked."""
    permission = session.get(DashboardPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Dashboard permission not found")
    _guard(permissions_service.require_dashboard_manage, session, user, permission.dashboard)
    if permissions_service.is_revoked(permission):
        raise HTTPException(
            status_code=400, detail=f"Dashboard permission '{permission_id}' is revoked")
    return permission


@router.post("/", response_model=DashboardPermission, status_code=201)
def create(
    permission: DashboardPermissionCreate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=True)),
) -> DashboardPermission:
    """Grant access to a dashboard. Requires MANAGE on it. A PUBLIC grant is
    stored with target_code 'ALL'. A live duplicate `(dashboard, target_type,
    target_code, access_level)` → 409; a revoked one does not block re-granting."""
    dashboard = session.get(Dashboard, permission.dashboard)
    if not dashboard or not dashboard.is_active:
        raise HTTPException(
            status_code=400, detail=f"Dashboard with id '{permission.dashboard}' does not exist")
    _guard(permissions_service.require_dashboard_manage, session, current, permission.dashboard)
    _check_lists(session, permission.target_type, permission.access_level)
    _check_window(permission.valid_from, permission.valid_to)

    data = permission.model_dump(exclude_unset=True)
    if permission.target_type == SCOPE_PUBLIC:
        data["target_code"] = PUBLIC_CODE
    elif not (permission.target_code or "").strip() or permission.target_code == PUBLIC_CODE:
        raise HTTPException(status_code=400, detail="target_code is required for this target type")
    if data.get("valid_from") is None:
        data.pop("valid_from", None)

    existing = session.exec(
        select(DashboardPermission).where(
            DashboardPermission.dashboard == permission.dashboard,
            DashboardPermission.target_type == permission.target_type,
            DashboardPermission.target_code == data["target_code"],
            DashboardPermission.access_level == permission.access_level,
            permissions_service.not_revoked_clause(),
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An active permission for this target + access level already exists")
    try:
        db = DashboardPermission(**data)
        session.add(db)
        session.commit()
        session.refresh(db)
    except IntegrityError as e:
        session.rollback()
        logger.error("Integrity error creating dashboard permission: %s", e)
        raise HTTPException(status_code=409, detail="Dashboard permission conflict")
    logger.info("Dashboard permission created: dashboard=%s %s:%s → %s by user=%s",
                db.dashboard, db.target_type, db.target_code, db.access_level, current.id)
    return db


@router.put("/{permission_id}", response_model=DashboardPermission)
def update(
    permission_id: int,
    update: DashboardPermissionUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=True)),
) -> DashboardPermission:
    """Partially update a live grant. Requires MANAGE on its dashboard."""
    permission = _live_grant(session, current, permission_id)
    changes = update.model_dump(exclude_unset=True)
    _check_lists(session, access_level=changes.get("access_level"))
    _check_window(changes.get("valid_from", permission.valid_from),
                  changes.get("valid_to", permission.valid_to))
    for key, value in changes.items():
        if value is not None or key == "valid_to":
            setattr(permission, key, value)
    session.add(permission)
    session.commit()
    session.refresh(permission)
    return permission


@router.delete("/{permission_id}", response_model=RevokedDashboardPermission)
def revoke(
    permission_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=True)),
) -> RevokedDashboardPermission:
    """Revoke a grant by closing its validity window (`valid_to` = now); the row
    is retained. An already-scheduled future `valid_to` is overwritten so the
    revoke is immediate. Requires MANAGE on the dashboard. Active parameters
    bound to the grant keep their binding — it simply stops applying — and are
    listed in `bound_parameters`."""
    permission = _live_grant(session, current, permission_id)
    permission.valid_to = datetime.utcnow()
    session.add(permission)
    session.commit()
    session.refresh(permission)
    bound = session.exec(
        select(Parameter.name).where(
            Parameter.context_binding == permission_id,
            Parameter.is_active == True,  # noqa: E712
        ).order_by(Parameter.name)
    ).all()
    logger.info("Dashboard permission revoked: %s by user=%s (bound parameters: %s)",
                permission_id, current.id, list(bound))
    return RevokedDashboardPermission(**permission.model_dump(), bound_parameters=list(bound))
