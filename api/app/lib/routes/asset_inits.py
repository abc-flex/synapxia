import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import AssetInit, AssetInitCreate, AssetInitUpdate, Asset
from ..internal import permissions_service
from ..internal.dependencies import get_db_session
from ...inits.internal.models import Initiative
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/asset_inits", tags=["asset_inits"])


def _ensure_manage(session: Session, user: User, asset_id: int) -> None:
    """Per-asset write guard (mirrors asset_relations): MANAGE grant or
    superuser required. Managed FROM the asset's detail tab, so writes guard
    on the asset only (the initiative need only exist)."""
    try:
        permissions_service.require_asset_manage(session, user, asset_id)
    except permissions_service.AssetAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/", response_model=List[AssetInit])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetInit]:
    """
    List all asset-initiative relations with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    relations = session.exec(
        select(AssetInit).where(AssetInit.is_active == True)
        .offset(skip).limit(limit)
        .order_by(AssetInit.asset, AssetInit.init)
    ).all()
    return relations


# Registered BEFORE the composite /{asset_id}/{init_id} route so that
# GET /asset/5 matches here instead of 422-ing on the composite parser.
@router.get("/asset/{asset_id}", response_model=List[AssetInit])
def get_by_asset(
    asset_id: int, skip: int = 0, limit: int = 100,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetInit]:
    """
    List active initiative relations for the given asset.

    - **asset_id**: Asset id
    - **skip** / **limit**: pagination
    """
    relations = session.exec(
        select(AssetInit)
        .where(AssetInit.asset == asset_id, AssetInit.is_active == True)
        .offset(skip).limit(limit)
        .order_by(AssetInit.init)
    ).all()
    return relations


@router.get("/{asset_id}/{init_id}", response_model=AssetInit)
def get(
    asset_id: int, init_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> AssetInit:
    """
    Get an asset-initiative relation by asset and initiative id.

    - **asset_id**: Asset id
    - **init_id**: Initiative id
    """
    relation = session.exec(
        select(AssetInit).where(
            AssetInit.asset == asset_id,
            AssetInit.init == init_id
        )
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="Asset-initiative relation not found")
    elif not relation.is_active:
        raise HTTPException(status_code=400, detail=f"Asset-initiative relation with asset '{asset_id}' and init '{init_id}' is inactive")
    return relation


@router.post("/", response_model=AssetInit, status_code=201)
def create(
    relation: AssetInitCreate, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> AssetInit:
    """
    Create a new asset-initiative relation.

    - **asset**: Asset id (required)
    - **init**: Initiative id (required)
    - **type**: Relation type (required)
    - **rationale**: Optional note on why the asset and initiative are related
    - **is_active**: Active/inactive status (default: True)
    """
    asset = session.get(Asset, relation.asset)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{relation.asset}' does not exist"
        )

    initiative = session.get(Initiative, relation.init)
    if not initiative:
        raise HTTPException(
            status_code=400,
            detail=f"Initiative with id '{relation.init}' does not exist"
        )

    _ensure_manage(session, current, relation.asset)

    existing = session.exec(
        select(AssetInit).where(
            AssetInit.asset == relation.asset,
            AssetInit.init == relation.init
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Asset-initiative relation with asset '{relation.asset}' and init '{relation.init}' already exists"
        )

    try:
        db = AssetInit.model_validate(relation)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(
            f"Asset-initiative relation created: {relation.asset} -> {relation.init}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating asset-initiative relation {relation.asset}/{relation.init}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Asset-initiative relation with asset '{relation.asset}' and init '{relation.init}' already exists"
        )


@router.put("/{asset_id}/{init_id}", response_model=AssetInit)
def update(
    asset_id: int,
    init_id: int,
    update: AssetInitUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True)),
) -> AssetInit:
    """
    Update an existing asset-initiative relation. Requires MANAGE on the asset.

    - **asset_id**: Asset id
    - **init_id**: Initiative id
    - Only provided fields are updated
    """
    relation = session.exec(
        select(AssetInit).where(
            AssetInit.asset == asset_id,
            AssetInit.init == init_id
        )
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="Asset-initiative relation not found")
    _ensure_manage(session, current, asset_id)

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(relation, key, value)

    relation.updated_at = datetime.utcnow()

    session.add(relation)
    session.commit()
    session.refresh(relation)
    logger.info(f"Asset-initiative relation updated: {asset_id} -> {init_id}")
    return relation


@router.delete("/{asset_id}/{init_id}", response_model=AssetInit, status_code=200)
def delete(
    asset_id: int, init_id: int, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> AssetInit:
    """
    Delete an asset-initiative relation (logical delete). Requires MANAGE on the asset.

    Performs a logical delete by setting is_active=False instead of removing the record.

    - **asset_id**: Asset id
    - **init_id**: Initiative id
    """
    relation = session.exec(
        select(AssetInit).where(
            AssetInit.asset == asset_id,
            AssetInit.init == init_id
        )
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="Asset-initiative relation not found")
    _ensure_manage(session, current, asset_id)

    if not relation.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Asset-initiative relation with asset '{asset_id}' and init '{init_id}' is already inactive"
        )

    relation.is_active = False
    relation.updated_at = datetime.utcnow()

    session.add(relation)
    session.commit()
    session.refresh(relation)
    logger.info(
        f"Asset-initiative relation deactivated (logical delete): {asset_id} -> {init_id}")
    return relation
