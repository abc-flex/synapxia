import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Asset, AssetCreate, AssetUpdate
from ...taxo.internal.models import Category
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import check_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("/", response_model=List[Asset])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "ASSETS", can_edit=False))
) -> List[Asset]:
    """
    List all assets with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    assets = session.exec(select(Asset).where(Asset.is_active == True)
                          .offset(skip).limit(limit)
                          .order_by(Asset.name)).all()
    return assets


@router.get("/category/{category_code}", response_model=List[Asset])
def get_by_category(
    category_code: str,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db_session)
) -> List[Asset]:
    """
    Obtener todos los assets de una categoría específica.

    - **category_code**: Código de la categoría para filtrar
    """
    # Validar primero si la categoría existe (opcional, pero recomendado por integridad)
    category_exists = session.get(Category, category_code)
    if not category_exists:
        raise HTTPException(
            status_code=404, 
            detail=f"Category with code '{category_code}' does not exist"
        )
    items = session.exec(
        select(Asset)
        .where(Asset.category == category_code)
        .offset(skip)
        .limit(limit)
        .order_by(Asset.name)
    ).all()
    return items


@router.get("/{asset_id}", response_model=Asset)
def get(
    asset_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "ASSETS", can_edit=False))
) -> Asset:
    """
    Get an asset by its id.

    - **asset_id**: Unique asset id
    """
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    elif not asset.is_active:
        raise HTTPException(status_code=400, detail=f"Asset with id '{asset_id}' is inactive")
    return asset


@router.post("/", response_model=Asset, status_code=201)
def create(
    asset: AssetCreate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "ASSETS", can_edit=True))
) -> Asset:
    """
    Create a new asset.

    - **name**: Asset name (required)
    - **status**: Asset status (required)
    - **description**: Optional description
    - **category**: Category code (optional)
    - **reference**: Asset reference (optional)
    - **tags**: Asset tags in JSON format (optional)
    - **detail**: Asset detail (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the category exists if provided
    if asset.category:
        category = session.get(Category, asset.category)
        if not category:
            raise HTTPException(
                status_code=400,
                detail=f"Category with code '{asset.category}' does not exist"
            )

    try:
        db = Asset.model_validate(asset)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Asset created: {db.id}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating asset {asset.name}: {e}")
        raise HTTPException(
            status_code=409,
            detail="Asset could not be created due to a constraint violation"
        )


@router.put("/{asset_id}", response_model=Asset)
def update(
    asset_id: int, update: AssetUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "ASSETS", can_edit=True))
) -> Asset:
    """
    Update an existing asset.

    - **asset_id**: Unique asset id to update
    - Only provided fields are updated
    """
    asset = session.get(Asset, asset_id)
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
    for key, value in update_data.items():
        setattr(asset, key, value)

    # Update timestamp
    asset.updated_at = datetime.utcnow()

    session.add(asset)
    session.commit()
    session.refresh(asset)
    logger.info(f"Asset updated: {asset_id}")
    return asset


@router.delete("/{asset_id}", response_model=Asset, status_code=200)
def delete(
    asset_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "ASSETS", can_edit=True))
) -> Asset:
    """
    Delete an asset (logical delete).

    Performs a logical delete by setting is_active=False instead of removing the record.

    - **asset_id**: Unique asset id to delete
    """
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Check if already inactive
    if not asset.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' is already inactive"
        )

    # Logical delete: update is_active to False
    asset.is_active = False
    asset.updated_at = datetime.utcnow()

    session.add(asset)
    session.commit()
    session.refresh(asset)
    logger.info(f"Asset deactivated (logical delete): {asset_id}")
    return asset
