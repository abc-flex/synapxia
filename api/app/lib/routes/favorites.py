import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Favorite, FavoriteCreate, FavoriteUpdate, Asset
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import check_privilege

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("/", response_model=List[Favorite])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "FAVORITES", can_edit=False))
) -> List[Favorite]:
    """
    List all favorites with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    favorites = session.exec(select(Favorite).where(Favorite.is_active == True)
                             .offset(skip).limit(limit)
                             .order_by(Favorite.user_id, Favorite.asset)).all()
    return favorites


@router.get("/{user_id}/{asset_code}", response_model=Favorite)
def get(
    user_id: int, asset_code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "FAVORITES", can_edit=False))
) -> Favorite:
    """
    Get a favorite by its user and asset.

    - **user_id**: User ID
    - **asset_code**: Asset code
    """
    favorite = session.exec(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.asset == asset_code
        )
    ).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    elif not favorite.is_active:
        raise HTTPException(status_code=400, detail=f"Favorite with user_id '{user_id}' and asset '{asset_code}' is inactive")
    return favorite


@router.post("/", response_model=Favorite, status_code=201)
def create(
    favorite: FavoriteCreate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "FAVORITES", can_edit=True))
) -> Favorite:
    """
    Create a new favorite.

    - **user_id**: User ID (required)
    - **asset**: Asset code (required)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the asset exists
    asset = session.get(Asset, favorite.asset)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with code '{favorite.asset}' does not exist"
        )

    # Validate that the favorite does not already exist
    existing = session.exec(
        select(Favorite).where(
            Favorite.user_id == favorite.user_id,
            Favorite.asset == favorite.asset
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Favorite with user_id '{favorite.user_id}' and asset '{favorite.asset}' already exists"
        )

    try:
        db = Favorite.model_validate(favorite)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Favorite created: {favorite.user_id}/{favorite.asset}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating favorite {favorite.user_id}/{favorite.asset}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Favorite with user_id '{favorite.user_id}' and asset '{favorite.asset}' already exists"
        )


@router.put("/{user_id}/{asset_code}", response_model=Favorite)
def update(
    user_id: int, asset_code: str, favorite_update: FavoriteUpdate, session: Session = Depends(get_db_session)
) -> Favorite:
    """
    Update an existing favorite.

    - **user_id**: User ID
    - **asset_code**: Asset code
    - Only provided fields are updated
    """
    favorite = session.exec(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.asset == asset_code
        )
    ).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    update_data = favorite_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(favorite, key, value)

    # Update timestamp
    favorite.updated_at = datetime.utcnow()

    session.add(favorite)
    session.commit()
    session.refresh(favorite)
    logger.info(f"Favorite updated: {user_id}/{asset_code}")
    return favorite


@router.delete("/{user_id}/{asset_code}", response_model=Favorite, status_code=200)
def delete(
    user_id: int, asset_code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "FAVORITES", can_edit=True))
) -> Favorite:
    """
    Delete a favorite (logical delete).

    Performs a logical delete by setting is_active=False instead of removing the record.

    - **user_id**: User ID
    - **asset_code**: Asset code
    """
    favorite = session.exec(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.asset == asset_code
        )
    ).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    # Check if already inactive
    if not favorite.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Favorite with user_id '{user_id}' and asset '{asset_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    favorite.is_active = False
    favorite.updated_at = datetime.utcnow()

    session.add(favorite)
    session.commit()
    session.refresh(favorite)
    logger.info(
        f"Favorite deactivated (logical delete): {user_id}/{asset_code}")
    return favorite
