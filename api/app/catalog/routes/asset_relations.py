import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import AssetRelation, AssetRelationCreate, AssetRelationUpdate, Asset
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/asset_relations", tags=["asset_relations"])


@router.post("/", response_model=AssetRelation, status_code=201)
def create_asset_relation(relation: AssetRelationCreate, session: Session = Depends(get_db_session)) -> AssetRelation:
    """
    Create a new asset relation.

    - **source**: Source asset code (required)
    - **target**: Target asset code (required)
    - **type**: Relation type (required)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the source asset exists
    source_asset = session.get(Asset, relation.source)
    if not source_asset:
        raise HTTPException(
            status_code=400,
            detail=f"Source asset with code '{relation.source}' does not exist"
        )

    # Validate that the target asset exists
    target_asset = session.get(Asset, relation.target)
    if not target_asset:
        raise HTTPException(
            status_code=400,
            detail=f"Target asset with code '{relation.target}' does not exist"
        )

    # Validate that it's not the same relation
    if relation.source == relation.target:
        raise HTTPException(
            status_code=400,
            detail="Source and target assets cannot be the same"
        )

    # Validate that the relation does not already exist
    existing_relation = session.exec(
        select(AssetRelation).where(
            AssetRelation.source == relation.source,
            AssetRelation.target == relation.target
        )
    ).first()
    if existing_relation:
        raise HTTPException(
            status_code=409,
            detail=f"Asset relation with source '{relation.source}' and target '{relation.target}' already exists"
        )

    try:
        db_relation = AssetRelation.model_validate(relation)
        session.add(db_relation)
        session.commit()
        session.refresh(db_relation)
        logger.info(
            f"Asset relation created: {relation.source} -> {relation.target}")
        return db_relation
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating asset relation {relation.source}/{relation.target}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Asset relation with source '{relation.source}' and target '{relation.target}' already exists"
        )


@router.get("/", response_model=List[AssetRelation])
def list_asset_relations(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[AssetRelation]:
    """
    List all asset relations with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    relations = session.exec(select(AssetRelation).offset(skip).limit(
        limit).order_by(AssetRelation.source, AssetRelation.target)).all()
    return relations


@router.get("/{source_code}/{target_code}", response_model=AssetRelation)
def get_asset_relation(source_code: str, target_code: str, session: Session = Depends(get_db_session)) -> AssetRelation:
    """
    Get an asset relation by its source and target.

    - **source_code**: Source asset code
    - **target_code**: Target asset code
    """
    relation = session.exec(
        select(AssetRelation).where(
            AssetRelation.source == source_code,
            AssetRelation.target == target_code
        )
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="Asset relation not found")
    return relation


@router.put("/{source_code}/{target_code}", response_model=AssetRelation)
def update_asset_relation(
    source_code: str, target_code: str, relation_update: AssetRelationUpdate, session: Session = Depends(get_db_session)
) -> AssetRelation:
    """
    Update an existing asset relation.

    - **source_code**: Source asset code
    - **target_code**: Target asset code
    - Only provided fields are updated
    """
    relation = session.exec(
        select(AssetRelation).where(
            AssetRelation.source == source_code,
            AssetRelation.target == target_code
        )
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="Asset relation not found")

    update_data = relation_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(relation, key, value)

    # Update timestamp
    relation.updated_at = datetime.utcnow()

    session.add(relation)
    session.commit()
    session.refresh(relation)
    logger.info(f"Asset relation updated: {source_code} -> {target_code}")
    return relation


@router.delete("/{source_code}/{target_code}", response_model=AssetRelation, status_code=200)
def delete_asset_relation(source_code: str, target_code: str, session: Session = Depends(get_db_session)) -> AssetRelation:
    """
    Delete an asset relation (logical delete).

    Performs a logical delete by setting is_active=False instead of removing the record.

    - **source_code**: Source asset code
    - **target_code**: Target asset code
    """
    relation = session.exec(
        select(AssetRelation).where(
            AssetRelation.source == source_code,
            AssetRelation.target == target_code
        )
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="Asset relation not found")

    # Check if already inactive
    if not relation.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Asset relation with source '{source_code}' and target '{target_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    relation.is_active = False
    relation.updated_at = datetime.utcnow()

    session.add(relation)
    session.commit()
    session.refresh(relation)
    logger.info(
        f"Asset relation deactivated (logical delete): {source_code} -> {target_code}")
    return relation
