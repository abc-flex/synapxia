import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Dimension, DimensionCreate, DimensionUpdate
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import check_privilege

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dimensions", tags=["dimensions"])


@router.get("/", response_model=List[Dimension])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("COLLAB", "DIMENSIONS", can_edit=False))
) -> List[Dimension]:
    """
    List all dimensions with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    dimensions = session.exec(select(Dimension).where(Dimension.is_active == True)
                              .offset(skip).limit(limit)
                              .order_by(Dimension.name)).all()
    return dimensions


@router.get("/{code}", response_model=Dimension)
def get(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("COLLAB", "DIMENSIONS", can_edit=False))
) -> Dimension:
    """
    Get a dimension by its code.

    - **code**: Unique dimension code
    """
    dimension = session.get(Dimension, code)
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    elif not dimension.is_active:
        raise HTTPException(status_code=400, detail=f"Dimension with code '{code}' is inactive")
    return dimension


@router.post("/", response_model=Dimension, status_code=201)
def create(
    dimension: DimensionCreate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("COLLAB", "DIMENSIONS", can_edit=True))
) -> Dimension:
    """
    Create a new dimension.

    - **code**: Unique dimension code (required)
    - **name**: Dimension name (required)
    - **description**: Optional description
    - **scale**: Scale code (list) (optional)
    - **unit**: Unit of measurement (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing = session.get(Dimension, dimension.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Dimension with code '{dimension.code}' already exists"
        )

    try:
        db = Dimension.model_validate(dimension)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Dimension created: {dimension.code}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating dimension {dimension.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Dimension with code '{dimension.code}' already exists"
        )


@router.put("/{code}", response_model=Dimension)
def update(
    code: str, update: DimensionUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("COLLAB", "DIMENSIONS", can_edit=True))
) -> Dimension:
    """
    Update an existing dimension.

    - **code**: Unique dimension code to update
    - Only provided fields are updated
    """
    dimension = session.get(Dimension, code)
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dimension, key, value)

    # Update timestamp
    dimension.updated_at = datetime.utcnow()

    session.add(dimension)
    session.commit()
    session.refresh(dimension)
    logger.info(f"Dimension updated: {code}")
    return dimension


@router.delete("/{code}", response_model=Dimension, status_code=200)
def delete(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("COLLAB", "DIMENSIONS", can_edit=True))
) -> Dimension:
    """
    Delete a dimension (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique dimension code to delete
    """
    dimension = session.get(Dimension, code)
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")

    # Check if already inactive
    if not dimension.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Dimension with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    dimension.is_active = False
    dimension.updated_at = datetime.utcnow()

    session.add(dimension)
    session.commit()
    session.refresh(dimension)
    logger.info(f"Dimension deactivated (logical delete): {code}")
    return dimension
