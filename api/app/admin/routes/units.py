import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Unit, UnitCreate, UnitUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/units", tags=["units"])


@router.post("/", response_model=Unit, status_code=201)
def create_unit(unit: UnitCreate, session: Session = Depends(get_db_session)) -> Unit:
    """
    Create a new organizational unit.

    - **code**: Unique unit code (required)
    - **name**: Unit name (required)
    - **description**: Optional description
    - **type**: Unit type (optional)
    - **parent**: Parent unit code (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing_unit = session.get(Unit, unit.code)
    if existing_unit:
        raise HTTPException(
            status_code=409,
            detail=f"Unit with code '{unit.code}' already exists"
        )

    # Validate that the parent unit exists if provided
    if unit.parent_unit:
        parent_unit = session.get(Unit, unit.parent_unit)
        if not parent_unit:
            raise HTTPException(
                status_code=400,
                detail=f"Parent unit with code '{unit.parent_unit}' does not exist"
            )

    try:
        db_unit = Unit.model_validate(unit)
        session.add(db_unit)
        session.commit()
        session.refresh(db_unit)
        logger.info(f"Unit created: {unit.code}")
        return db_unit
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating unit {unit.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Unit with code '{unit.code}' already exists"
        )


@router.get("/", response_model=List[Unit])
def list_units(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Unit]:
    """
    List all units with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    units = session.exec(select(Unit).offset(
        skip).limit(limit).order_by(Unit.name)).all()
    return units


@router.get("/{unit_code}", response_model=Unit)
def get_unit(unit_code: str, session: Session = Depends(get_db_session)) -> Unit:
    """
    Get a unit by its code.

    - **unit_code**: Unique unit code
    """
    unit = session.get(Unit, unit_code)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.put("/{unit_code}", response_model=Unit)
def update_unit(unit_code: str, unit_update: UnitUpdate, session: Session = Depends(get_db_session)) -> Unit:
    """
    Update an existing unit.

    - **unit_code**: Unique unit code to update
    - Only provided fields are updated
    """
    unit = session.get(Unit, unit_code)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Validate that the parent unit exists if provided
    if unit_update.parent_unit is not None:
        parent_unit = session.get(Unit, unit_update.parent_unit)
        if not parent_unit:
            raise HTTPException(
                status_code=400,
                detail=f"Parent unit with code '{unit_update.parent_unit}' does not exist"
            )

    update_data = unit_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(unit, key, value)

    # Update timestamp
    unit.updated_at = datetime.utcnow()

    session.add(unit)
    session.commit()
    session.refresh(unit)
    logger.info(f"Unit updated: {unit_code}")
    return unit


@router.delete("/{unit_code}", response_model=Unit, status_code=200)
def delete_unit(unit_code: str, session: Session = Depends(get_db_session)) -> Unit:
    """
    Delete a unit (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **unit_code**: Unique unit code to delete
    """
    unit = session.get(Unit, unit_code)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Check if already inactive
    if not unit.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Unit with code '{unit_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    unit.is_active = False
    unit.updated_at = datetime.utcnow()

    session.add(unit)
    session.commit()
    session.refresh(unit)
    logger.info(f"Unit deactivated (logical delete): {unit_code}")
    return unit
