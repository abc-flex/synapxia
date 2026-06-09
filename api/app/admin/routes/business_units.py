import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy.exc import IntegrityError

from ..internal.models import BusinessUnit, BusinessUnitCreate, BusinessUnitUpdate, User
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/business_units", tags=["business_units"])

#Model for business_unit select options
class BusinessUnitBasic(SQLModel):
    value: str
    label: str

@router.get("/select", response_model=List[BusinessUnitBasic])
def get_list(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "BUSINESS_UNITS", can_edit=False))
) -> List[BusinessUnitBasic]:
    """
    Returns a business units list optimized for selects with value (code) and label (name). 
    Only active business units.
    """
    statement = (
        select(
            BusinessUnit.code.label("value"), 
            BusinessUnit.name.label("label")
        )
        .where(BusinessUnit.is_active == True)
        .order_by(BusinessUnit.name)
    )
    return session.exec(statement).all()


@router.get("/", response_model=List[BusinessUnit])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "BUSINESS_UNITS", can_edit=False))
) -> List[BusinessUnit]:
    """
    List all business_units with pagination (*Only active business_units).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    business_units = session.exec(select(BusinessUnit).where(BusinessUnit.is_active == True)
                                  .offset(skip).limit(limit)
                                  .order_by(BusinessUnit.name)).all()
    return business_units


@router.get("/{code}", response_model=BusinessUnit)
def get(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "BUSINESS_UNITS", can_edit=False))
) -> BusinessUnit:
    """
    Get a business unit by its code.

    - **code**: Unique business unit code
    """
    business_unit = session.get(BusinessUnit, code)
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")
    elif not business_unit.is_active:
        raise HTTPException(status_code=400, detail=f"Business unit with code '{code}' is inactive")
    return business_unit


@router.post("/", response_model=BusinessUnit, status_code=201)
def create(
    business_unit: BusinessUnitCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "BUSINESS_UNITS", can_edit=True))
) -> BusinessUnit:
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


@router.put("/{code}", response_model=BusinessUnit)
def update(
    code: str, unit_update: BusinessUnitUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "BUSINESS_UNITS", can_edit=True))
) -> BusinessUnit:
    """
    Update an existing business_unit.

    - **code**: Unique business_unit code to update
    - Only provided fields are updated
    """
    business_unit = session.get(BusinessUnit, code)
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
    logger.info(f"Business unit updated: {code}")
    return business_unit


@router.delete("/{code}", response_model=BusinessUnit, status_code=200)
def delete(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "BUSINESS_UNITS", can_edit=True))
) -> BusinessUnit:
    """
    Delete a business_unit (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique business_unit code to delete
    """
    business_unit = session.get(BusinessUnit, code)
    if not business_unit:
        raise HTTPException(status_code=404, detail="Business unit not found")

    # Check if already inactive
    if not business_unit.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Business unit with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    business_unit.is_active = False
    business_unit.updated_at = datetime.utcnow()

    session.add(business_unit)
    session.commit()
    session.refresh(business_unit)
    logger.info(f"Business unit deactivated (logical delete): {code}")
    return business_unit
