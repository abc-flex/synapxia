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
    """List all asset permissions that have not been revoked (paginated)."""
    return session.exec(
        select(AssetPermission)
        .where(permissions_service.not_revoked_clause())
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
    """List the not-yet-revoked permissions of one asset. A future-dated grant
    (``valid_from`` ahead of now) is included — it is scheduled, not revoked,
    and must stay manageable until it takes effect."""
    return session.exec(
        select(AssetPermission)
        .where(
            AssetPermission.asset == asset_id,
            permissions_service.not_revoked_clause(),
        )
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
    elif permissions_service.is_revoked(permission):
        raise HTTPException(
            status_code=400,
            detail=f"Asset permission '{permission_id}' has been revoked")
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

    # Reject a duplicate un-revoked grant for the same (asset, target_type,
    # target_code, access_level) so a re-add doesn't pile up rows. A previously
    # revoked grant does NOT block re-granting the same access.
    existing = session.exec(
        select(AssetPermission).where(
            AssetPermission.asset == permission.asset,
            AssetPermission.target_type == permission.target_type,
            AssetPermission.target_code == permission.target_code,
            AssetPermission.access_level == permission.access_level,
            permissions_service.not_revoked_clause(),
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
    """Revoke the grant by closing its validity window (``valid_to`` = now).
    The record is retained. Requires MANAGE on the asset.

    A permission is never logically deleted: revoking it and letting it expire
    are the same state, so ``valid_to`` is the single mechanism for both. Any
    ``valid_to`` already set in the future is overwritten — an explicit revoke
    takes effect immediately, not on the originally scheduled date."""
    permission = session.get(AssetPermission, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Asset permission not found")
    _ensure_manage(session, current, permission.asset)
    if permissions_service.is_revoked(permission):
        raise HTTPException(
            status_code=400,
            detail=f"Asset permission '{permission_id}' is already revoked")

    permission.valid_to = datetime.utcnow()
    session.add(permission)
    session.commit()
    session.refresh(permission)
    logger.info(f"Asset permission revoked (valid_to closed): {permission_id}")
    return permission
