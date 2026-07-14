import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import (
    AssetPermission, AssetPermissionCreate, AssetPermissionUpdate, Asset,
)
from ..internal import permissions_service
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/asset_permissions", tags=["asset_permissions"])

# Privilege option: permissions are a subordinate resource managed from the
# Assets screen, so they gate on (LIB, ASSETS) — the seeded option. An
# "ASSET_PERMISSIONS" option was never seeded and would 403 every non-superuser.


def _ensure_manage(session: Session, user: User, asset_id: int) -> None:
    """Per-asset write guard (HU-LI08): only MANAGE holders (or superusers) may
    grant/revoke permissions on an asset — otherwise a VIEW-only user could
    escalate by granting themselves MANAGE."""
    try:
        permissions_service.require_asset_manage(session, user, asset_id)
    except permissions_service.AssetAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/", response_model=List[AssetPermission])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetPermission]:
    """List all active asset permissions (paginated)."""
    return session.exec(
        select(AssetPermission)
        .where(AssetPermission.is_active == True)
        .offset(skip).limit(limit)
        .order_by(AssetPermission.asset, AssetPermission.id)
    ).all()


# Registered BEFORE the `/{permission_id}` route so GET /asset/5 matches here
# instead of parsing "asset" as an int permission_id.
@router.get("/asset/{asset_id}", response_model=List[AssetPermission])
def get_by_asset(
    asset_id: int, skip: int = 0, limit: int = 100,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetPermission]:
    """List active permissions for one asset."""
    return session.exec(
        select(AssetPermission)
        .where(AssetPermission.asset == asset_id, AssetPermission.is_active == True)
        .offset(skip).limit(limit)
        .order_by(AssetPermission.id)
    ).all()


@router.get("/{permission_id}", response_model=AssetPermission)
def get(
    permission_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> AssetPermission:
    """Get an asset permission by its surrogate id."""
    permission = session.get(AssetPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Asset permission not found")
    elif not permission.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Asset permission '{permission_id}' is inactive")
    return permission


@router.post("/", response_model=AssetPermission, status_code=201)
def create(
    permission: AssetPermissionCreate, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> AssetPermission:
    """
    Create a new asset permission. Requires MANAGE on the asset.

    - **asset**: Asset id (required, must exist)
    - **target_type** / **target_code** / **access_level**: required
    """
    # Validate the asset exists.
    if not session.get(Asset, permission.asset):
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{permission.asset}' does not exist")

    _ensure_manage(session, current, permission.asset)

    # Reject a duplicate ACTIVE grant for the same (asset, target_type, target_code,
    # access_level) so a re-add doesn't pile up rows.
    existing = session.exec(
        select(AssetPermission).where(
            AssetPermission.asset == permission.asset,
            AssetPermission.target_type == permission.target_type,
            AssetPermission.target_code == permission.target_code,
            AssetPermission.access_level == permission.access_level,
            AssetPermission.is_active == True,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An active permission for this target + access level already exists")

    try:
        db = AssetPermission.model_validate(permission)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(
            f"Asset permission created: asset={permission.asset} "
            f"{permission.target_type}:{permission.target_code} → {permission.access_level}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating asset permission: {e}")
        raise HTTPException(status_code=409, detail="Asset permission conflict")


@router.put("/{permission_id}", response_model=AssetPermission)
def update(
    permission_id: int,
    update: AssetPermissionUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True)),
) -> AssetPermission:
    """Update an existing asset permission (only provided fields). Requires
    MANAGE on the asset."""
    permission = session.get(AssetPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Asset permission not found")
    _ensure_manage(session, current, permission.asset)

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(permission, key, value)

    session.add(permission)
    session.commit()
    session.refresh(permission)
    logger.info(f"Asset permission updated: {permission_id}")
    return permission


@router.delete("/{permission_id}", response_model=AssetPermission, status_code=200)
def delete(
    permission_id: int, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> AssetPermission:
    """Logical delete: set is_active=False (the record is retained). Requires
    MANAGE on the asset."""
    permission = session.get(AssetPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Asset permission not found")
    _ensure_manage(session, current, permission.asset)
    if not permission.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Asset permission '{permission_id}' is already inactive")

    permission.is_active = False
    session.add(permission)
    session.commit()
    session.refresh(permission)
    logger.info(f"Asset permission deactivated (logical delete): {permission_id}")
    return permission
