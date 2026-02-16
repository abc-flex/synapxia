import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import BusinessUnit, BusinessUnitCreate, BusinessUnitUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/business_units", tags=["business_units"])


@router.post("/", response_model=BusinessUnit, status_code=201)
def create_business_unit(business_unit: BusinessUnitCreate, session: Session = Depends(get_db_session)) -> BusinessUnit:
    """
    Create a new organizational business_unit.

    - **code**: Unique business_unit code (required)
    - **name**: BusinessUnit name (required)
    - **description**: Optional description
    - **type**: BusinessUnit type (optional)
    - **parent**: Parent business_unit code (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing_unit = session.get(BusinessUnit, business_unit.code)
    if existing_unit:
        raise HTTPException(
            status_code=409,
            detail=f"BusinessUnit with code '{business_unit.code}' already exists"
        )

    # Validate that the parent business_unit exists if provided
    if business_unit.parent:
        parent = session.get(BusinessUnit, business_unit.parent)
        if not parent:
            raise HTTPException(
                status_code=400,
                detail=f"Parent business unit with code '{business_unit.parent}' does not exist"
            )

    try:
        db_unit = BusinessUnit.model_validate(business_unit)
        session.add(db_unit)
        session.commit()
        session.refresh(db_unit)
        logger.info(f"Business unit created: {business_unit.code}")
        return db_unit
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating business_unit {business_unit.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Business unit with code '{business_unit.code}' already exists"
        )


@router.get("/", response_model=List[BusinessUnit])
def list_business_units(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[BusinessUnit]:
    """
    List all business_units with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    business_units = session.exec(select(BusinessUnit).offset(
        skip).limit(limit).order_by(BusinessUnit.name)).all()
    return business_units


@router.get("/{unit_code}", response_model=BusinessUnit)
def get_business_unit(unit_code: str, session: Session = Depends(get_db_session)) -> BusinessUnit:
    """
    Get a business unit by its code.

    - **unit_code**: Unique business unit code
    """
    business_unit = session.get(BusinessUnit, unit_code)
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")
    return business_unit


@router.put("/{unit_code}", response_model=BusinessUnit)
def update_business_unit(unit_code: str, unit_update: BusinessUnitUpdate, session: Session = Depends(get_db_session)) -> BusinessUnit:
    """
    Update an existing business_unit.

    - **unit_code**: Unique business_unit code to update
    - Only provided fields are updated
    """
    business_unit = session.get(BusinessUnit, unit_code)
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")

    # Validate that the parent business_unit exists if provided
    if unit_update.parent is not None:
        parent = session.get(BusinessUnit, unit_update.parent)
        if not parent:
            raise HTTPException(
                status_code=400,
                detail=f"Parent business_unit with code '{unit_update.parent}' does not exist"
            )

    update_data = unit_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(business_unit, key, value)

    # Update timestamp
    business_unit.updated_at = datetime.utcnow()

    session.add(business_unit)
    session.commit()
    session.refresh(business_unit)
    logger.info(f"Business unit updated: {unit_code}")
    return business_unit


@router.delete("/{unit_code}", response_model=BusinessUnit, status_code=200)
def delete_business_unit(unit_code: str, session: Session = Depends(get_db_session)) -> BusinessUnit:
    """
    Delete a business_unit (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **unit_code**: Unique business_unit code to delete
    """
    business_unit = session.get(BusinessUnit, unit_code)
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")

    # Check if already inactive
    if not business_unit.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Business unit with code '{unit_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    business_unit.is_active = False
    business_unit.updated_at = datetime.utcnow()

    session.add(business_unit)
    session.commit()
    session.refresh(business_unit)
    logger.info(f"Business unit deactivated (logical delete): {unit_code}")
    return business_unit
