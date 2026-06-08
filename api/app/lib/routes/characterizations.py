import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Characterization, CharacterizationCreate, CharacterizationUpdate, Asset
from ...taxo.internal.models import Feature
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import check_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/characterizations", tags=["characterizations"])


@router.get("/", response_model=List[Characterization])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "CHARACTERIZATIONS", can_edit=False))
) -> List[Characterization]:
    """
    List all characterizations with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    characterizations = session.exec(select(Characterization).where(Characterization.is_active == True)
                                     .offset(skip).limit(limit)
                                     .order_by(Characterization.asset, Characterization.feature)).all()
    return characterizations


@router.get("/{code}/{feature_code}", response_model=Characterization)
def get(
    code: str, feature_code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "CHARACTERIZATIONS", can_edit=False))
) -> Characterization:
    """
    Get a characterization by its asset and feature.

    - **code**: Asset code
    - **feature_code**: Feature code
    """
    characterization = session.exec(
        select(Characterization).where(
            Characterization.asset == code,
            Characterization.feature == feature_code
        )
    ).first()
    if not characterization:
        raise HTTPException(status_code=404, detail="Characterization not found")
    elif not characterization.is_active:
        raise HTTPException(status_code=400, detail=f"Characterization with asset '{code}' and feature '{feature_code}' is inactive")
    return characterization


@router.post("/", response_model=Characterization, status_code=201)
def create(
    characterization: CharacterizationCreate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "CHARACTERIZATIONS", can_edit=True))
) -> Characterization:
    """
    Create a new characterization.

    - **asset**: Asset code (required)
    - **feature**: Feature code (required)
    - **value**: Characterization value (required)
    - **details**: Additional details (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the asset exists
    asset = session.get(Asset, characterization.asset)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with code '{characterization.asset}' does not exist"
        )

    # Validate that the feature exists
    feature = session.get(
        Feature, characterization.feature)
    if not feature:
        raise HTTPException(
            status_code=400,
            detail=f"Feature with code '{characterization.feature}' does not exist"
        )

    # Validate that the characterization doesn't already exist
    existing_char = session.exec(
        select(Characterization).where(
            Characterization.asset == characterization.asset,
            Characterization.feature == characterization.feature
        )
    ).first()
    if existing_char:
        raise HTTPException(
            status_code=409,
            detail=f"Characterization with asset '{characterization.asset}' and feature '{characterization.feature}' already exists"
        )

    try:
        db_char = Characterization.model_validate(characterization)
        session.add(db_char)
        session.commit()
        session.refresh(db_char)
        logger.info(
            f"Characterization created: {characterization.asset}/{characterization.feature}")
        return db_char
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating characterization {characterization.asset}/{characterization.feature}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Characterization with asset '{characterization.asset}' and feature '{characterization.feature}' already exists"
        )


@router.put("/{code}/{feature_code}", response_model=Characterization)
def update(
    code: str, feature_code: str, characterization_update: CharacterizationUpdate, session: Session = Depends(get_db_session)
) -> Characterization:
    """
    Update an existing characterization.

    - **code**: Asset code
    - **feature_code**: Feature code
    - Only provided fields are updated
    """
    characterization = session.exec(
        select(Characterization).where(
            Characterization.asset == code,
            Characterization.feature == feature_code
        )
    ).first()
    if not characterization:
        raise HTTPException(
            status_code=404, detail="Characterization not found")

    update_data = characterization_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(characterization, key, value)

    # Update timestamp
    characterization.updated_at = datetime.utcnow()

    session.add(characterization)
    session.commit()
    session.refresh(characterization)
    logger.info(
        f"Characterization updated: {code}/{feature_code}")
    return characterization


@router.delete("/{code}/{feature_code}", response_model=Characterization, status_code=200)
def delete(
    code: str, feature_code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("LIB", "CHARACTERIZATIONS", can_edit=True))
) -> Characterization:
    """
    Delete a characterization (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Asset code
    - **feature_code**: Feature code
    """
    characterization = session.exec(
        select(Characterization).where(
            Characterization.asset == code,
            Characterization.feature == feature_code
        )
    ).first()
    if not characterization:
        raise HTTPException(
            status_code=404, detail="Characterization not found")

    # Check if already inactive
    if not characterization.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Characterization with asset '{code}' and feature '{feature_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    characterization.is_active = False
    characterization.updated_at = datetime.utcnow()

    session.add(characterization)
    session.commit()
    session.refresh(characterization)
    logger.info(
        f"Characterization deactivated (logical delete): {code}/{feature_code}")
    return characterization
