import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import User, UserCreate, UserUpdate, Role, BusinessUnit
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/", response_model=User, status_code=201)
def create_user(user: UserCreate, session: Session = Depends(get_db_session)) -> User:
    """
    Create a new user.

    - **username**: Unique username (required)
    - **email**: Unique email address (required)
    - **password_hash**: Password hash (required)
    - **first_name**: First name (required)
    - **last_name**: Last name (required)
    - **menu_role**: Role code (required)
    - **business_unit**: Business unit code (required)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the username does not exist
    existing_user = session.exec(select(User).where(
        User.username == user.username)).first()
    if existing_user:
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

    # Validate that the role exists
    role = session.get(Role, user.menu_role)
    if not role:
        raise HTTPException(
            status_code=400,
            detail=f"Role with code '{user.menu_role}' does not exist"
        )

    # Validate that the business_unit exists
    business_unit = session.get(BusinessUnit, user.business_unit)
    if not business_unit:
        raise HTTPException(
            status_code=400,
            detail=f"Business unit with code '{user.business_unit}' does not exist"
        )

    try:
        db_user = User.model_validate(user)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        logger.info(f"User created: {user.username}")
        return db_user
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating user {user.username}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"User with username '{user.username}' or email '{user.email}' already exists"
        )


@router.get("/", response_model=List[User])
def list_users(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[User]:
    """
    List all users with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    users = session.exec(select(User).offset(
        skip).limit(limit).order_by(User.username)).all()
    return users

@router.get("/{role_code}", response_model=List[User])
def get_users_by_role(
    role_code: str, 
    session: Session = Depends(get_db_session)
) -> List[User]:
    """
    Get all users from a specific role.
    
    - **role_code**: role code to filter users
    """
    # Validate if role exists (optional)
    role_exists = session.get(Role, role_code)
    if not role_exists:
        raise HTTPException(
            status_code=404, 
            detail=f"Role with code '{role_code}' does not exist"
        )
    users = session.exec(
        select(User)
        .where(User.menu_role == role_code)
        .order_by(User.username)
    ).all()
    return users


@router.get("/{user_id}", response_model=User)
def get_user(user_id: int, session: Session = Depends(get_db_session)) -> User:
    """
    Get a user by their ID.

    - **user_id**: Unique user ID
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=User)
def update_user(user_id: int, user_update: UserUpdate, session: Session = Depends(get_db_session)) -> User:
    """
    Update an existing user.

    - **user_id**: Unique user ID to update
    - Only provided fields are updated
    """
    user = session.get(User, user_id)
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

    # Validate that the role exists if provided
    if user_update.menu_role is not None:
        role = session.get(Role, user_update.menu_role)
        if not role:
            raise HTTPException(
                status_code=400,
                detail=f"Role with code '{user_update.menu_role}' does not exist"
            )

    # Validate that the business_unit exists if provided
    if user_update.business_unit is not None:
        business_unit = session.get(BusinessUnit, user_update.business_unit)
        if not business_unit:
            raise HTTPException(
                status_code=400,
                detail=f"Business unit with code '{user_update.business_unit}' does not exist"
            )

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    # Update timestamp
    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"User updated: {user_id}")
    return user


@router.delete("/{user_id}", response_model=User, status_code=200)
def delete_user(user_id: int, session: Session = Depends(get_db_session)) -> User:
    """
    Delete a user (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **user_id**: Unique user ID to delete
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already inactive
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"User with id '{user_id}' is already inactive"
        )

    # Logical delete: update is_active to False
    user.is_active = False
    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"User deactivated (logical delete): {user_id}")
    return user
