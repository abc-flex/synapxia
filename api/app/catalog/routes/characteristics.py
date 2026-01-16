import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Characteristic, CharacteristicCreate, CharacteristicUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/characteristics", tags=["characteristics"])


@router.post("/", response_model=Characteristic, status_code=201)
def create_characteristic(characteristic: CharacteristicCreate, session: Session = Depends(get_db_session)) -> Characteristic:
    """
    Create a new characteristic.

    - **code**: Unique characteristic code (required)
    - **name**: Characteristic name (required)
    - **type**: Characteristic type (required)
    - **status**: Characteristic status (required)
    - **description**: Optional description
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing_characteristic = session.get(Characteristic, characteristic.code)
    if existing_characteristic:
        raise HTTPException(
            status_code=409,
            detail=f"Characteristic with code '{characteristic.code}' already exists"
        )

    try:
        db_characteristic = Characteristic.model_validate(characteristic)
        session.add(db_characteristic)
        session.commit()
        session.refresh(db_characteristic)
        logger.info(f"Characteristic created: {characteristic.code}")
        return db_characteristic
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating characteristic {characteristic.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Characteristic with code '{characteristic.code}' already exists"
        )


@router.get("/", response_model=List[Characteristic])
def list_characteristics(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Characteristic]:
    """
    List all characteristics with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    characteristics = session.exec(select(Characteristic).offset(
        skip).limit(limit).order_by(Characteristic.name)).all()
    return characteristics


@router.get("/{characteristic_code}", response_model=Characteristic)
def get_characteristic(characteristic_code: str, session: Session = Depends(get_db_session)) -> Characteristic:
    """
    Get a characteristic by its code.

    - **characteristic_code**: Unique characteristic code
    """
    characteristic = session.get(Characteristic, characteristic_code)
    if not characteristic:
        raise HTTPException(status_code=404, detail="Characteristic not found")
    return characteristic


@router.put("/{characteristic_code}", response_model=Characteristic)
def update_characteristic(characteristic_code: str, characteristic_update: CharacteristicUpdate, session: Session = Depends(get_db_session)) -> Characteristic:
    """
    Update an existing characteristic.

    - **characteristic_code**: Unique characteristic code to update
    - Only provided fields are updated
    """
    characteristic = session.get(Characteristic, characteristic_code)
    if not characteristic:
        raise HTTPException(status_code=404, detail="Characteristic not found")

    update_data = characteristic_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(characteristic, key, value)

    # Update timestamp
    characteristic.updated_at = datetime.utcnow()

    session.add(characteristic)
    session.commit()
    session.refresh(characteristic)
    logger.info(f"Characteristic updated: {characteristic_code}")
    return characteristic


@router.delete("/{characteristic_code}", response_model=Characteristic, status_code=200)
def delete_characteristic(characteristic_code: str, session: Session = Depends(get_db_session)) -> Characteristic:
    """
    Delete a characteristic (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **characteristic_code**: Unique characteristic code to delete
    """
    characteristic = session.get(Characteristic, characteristic_code)
    if not characteristic:
        raise HTTPException(status_code=404, detail="Characteristic not found")

    # Check if already inactive
    if not characteristic.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Characteristic with code '{characteristic_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    characteristic.is_active = False
    characteristic.updated_at = datetime.utcnow()

    session.add(characteristic)
    session.commit()
    session.refresh(characteristic)
    logger.info(
        f"Characteristic deactivated (logical delete): {characteristic_code}")
    return characteristic
