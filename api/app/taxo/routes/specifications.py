import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Specification, SpecificationCreate, SpecificationUpdate, Category, Feature
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/specifications", tags=["specifications"])


@router.get("/", response_model=List[Specification])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "SPECIFICATIONS", can_edit=False))
) -> List[Specification]:
    """
    List all specifications with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    specifications = session.exec(select(Specification).where(Specification.is_active == True)
                                  .offset(skip).limit(limit)
                                  .order_by(Specification.category, Specification.sort_order,
                                            Specification.feature)).all()
    return specifications


@router.get("/category/{category_code}", response_model=List[Specification])
def get_by_category(
    category_code: str,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "SPECIFICATIONS", can_edit=False)),
) -> List[Specification]:
    """
    List specifications belonging to a category — used by the Propose / Modify /
    asset-detail forms to know which feature inputs to render, in the configured
    display order (``sort_order``, then feature code as a stable tiebreaker).
    """
    return session.exec(
        select(Specification)
        .where(
            Specification.category == category_code,
            Specification.is_active == True,
        )
        .order_by(Specification.sort_order, Specification.feature)
        .offset(skip)
        .limit(limit)
    ).all()


@router.get("/{category_code}/{feature_code}", response_model=Specification)
def get(
    category_code: str, feature_code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "SPECIFICATIONS", can_edit=False))
) -> Specification:
    """
    Get a specification by its category and feature.

    - **category_code**: Category code
    - **feature_code**: Feature code
    """
    specification = session.exec(
        select(Specification).where(
            Specification.category == category_code,
            Specification.feature == feature_code
        )
    ).first()
    if not specification:
        raise HTTPException(status_code=404, detail="Specification not found")
    elif not specification.is_active:
        raise HTTPException(status_code=400, detail=f"Specification with category '{category_code}' and feature '{feature_code}' is inactive")
    return specification


@router.post("/", response_model=Specification, status_code=201)
def create(
    specification: SpecificationCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "SPECIFICATIONS", can_edit=True))
) -> Specification:
    """
    Create a new specification.

    - **category**: Category code (required)
    - **feature**: Feature code (required)
    - **default_value**: Default value (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the category exists
    category = session.get(Category, specification.category)
    if not category:
        raise HTTPException(
            status_code=400,
            detail=f"Category with code '{specification.category}' does not exist"
        )

    # Validate that the feature exists
    feature = session.get(Feature, specification.feature)
    if not feature:
        raise HTTPException(
            status_code=400,
            detail=f"Feature with code '{specification.feature}' does not exist"
        )

    # Validate that the specification doesn't already exist
    existing_spec = session.exec(
        select(Specification).where(
            Specification.category == specification.category,
            Specification.feature == specification.feature
        )
    ).first()
    if existing_spec:
        raise HTTPException(
            status_code=409,
            detail=f"Specification with category '{specification.category}' and feature '{specification.feature}' already exists"
        )

    try:
        db_spec = Specification.model_validate(specification)
        session.add(db_spec)
        session.commit()
        session.refresh(db_spec)
        logger.info(
            f"Specification created: {specification.category}/{specification.feature}")
        return db_spec
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating specification {specification.category}/{specification.feature}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Specification with category '{specification.category}' and feature '{specification.feature}' already exists"
        )


@router.put("/{category_code}/{feature_code}", response_model=Specification)
def update(
    category_code: str,
    feature_code: str,
    specification_update: SpecificationUpdate,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "SPECIFICATIONS", can_edit=True)),
) -> Specification:
    """
    Update an existing specification.

    - **category_code**: Category code
    - **feature_code**: Feature code
    - Only provided fields are updated
    """
    specification = session.exec(
        select(Specification).where(
            Specification.category == category_code,
            Specification.feature == feature_code
        )
    ).first()
    if not specification:
        raise HTTPException(
            status_code=404, detail="Specification not found")

    update_data = specification_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(specification, key, value)

    # Update timestamp
    specification.updated_at = datetime.utcnow()

    session.add(specification)
    session.commit()
    session.refresh(specification)
    logger.info(
        f"Specification updated: {category_code}/{feature_code}")
    return specification


@router.delete("/{category_code}/{feature_code}", response_model=Specification, status_code=200)
def delete(
    category_code: str, feature_code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "SPECIFICATIONS", can_edit=True))
) -> Specification:
    """
    Delete a specification (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **category_code**: Category code
    - **feature_code**: Feature code
    """
    specification = session.exec(
        select(Specification).where(
            Specification.category == category_code,
            Specification.feature == feature_code
        )
    ).first()
    if not specification:
        raise HTTPException(
            status_code=404, detail="Specification not found")

    # Check if already inactive
    if not specification.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Specification with category '{category_code}' and feature '{feature_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    specification.is_active = False
    specification.updated_at = datetime.utcnow()

    session.add(specification)
    session.commit()
    session.refresh(specification)
    logger.info(
        f"Specification deactivated (logical delete): {category_code}/{feature_code}")
    return specification
