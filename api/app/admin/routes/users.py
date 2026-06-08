import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, literal, cast, String

from ..internal.models import User, UserCreate, UserUpdate, Profile, BusinessUnit
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import check_privilege

#Model for user select options
class UserBasic(SQLModel):
    value: str
    label: str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/select", response_model=List[UserBasic])
def get_list(
    _: User = Depends(current_active_user),
    session: Session = Depends(get_db_session)
) -> List[UserBasic]:
    """
    Returns a users list optimized for selects with value (id) and label (full name).
    Only active users.
    """
    statement = (
        select(
            cast(User.id, String).label("value"), 
            func.concat(User.first_name, literal(" "), User.last_name).label("label")
        )
        .where(User.is_active == True)
        .order_by(User.first_name, User.last_name)
    )
    return session.exec(statement).all()


@router.get("/", response_model=List[User])
def get_all(
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(lambda: check_privilege("ADMIN", "USERS", can_edit=False)),
    session: Session = Depends(get_db_session)
) -> List[User]:
    """
    List all users with pagination (*Only active users).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    users = session.exec(select(User).where(User.is_active == True).offset(skip).limit(limit).
                         order_by(User.username)).all()
    return users


@router.get("/profile/{profile_code}", response_model=List[User])
def get_by_profile(
    profile_code: str,
    _: User = Depends(lambda: check_privilege("ADMIN", "USERS", can_edit=False)),
    session: Session = Depends(get_db_session)
) -> List[User]:
    """
    Get all users from a specific profile.

    - **profile_code**: profile code to filter users
    """
    # Validate if profile exists (optional)
    profile_exists = session.get(Profile, profile_code)
    if not profile_exists:
        raise HTTPException(
            status_code=404, 
            detail=f"Profile with code '{profile_code}' does not exist"
        )
    users = session.exec(
        select(User)
        .where(User.profile == profile_code)
        .order_by(User.username)
    ).all()
    return users


@router.get("/{id}", response_model=User)
def get(
    id: int,
    _: User = Depends(lambda: check_privilege("ADMIN", "USERS", can_edit=False)),
    session: Session = Depends(get_db_session)
) -> User:
    """
    Get a user by their ID.

    - **id**: Unique user ID
    """
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail=f"User with id '{id}' is inactive")
    return user


@router.post("/", response_model=User, status_code=201)
def create(user: UserCreate, session: Session = Depends(get_db_session)) -> User:
    """
    Create a new user.

    - **username**: Unique username (required)
    - **email**: Unique email address (required)
    - **password_hash**: Password hash (required)
    - **first_name**: First name (required)
    - **last_name**: Last name (required)
    - **profile**: Profile code (required)
    - **unit**: Business unit code (required)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the username does not exist
    existing = session.exec(select(User).where(
        User.username == user.username)).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"User with username '{user.username}' already exists"
        )

    # Validate that the email does not exist
    existing_email = session.exec(
        select(User).where(User.email == user.email)).first()
    if existing_email:
        raise HTTPException(
            status_code=409,
            detail=f"User with email '{user.email}' already exists"
        )

    # Validate that the profile exists
    profile = session.get(Profile, user.profile)
    if not profile:
        raise HTTPException(
            status_code=400,
            detail=f"Profile with code '{user.profile}' does not exist"
        )

    # Validate that the unit exists
    unit = session.get(BusinessUnit, user.unit)
    if not unit:
        raise HTTPException(
            status_code=400,
            detail=f"Business unit with code '{user.unit}' does not exist"
        )

    try:
        db = User.model_validate(user)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"User created: {user.username}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating user {user.username}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"User with username '{user.username}' or email '{user.email}' already exists"
        )


@router.put("/{id}", response_model=User)
def update(id: int, user_update: UserUpdate, session: Session = Depends(get_db_session)) -> User:
    """
    Update an existing user.

    - **id**: Unique user ID to update
    - Only provided fields are updated
    """
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate that the email does not exist if being updated
    if user_update.email is not None and user_update.email != user.email:
        existing_email = session.exec(select(User).where(
            User.email == user_update.email)).first()
        if existing_email:
            raise HTTPException(
                status_code=409,
                detail=f"User with email '{user_update.email}' already exists"
            )

    # Validate that the profile exists if provided
    if user_update.profile is not None:
        profile = session.get(Profile, user_update.profile)
        if not profile:
            raise HTTPException(
                status_code=400,
                detail=f"Profile with code '{user_update.profile}' does not exist"
            )

    # Validate that the unit exists if provided
    if user_update.unit is not None:
        unit = session.get(BusinessUnit, user_update.unit)
        if not unit:
            raise HTTPException(
                status_code=400,
                detail=f"Business unit with code '{user_update.unit}' does not exist"
            )

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    # Update timestamp
    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"User updated: {id}")
    return user


@router.delete("/{id}", response_model=User, status_code=200)
def delete(id: int, session: Session = Depends(get_db_session)) -> User:
    """
    Delete a user (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **id**: Unique user ID to delete
    """
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already inactive
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"User with id '{id}' is already inactive"
        )

    # Logical delete: update is_active to False
    user.is_active = False
    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"User deactivated (logical delete): {id}")
    return user
