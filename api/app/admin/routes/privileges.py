import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Privilege, PrivilegeCreate, PrivilegeUpdate, Profile, Option, User
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import check_privilege

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/privileges", tags=["privileges"])


@router.get("/", response_model=List[Privilege])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "PRIVILEGES", can_edit=False))
) -> List[Privilege]:
    """
    List all privileges with pagination (*Only active privileges).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    privileges = session.exec(select(Privilege).where(Privilege.is_active == True)
                              .offset(skip).limit(limit)
                              .order_by(Privilege.profile, Privilege.module, Privilege.option)).all()
    return privileges


@router.get("/profile/{profile_code}", response_model=List[Privilege])
def get_by_profile(
    profile_code: str, 
    session: Session = Depends(get_db_session)
) -> List[Privilege]:
    """
    Get all privileges for a specific profile.
    
    - **profile_code**: Profile code to filter by
    """
    # Validar primero si la lista existe (opcional, pero recomendado por integridad)
    profile_exists = session.get(Profile, profile_code)
    if not profile_exists:
        raise HTTPException(
            status_code=404, 
            detail=f"Profile with code '{profile_code}' does not exist"
        )
    items = session.exec(
        select(Privilege)
        .where(Privilege.profile == profile_code)
        .order_by(Privilege.module, Privilege.option)
    ).all()
    return items


@router.get("/{profile_code}/{module_code}/{option_code}", response_model=Privilege)
def get(
    profile_code: str, module_code: str, option_code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "PRIVILEGES", can_edit=False))
) -> Privilege:
    """
    Get a privilege by its profile, module and option.

    - **profile_code**: Profile code
    - **module_code**: Module code
    - **option_code**: Option code
    """
    privilege = session.exec(
        select(Privilege).where(
            Privilege.profile == profile_code,
            Privilege.module == module_code,
            Privilege.option == option_code
        )
    ).first()
    if not privilege:
        raise HTTPException(status_code=404, detail="Privilege not found")
    elif not privilege.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Privilege with profile '{profile_code}', module '{module_code}' and option '{option_code}' is inactive"
        )
    return privilege


@router.post("/", response_model=Privilege, status_code=201)
def create(
    privilege: PrivilegeCreate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "PRIVILEGES", can_edit=True))
) -> Privilege:
    """
    Create a new privilege.

    - **profile**: Profile code (required)
    - **module**: Module code (required)
    - **option**: Option code (required)
    - **can_edit**: Indicates if can edit (default: True)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the profile exists
    profile = session.get(Profile, privilege.profile)
    if not profile:
        raise HTTPException(
            status_code=400,
            detail=f"Profile with code '{privilege.profile}' does not exist"
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
    existing = session.exec(
        select(Privilege).where(
            Privilege.profile == privilege.profile,
            Privilege.module == privilege.module,
            Privilege.option == privilege.option
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Privilege with profile '{privilege.profile}', module '{privilege.module}' and option '{privilege.option}' already exists"
        )

    try:
        db = Privilege.model_validate(privilege)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(
            f"Privilege created: {privilege.profile}/{privilege.module}/{privilege.option}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating privilege {privilege.profile}/{privilege.module}/{privilege.option}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Privilege with profile '{privilege.profile}', module '{privilege.module}' and option '{privilege.option}' already exists"
        )


@router.put("/{profile_code}/{module_code}/{option_code}", response_model=Privilege)
def update(
    profile_code: str, module_code: str, option_code: str, privilege_update: PrivilegeUpdate, session: Session = Depends(get_db_session)
) -> Privilege:
    """
    Update an existing privilege.

    - **profile_code**: Profile code
    - **module_code**: Module code
    - **option_code**: Option code
    - Only provided fields are updated
    """
    privilege = session.exec(
        select(Privilege).where(
            Privilege.profile == profile_code,
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
    logger.info(f"Privilege updated: {profile_code}/{module_code}/{option_code}")
    return privilege


@router.delete("/{profile_code}/{module_code}/{option_code}", response_model=Privilege, status_code=200)
def delete(
    profile_code: str, module_code: str, option_code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "PRIVILEGES", can_edit=True))
) -> Privilege:
    """
    Delete a privilege (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **profile_code**: Profile code
    - **module_code**: Module code
    - **option_code**: Option code
    """
    privilege = session.exec(
        select(Privilege).where(
            Privilege.profile == profile_code,
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
            detail=f"Privilege with profile '{profile_code}', module '{module_code}' and option '{option_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    privilege.is_active = False
    privilege.updated_at = datetime.utcnow()

    session.add(privilege)
    session.commit()
    session.refresh(privilege)
    logger.info(
        f"Privilege deactivated (logical delete): {profile_code}/{module_code}/{option_code}")
    return privilege
