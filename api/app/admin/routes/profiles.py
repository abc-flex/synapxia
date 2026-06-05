import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy.exc import IntegrityError

from ..internal.models import Profile, ProfileCreate, ProfileUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profiles", tags=["profiles"])

#Model for profiles select options
class ProfileBasic(SQLModel):
    value: str
    label: str

@router.get("/select", response_model=List[ProfileBasic])
def get_list(session: Session = Depends(get_db_session)) -> List[ProfileBasic]:
    """
    Returns a profiles list optimized for selects with value (code) and label (name). 
    Only active profiles.
    """
    statement = (
        select(
            Profile.code.label("value"), 
            Profile.name.label("label")
        )
        .where(Profile.is_active == True)
        .order_by(Profile.name)
    )
    return session.exec(statement).all()


@router.get("/", response_model=List[Profile])
def get_all(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db_session),
) -> List[Profile]:
    """
    List all profiles actives with pagination (*Only active profiles).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    profiles = session.exec(select(Profile).where(Profile.is_active == True)
                         .offset(skip).limit(limit)
                         .order_by(Profile.name)).all()
    return profiles


@router.get("/{code}", response_model=Profile)
def get(code: str, session: Session = Depends(get_db_session)) -> Profile:
    """
    Get a profile by its code.

    - **code**: Unique profile code
    """
    profile = session.get(Profile, code)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    elif not profile.is_active:
        raise HTTPException(status_code=400, detail=f"Profile with code '{code}' is inactive")
    return profile


@router.post("/", response_model=Profile, status_code=201)
def create(
    profile: ProfileCreate, session: Session = Depends(get_db_session)
) -> Profile:
    """
    Create a new profile.

    - **code**: Unique profile code (required)
    - **name**: Profile name (required)
    - **description**: Optional profile description
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing = session.get(Profile, profile.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Profile with code '{profile.code}' already exists"
        )

    try:
        db = Profile.model_validate(profile)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Profile created: {profile.code}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating profile {profile.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Profile with code '{profile.code}' already exists"
        )


@router.put("/{code}", response_model=Profile)
def update(
    code: str, profile_update: ProfileUpdate, session: Session = Depends(get_db_session)
) -> Profile:
    """
    Update an existing profile.

    - **code**: Unique profile code to update
    - Only provided fields are updated
    """
    profile = session.get(Profile, code)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = profile_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    # Update timestamp
    profile.updated_at = datetime.utcnow()

    session.add(profile)
    session.commit()
    session.refresh(profile)
    logger.info(f"Profile updated: {code}")
    return profile


@router.delete("/{code}", response_model=Profile, status_code=200)
def delete(code: str, session: Session = Depends(get_db_session)) -> Profile:
    """
    Delete a profile (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique profile code to delete
    """
    profile = session.get(Profile, code)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Check if already inactive
    if not profile.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Profile with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    profile.is_active = False
    profile.updated_at = datetime.utcnow()

    session.add(profile)
    session.commit()
    session.refresh(profile)
    logger.info(f"Profile deactivated (logical delete): {code}")
    return profile
