import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Role, RoleCreate, RoleUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.post("/", response_model=Role, status_code=201)
def create_role(
    role: RoleCreate, session: Session = Depends(get_db_session)
) -> Role:
    """
    Create a new role.

    - **code**: Unique role code (required)
    - **name**: Role name (required)
    - **description**: Optional role description
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing_role = session.get(Role, role.code)
    if existing_role:
        raise HTTPException(
            status_code=409,
            detail=f"Role with code '{role.code}' already exists"
        )

    try:
        db_role = Role.model_validate(role)
        session.add(db_role)
        session.commit()
        session.refresh(db_role)
        logger.info(f"Role created: {role.code}")
        return db_role
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating role {role.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Role with code '{role.code}' already exists"
        )


@router.get("/", response_model=List[Role])
def list_roles(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db_session),
) -> List[Role]:
    """
    List all roles with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    roles = session.exec(select(Role).offset(
        skip).limit(limit).order_by(Role.name)).all()
    return roles


@router.get("/{role_code}", response_model=Role)
def get_role(role_code: str, session: Session = Depends(get_db_session)) -> Role:
    """
    Get a role by its code.

    - **role_code**: Unique role code
    """
    role = session.get(Role, role_code)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.put("/{role_code}", response_model=Role)
def update_role(
    role_code: str, role_update: RoleUpdate, session: Session = Depends(get_db_session)
) -> Role:
    """
    Update an existing role.

    - **role_code**: Unique role code to update
    - Only provided fields are updated
    """
    role = session.get(Role, role_code)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    update_data = role_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(role, key, value)

    # Update timestamp
    role.updated_at = datetime.utcnow()

    session.add(role)
    session.commit()
    session.refresh(role)
    logger.info(f"Role updated: {role_code}")
    return role


@router.delete("/{role_code}", response_model=Role, status_code=200)
def delete_role(role_code: str, session: Session = Depends(get_db_session)) -> Role:
    """
    Delete a role (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **role_code**: Unique role code to delete
    """
    role = session.get(Role, role_code)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Check if already inactive
    if not role.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Role with code '{role_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    role.is_active = False
    role.updated_at = datetime.utcnow()

    session.add(role)
    session.commit()
    session.refresh(role)
    logger.info(f"Role deactivated (logical delete): {role_code}")
    return role
