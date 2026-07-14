import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy.exc import IntegrityError

from ..internal.models import Feature, FeatureCreate, FeatureUpdate
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/features", tags=["features"])

#Model for module select options
class FeatureBasic(SQLModel):
    value: str
    label: str

@router.get("/select", response_model=List[FeatureBasic])
def get_list(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "FEATURES", can_edit=False))
) -> List[FeatureBasic]:
    """
    Returns a features list optimized for selects with value (code) and label (name). 
    Only active features.
    """
    statement = (
        select(
            Feature.code.label("value"), 
            Feature.name.label("label")
        )
        .where(Feature.is_active == True)
        .order_by(Feature.name)
    )
    return session.exec(statement).all()


@router.get("/", response_model=List[Feature])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "FEATURES", can_edit=False))
) -> List[Feature]:
    """
    List all features with pagination (*Only active features).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    features = session.exec(select(Feature).where(Feature.is_active == True)
                            .offset(skip).limit(limit)
                            .order_by(Feature.name)).all()
    return features


@router.get("/{code}", response_model=Feature)
def get(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "FEATURES", can_edit=False))
) -> Feature:
    """
    Get a feature by its code.

    - **code**: Unique feature code
    """
    feature = session.get(Feature, code)
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    elif not feature.is_active:
        raise HTTPException(status_code=400, detail=f"Feature with code '{code}' is inactive")
    return feature


@router.post("/", response_model=Feature, status_code=201)
def create(
    feature: FeatureCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "FEATURES", can_edit=True))
) -> Feature:
    """
    Create a new feature.

    - **code**: Unique feature code (required)
    - **name**: Feature name (required)
    - **type**: Feature type (required)
    - **description**: Optional description
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing = session.get(Feature, feature.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Feature with code '{feature.code}' already exists"
        )

    # If type is empty, "null" or "none", convert to None
    if feature.type is not None and feature.type in ["", "null", "none"]: 
        feature.type = None

    try:
        db = Feature.model_validate(feature)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Feature created: {feature.code}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating feature {feature.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Feature with code '{feature.code}' already exists"
        )


@router.put("/{code}", response_model=Feature)
def update(
    code: str, feature_update: FeatureUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "FEATURES", can_edit=True))
) -> Feature:
    """
    Update an existing feature.

    - **code**: Unique feature code to update
    - Only provided fields are updated
    """
    feature = session.get(Feature, code)
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    update_data = feature_update.model_dump(exclude_unset=True)
    
    # Validate type field - if type is empty, "null" or "none", convert to None
    if "type" in update_data and update_data["type"] in ["", "null", "none"]:
        update_data["type"] = None
    
    for key, value in update_data.items():
        setattr(feature, key, value)

    # Update timestamp
    feature.updated_at = datetime.utcnow()

    session.add(feature)
    session.commit()
    session.refresh(feature)
    logger.info(f"Feature updated: {code}")
    return feature


@router.delete("/{code}", response_model=Feature, status_code=200)
def delete(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "FEATURES", can_edit=True))
) -> Feature:
    """
    Delete a feature (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique feature code to delete
    """
    feature = session.get(Feature, code)
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    # Check if already inactive
    if not feature.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Feature with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    feature.is_active = False
    feature.updated_at = datetime.utcnow()

    session.add(feature)
    session.commit()
    session.refresh(feature)
    logger.info(
        f"Feature deactivated (logical delete): {code}")
    return feature
