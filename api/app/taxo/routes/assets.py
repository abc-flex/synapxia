import logging
from typing import List
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Asset, AssetCreate, AssetUpdate, Category
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/", response_model=List[Asset])
def get_all(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Asset]:
    """
    List all assets with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    assets = session.exec(select(Asset).where(Asset.is_active == True)
                          .offset(skip).limit(limit)
                          .order_by(Asset.name)).all()
    return assets


@router.get("/{code}", response_model=Asset)
def get(code: str, session: Session = Depends(get_db_session)) -> Asset:
    """
    Get an asset by its code.

    - **code**: Unique asset code
    """
    asset = session.get(Asset, code)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    elif not asset.is_active:
        raise HTTPException(status_code=400, detail=f"Asset with code '{code}' is inactive")
    return asset


@router.post("/", response_model=Asset, status_code=201)
def create(asset: AssetCreate, session: Session = Depends(get_db_session)) -> Asset:
    """
    Create a new asset.

    - **name**: Asset name (required)
    - **type**: Asset type (required)
    - **status**: Asset status (required)
    - **visibility**: Asset visibility (required)
    - **description**: Optional description
    - **category**: Category code (optional)
    - **reference**: Asset reference (optional)
    - **tags**: Asset tags in JSON format (optional)
    - **details**: Asset details in JSON format (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code doesn't exist
    existing = session.get(Asset, asset.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Asset with code '{asset.code}' already exists"
        )

    # Validate that the category exists if provided
    if asset.category:
        category = session.get(Category, asset.category)
        if not category:
            raise HTTPException(
                status_code=400,
                detail=f"Category with code '{asset.category}' does not exist"
            )

    try:
        # Convert tags and details to JSON string if they are dict
        data = asset.model_dump()
        if data.get('tags') and isinstance(data['tags'], dict):
            data['tags'] = json.dumps(data['tags'])
        if data.get('details') and isinstance(data['details'], dict):
            data['details'] = json.dumps(data['details'])

        db = Asset.model_validate(data)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Asset created: {asset.code}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating asset {asset.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Asset with code '{asset.code}' already exists"
        )


@router.put("/{code}", response_model=Asset)
def update(code: str, update: AssetUpdate, session: Session = Depends(get_db_session)) -> Asset:
    """
    Update an existing asset.

    - **code**: Unique asset code to update
    - Only provided fields are updated
    """
    asset = session.get(Asset, code)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Validate that the category exists if provided
    if update.category is not None:
        category = session.get(Category, update.category)
        if not category:
            raise HTTPException(
                status_code=400,
                detail=f"Category with code '{update.category}' does not exist"
            )

    update_data = update.model_dump(exclude_unset=True)
    # Convert tags and details to JSON string if they are dict
    if 'tags' in update_data and isinstance(update_data['tags'], dict):
        update_data['tags'] = json.dumps(update_data['tags'])
    if 'details' in update_data and isinstance(update_data['details'], dict):
        update_data['details'] = json.dumps(update_data['details'])

    for key, value in update_data.items():
        setattr(asset, key, value)

    # Update timestamp
    asset.updated_at = datetime.utcnow()

    session.add(asset)
    session.commit()
    session.refresh(asset)
    logger.info(f"Asset updated: {code}")
    return asset


@router.delete("/{code}", response_model=Asset, status_code=200)
def delete(code: str, session: Session = Depends(get_db_session)) -> Asset:
    """
    Delete an asset (logical delete).

    Performs a logical delete by setting is_active=False instead of removing the record.

    - **code**: Unique asset code to delete
    """
    asset = session.get(Asset, code)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Check if already inactive
    if not asset.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    asset.is_active = False
    asset.updated_at = datetime.utcnow()

    session.add(asset)
    session.commit()
    session.refresh(asset)
    logger.info(f"Asset deactivated (logical delete): {code}")
    return asset
