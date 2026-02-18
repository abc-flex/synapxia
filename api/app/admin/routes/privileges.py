import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Privilege, PrivilegeCreate, PrivilegeUpdate, Role, Option
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/privileges", tags=["privileges"])


@router.post("/", response_model=Privilege, status_code=201)
def create_privilege(privilege: PrivilegeCreate, session: Session = Depends(get_db_session)) -> Privilege:
    """
    Create a new privilege.

    - **role**: Role code (required)
    - **module**: Module code (required)
    - **option**: Option code (required)
    - **can_edit**: Indicates if can edit (default: True)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the role exists
    role = session.get(Role, privilege.role)
    if not role:
        raise HTTPException(
            status_code=400,
            detail=f"Role with code '{privilege.role}' does not exist"
        )

    # Validate that the option exists
    option = session.exec(
        select(Option).where(
            Option.module == privilege.module,
            Option.code == privilege.option
        )
    ).first()
    if not option:
        raise HTTPException(
            status_code=400,
            detail=f"Option with module '{privilege.module}' and code '{privilege.option}' does not exist"
        )

    # Validate that the privilege does not already exist
    existing_privilege = session.exec(
        select(Privilege).where(
            Privilege.role == privilege.role,
            Privilege.module == privilege.module,
            Privilege.option == privilege.option
        )
    ).first()
    if existing_privilege:
        raise HTTPException(
            status_code=409,
            detail=f"Privilege with role '{privilege.role}', module '{privilege.module}' and option '{privilege.option}' already exists"
        )

    try:
        db_privilege = Privilege.model_validate(privilege)
        session.add(db_privilege)
        session.commit()
        session.refresh(db_privilege)
        logger.info(
            f"Privilege created: {privilege.role}/{privilege.module}/{privilege.option}")
        return db_privilege
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating privilege {privilege.role}/{privilege.module}/{privilege.option}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Privilege with role '{privilege.role}', module '{privilege.module}' and option '{privilege.option}' already exists"
        )


@router.get("/", response_model=List[Privilege])
def list_privileges(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Privilege]:
    """
    List all privileges with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    privileges = session.exec(select(Privilege).offset(skip).limit(
        limit).order_by(Privilege.role, Privilege.module, Privilege.option)).all()
    return privileges


@router.get("/{role_code}/{module_code}/{option_code}", response_model=Privilege)
def get_privilege(role_code: str, module_code: str, option_code: str, session: Session = Depends(get_db_session)) -> Privilege:
    """
    Get a privilege by its role, module and option.

    - **role_code**: Role code
    - **module_code**: Module code
    - **option_code**: Option code
    """
    privilege = session.exec(
        select(Privilege).where(
            Privilege.role == role_code,
            Privilege.module == module_code,
            Privilege.option == option_code
        )
    ).first()
    if not privilege:
        raise HTTPException(status_code=404, detail="Privilege not found")
    return privilege


@router.get("/{role_code}", response_model=List[Privilege])
def get_privileges_by_role(
    role_code: str, 
    session: Session = Depends(get_db_session)
) -> List[Privilege]:
    """
    Get all privileges for a specific role.
    
    - **role_code**: Role code to filter by
    """
    # Validar primero si la lista existe (opcional, pero recomendado por integridad)
    role_exists = session.get(Role, role_code)
    if not role_exists:
        raise HTTPException(
            status_code=404, 
            detail=f"Role with code '{role_code}' does not exist"
        )
    items = session.exec(
        select(Privilege)
        .where(Privilege.role == role_code)
        .order_by(Privilege.module, Privilege.option)
    ).all()
    return items


@router.put("/{role_code}/{module_code}/{option_code}", response_model=Privilege)
def update_privilege(
    role_code: str, module_code: str, option_code: str, privilege_update: PrivilegeUpdate, session: Session = Depends(get_db_session)
) -> Privilege:
    """
    Update an existing privilege.

    - **role_code**: Role code
    - **module_code**: Module code
    - **option_code**: Option code
    - Only provided fields are updated
    """
    privilege = session.exec(
        select(Privilege).where(
            Privilege.role == role_code,
            Privilege.module == module_code,
            Privilege.option == option_code
        )
    ).first()
    if not privilege:
        raise HTTPException(status_code=404, detail="Privilege not found")

    update_data = privilege_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(privilege, key, value)

    # Update timestamp
    privilege.updated_at = datetime.utcnow()

    session.add(privilege)
    session.commit()
    session.refresh(privilege)
    logger.info(f"Privilege updated: {role_code}/{module_code}/{option_code}")
    return privilege


@router.delete("/{role_code}/{module_code}/{option_code}", response_model=Privilege, status_code=200)
def delete_privilege(role_code: str, module_code: str, option_code: str, session: Session = Depends(get_db_session)) -> Privilege:
    """
    Delete a privilege (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **role_code**: Role code
    - **module_code**: Module code
    - **option_code**: Option code
    """
    privilege = session.exec(
        select(Privilege).where(
            Privilege.role == role_code,
            Privilege.module == module_code,
            Privilege.option == option_code
        )
    ).first()
    if not privilege:
        raise HTTPException(status_code=404, detail="Privilege not found")

    # Check if already inactive
    if not privilege.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Privilege with role '{role_code}', module '{module_code}' and option '{option_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    privilege.is_active = False
    privilege.updated_at = datetime.utcnow()

    session.add(privilege)
    session.commit()
    session.refresh(privilege)
    logger.info(
        f"Privilege deactivated (logical delete): {role_code}/{module_code}/{option_code}")
    return privilege
