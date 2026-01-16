import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Characterization, CharacterizationCreate, CharacterizationUpdate, Asset, Characteristic
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/characterizations", tags=["characterizations"])


@router.post("/", response_model=Characterization, status_code=201)
def create_characterization(characterization: CharacterizationCreate, session: Session = Depends(get_db_session)) -> Characterization:
    """
    Create a new characterization.

    - **asset**: Asset code (required)
    - **characteristic**: Characteristic code (required)
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

    # Validate that the characteristic exists
    characteristic = session.get(
        Characteristic, characterization.characteristic)
    if not characteristic:
        raise HTTPException(
            status_code=400,
            detail=f"Characteristic with code '{characterization.characteristic}' does not exist"
        )

    # Validate that the characterization doesn't already exist
    existing_char = session.exec(
        select(Characterization).where(
            Characterization.asset == characterization.asset,
            Characterization.characteristic == characterization.characteristic
        )
    ).first()
    if existing_char:
        raise HTTPException(
            status_code=409,
            detail=f"Characterization with asset '{characterization.asset}' and characteristic '{characterization.characteristic}' already exists"
        )

    try:
        db_char = Characterization.model_validate(characterization)
        session.add(db_char)
        session.commit()
        session.refresh(db_char)
        logger.info(
            f"Characterization created: {characterization.asset}/{characterization.characteristic}")
        return db_char
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating characterization {characterization.asset}/{characterization.characteristic}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Characterization with asset '{characterization.asset}' and characteristic '{characterization.characteristic}' already exists"
        )


@router.get("/", response_model=List[Characterization])
def list_characterizations(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Characterization]:
    """
    List all characterizations with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    characterizations = session.exec(select(Characterization).offset(skip).limit(
        limit).order_by(Characterization.asset, Characterization.characteristic)).all()
    return characterizations


@router.get("/{asset_code}/{characteristic_code}", response_model=Characterization)
def get_characterization(asset_code: str, characteristic_code: str, session: Session = Depends(get_db_session)) -> Characterization:
    """
    Get a characterization by its asset and characteristic.

    - **asset_code**: Asset code
    - **characteristic_code**: Characteristic code
    """
    characterization = session.exec(
        select(Characterization).where(
            Characterization.asset == asset_code,
            Characterization.characteristic == characteristic_code
        )
    ).first()
    if not characterization:
        raise HTTPException(
            status_code=404, detail="Characterization not found")
    return characterization


@router.put("/{asset_code}/{characteristic_code}", response_model=Characterization)
def update_characterization(
    asset_code: str, characteristic_code: str, characterization_update: CharacterizationUpdate, session: Session = Depends(get_db_session)
) -> Characterization:
    """
    Update an existing characterization.

    - **asset_code**: Asset code
    - **characteristic_code**: Characteristic code
    - Only provided fields are updated
    """
    characterization = session.exec(
        select(Characterization).where(
            Characterization.asset == asset_code,
            Characterization.characteristic == characteristic_code
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
        f"Characterization updated: {asset_code}/{characteristic_code}")
    return characterization


@router.delete("/{asset_code}/{characteristic_code}", response_model=Characterization, status_code=200)
def delete_characterization(asset_code: str, characteristic_code: str, session: Session = Depends(get_db_session)) -> Characterization:
    """
    Delete a characterization (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **asset_code**: Asset code
    - **characteristic_code**: Characteristic code
    """
    characterization = session.exec(
        select(Characterization).where(
            Characterization.asset == asset_code,
            Characterization.characteristic == characteristic_code
        )
    ).first()
    if not characterization:
        raise HTTPException(
            status_code=404, detail="Characterization not found")

    # Check if already inactive
    if not characterization.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Characterization with asset '{asset_code}' and characteristic '{characteristic_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    characterization.is_active = False
    characterization.updated_at = datetime.utcnow()

    session.add(characterization)
    session.commit()
    session.refresh(characterization)
    logger.info(
        f"Characterization deactivated (logical delete): {asset_code}/{characteristic_code}")
    return characterization
