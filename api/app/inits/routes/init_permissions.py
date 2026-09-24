"""Initiative permissions (Initiative Management → Permissions tab).

Mirrors ``lib/routes/asset_permissions.py`` (Constitution "Per-resource
permissions"): module RBAC is the outer gate, MANAGE on the initiative the inner
one for every write (so a VIEW holder cannot grant themselves more), and a grant
is revoked — ``valid_to`` set to now — never deleted. Reads additionally require
VIEW on the initiative.
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
    InitPermission, InitPermissionCreate, InitPermissionUpdate, Initiative,
)
from ...admin.internal.models import User
from ...internal.permissions import require_privilege
from ...internal.resource_permissions import as_naive_utc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/init_permissions", tags=["init_permissions"])


def _guard(check, session: Session, user: User, init_id: int) -> None:
    try:
        check(session, user, init_id)
    except permissions_service.InitAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def _check_window(valid_from, valid_to) -> None:
    vf, vt = as_naive_utc(valid_from), as_naive_utc(valid_to)
    if vf is not None and vt is not None and vt <= vf:
        raise HTTPException(status_code=400, detail="valid_to must be later than valid_from")


@router.get("/init/{init_id}", response_model=List[InitPermission])
def get_by_init(
    init_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=False)),
) -> List[InitPermission]:
    """Live grants of an initiative (not revoked; future-dated included)."""
    if not session.get(Initiative, init_id):
        raise HTTPException(status_code=404, detail="Initiative not found")
    _guard(permissions_service.require_init_view, session, current, init_id)
    return session.exec(
        select(InitPermission)
        .where(InitPermission.init == init_id, permissions_service.not_revoked_clause())
        .order_by(InitPermission.id)
        .offset(skip).limit(limit)
    ).all()


@router.post("/", response_model=InitPermission, status_code=201)
def create(
    permission: InitPermissionCreate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=True)),
) -> InitPermission:
    """Grant access to an initiative. Requires MANAGE on it. A live duplicate
    `(init, target_type, target_code, access_level)` → 409; a revoked one does
    not block re-granting."""
    if not session.get(Initiative, permission.init):
        raise HTTPException(
            status_code=400, detail=f"Initiative with id '{permission.init}' does not exist")
    _guard(permissions_service.require_init_manage, session, current, permission.init)
    _check_window(permission.valid_from, permission.valid_to)

    existing = session.exec(
        select(InitPermission).where(
            InitPermission.init == permission.init,
            InitPermission.target_type == permission.target_type,
            InitPermission.target_code == permission.target_code,
            InitPermission.access_level == permission.access_level,
            permissions_service.not_revoked_clause(),
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An active permission for this target + access level already exists")

    data = permission.model_dump(exclude_unset=True)
    if data.get("valid_from") is None:
        data.pop("valid_from", None)
    try:
        db = InitPermission(**data)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(
            "Initiative permission created: init=%s %s:%s → %s",
            db.init, db.target_type, db.target_code, db.access_level)
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error("Integrity error creating initiative permission: %s", e)
        raise HTTPException(status_code=409, detail="Initiative permission conflict")


@router.put("/{permission_id}", response_model=InitPermission)
def update(
    permission_id: int,
    update: InitPermissionUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=True)),
) -> InitPermission:
    """Partially update a live grant. Requires MANAGE on its initiative."""
    permission = session.get(InitPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Initiative permission not found")
    _guard(permissions_service.require_init_manage, session, current, permission.init)
    if permissions_service.is_revoked(permission):
        raise HTTPException(
            status_code=400, detail=f"Initiative permission '{permission_id}' is revoked")

    changes = update.model_dump(exclude_unset=True)
    _check_window(changes.get("valid_from", permission.valid_from),
                  changes.get("valid_to", permission.valid_to))
    for key, value in changes.items():
        setattr(permission, key, value)
    session.add(permission)
    session.commit()
    session.refresh(permission)
    return permission


@router.delete("/{permission_id}", response_model=InitPermission)
def revoke(
    permission_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=True)),
) -> InitPermission:
    """Revoke a grant by closing its validity window (`valid_to` = now); the
    row is retained. An already-scheduled future `valid_to` is overwritten so
    the revoke is immediate. Requires MANAGE on the initiative."""
    permission = session.get(InitPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Initiative permission not found")
    _guard(permissions_service.require_init_manage, session, current, permission.init)
    if permissions_service.is_revoked(permission):
        raise HTTPException(
            status_code=400, detail=f"Initiative permission '{permission_id}' is already revoked")

    permission.valid_to = datetime.utcnow()
    session.add(permission)
    session.commit()
    session.refresh(permission)
    logger.info("Initiative permission revoked: %s", permission_id)
    return permission
