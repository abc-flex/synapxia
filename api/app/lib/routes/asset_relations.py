import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import AssetRelation, AssetRelationCreate, AssetRelationUpdate, Asset
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/asset_relations", tags=["asset_relations"])

# NOTE on privilege option: relations are subordinate resources managed from
# the Assets screen, so they gate on (LIB, ASSETS) — the option that's
# actually seeded in db/sql/12-admin-insert.sql. The previous
# "ASSET_RELATIONS" option was never seeded, which 403'd every non-superuser.


@router.get("/", response_model=List[AssetRelation])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetRelation]:
    """
    List all asset relations with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    relations = session.exec(select(AssetRelation).where(AssetRelation.is_active == True)
                             .offset(skip).limit(limit)
                             .order_by(AssetRelation.source, AssetRelation.target)).all()
    return relations


# Registered BEFORE the composite /{source_id}/{target_id} route so that
# GET /source/5 matches here instead of 422-ing on the composite parser.
@router.get("/source/{asset_id}", response_model=List[AssetRelation])
def get_by_source(
    asset_id: int, skip: int = 0, limit: int = 100,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetRelation]:
    """
    List active relations where the given asset is the source.

    - **asset_id**: Source asset id
    - **skip** / **limit**: pagination
    """
    relations = session.exec(
        select(AssetRelation)
        .where(AssetRelation.source == asset_id, AssetRelation.is_active == True)
        .offset(skip).limit(limit)
        .order_by(AssetRelation.target)
    ).all()
    return relations


@router.get("/{source_id}/{target_id}", response_model=AssetRelation)
def get(
    source_id: int, target_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> AssetRelation:
    """
    Get an asset relation by its source and target asset ids.

    - **source_id**: Source asset id
    - **target_id**: Target asset id
    """
    relation = session.exec(
        select(AssetRelation).where(
            AssetRelation.source == source_id,
            AssetRelation.target == target_id
        )
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="Asset relation not found")
    elif not relation.is_active:
        raise HTTPException(status_code=400, detail=f"Asset relation with source '{source_id}' and target '{target_id}' is inactive")
    return relation


@router.post("/", response_model=AssetRelation, status_code=201)
def create(
    relation: AssetRelationCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> AssetRelation:
    """
    Create a new asset relation.

    - **source**: Source asset id (required)
    - **target**: Target asset id (required)
    - **type**: Relation type (required)
    - **rationale**: Optional note on why the assets are related
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the source asset exists
    source_asset = session.get(Asset, relation.source)
    if not source_asset:
        raise HTTPException(
            status_code=400,
            detail=f"Source asset with id '{relation.source}' does not exist"
        )

    # Validate that the target asset exists
    target_asset = session.get(Asset, relation.target)
    if not target_asset:
        raise HTTPException(
            status_code=400,
            detail=f"Target asset with id '{relation.target}' does not exist"
        )

    # Validate that it's not the same relation
    if relation.source == relation.target:
        raise HTTPException(
            status_code=400,
            detail="Source and target assets cannot be the same"
        )

    # Validate that the relation does not already exist
    existing = session.exec(
        select(AssetRelation).where(
            AssetRelation.source == relation.source,
            AssetRelation.target == relation.target
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Asset relation with source '{relation.source}' and target '{relation.target}' already exists"
        )

    try:
        db = AssetRelation.model_validate(relation)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(
            f"Asset relation created: {relation.source} -> {relation.target}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating asset relation {relation.source}/{relation.target}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Asset relation with source '{relation.source}' and target '{relation.target}' already exists"
        )


@router.put("/{source_id}/{target_id}", response_model=AssetRelation)
def update(
    source_id: int,
    target_id: int,
    update: AssetRelationUpdate,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True)),
) -> AssetRelation:
    """
    Update an existing asset relation.

    - **source_id**: Source asset id
    - **target_id**: Target asset id
    - Only provided fields are updated
    """
    relation = session.exec(
        select(AssetRelation).where(
            AssetRelation.source == source_id,
            AssetRelation.target == target_id
        )
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="Asset relation not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(relation, key, value)

    # Update timestamp
    relation.updated_at = datetime.utcnow()

    session.add(relation)
    session.commit()
    session.refresh(relation)
    logger.info(f"Asset relation updated: {source_id} -> {target_id}")
    return relation


@router.delete("/{source_id}/{target_id}", response_model=AssetRelation, status_code=200)
def delete(
    source_id: int, target_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> AssetRelation:
    """
    Delete an asset relation (logical delete).

    Performs a logical delete by setting is_active=False instead of removing the record.

    - **source_id**: Source asset id
    - **target_id**: Target asset id
    """
    relation = session.exec(
        select(AssetRelation).where(
            AssetRelation.source == source_id,
            AssetRelation.target == target_id
        )
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="Asset relation not found")

    # Check if already inactive
    if not relation.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Asset relation with source '{source_id}' and target '{target_id}' is already inactive"
        )

    # Logical delete: update is_active to False
    relation.is_active = False
    relation.updated_at = datetime.utcnow()

    session.add(relation)
    session.commit()
    session.refresh(relation)
    logger.info(
        f"Asset relation deactivated (logical delete): {source_id} -> {target_id}")
    return relation
