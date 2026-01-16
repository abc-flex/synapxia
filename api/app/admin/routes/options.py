import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Option, OptionCreate, OptionUpdate, Module
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/options", tags=["options"])


@router.post("/", response_model=Option, status_code=201)
def create_option(option: OptionCreate, session: Session = Depends(get_db_session)) -> Option:
    """
    Create a new option.

    - **module**: Module code (required)
    - **code**: Unique option code (required)
    - **name**: Option name (required)
    - **type**: Option type (required)
    - **description**: Optional description
    - **path**: Option path (optional)
    - **icon**: Option icon (optional)
    - **sort_order**: Display order (default: 0)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the module exists
    module = session.get(Module, option.module)
    if not module:
        raise HTTPException(
            status_code=400,
            detail=f"Module with code '{option.module}' does not exist"
        )

    # Validate that the option does not already exist
    existing_option = session.exec(
        select(Option).where(
            Option.module == option.module,
            Option.code == option.code
        )
    ).first()
    if existing_option:
        raise HTTPException(
            status_code=409,
            detail=f"Option with module '{option.module}' and code '{option.code}' already exists"
        )

    try:
        db_option = Option.model_validate(option)
        session.add(db_option)
        session.commit()
        session.refresh(db_option)
        logger.info(f"Option created: {option.module}/{option.code}")
        return db_option
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating option {option.module}/{option.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Option with module '{option.module}' and code '{option.code}' already exists"
        )


@router.get("/", response_model=List[Option])
def list_options(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Option]:
    """
    List all options with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    options = session.exec(select(Option).offset(skip).limit(
        limit).order_by(Option.module, Option.sort_order, Option.name)).all()
    return options


@router.get("/{module_code}/{option_code}", response_model=Option)
def get_option(module_code: str, option_code: str, session: Session = Depends(get_db_session)) -> Option:
    """
    Get an option by its module and code.

    - **module_code**: Module code
    - **option_code**: Option code
    """
    option = session.exec(
        select(Option).where(Option.module ==
                             module_code, Option.code == option_code)
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    return option


@router.put("/{module_code}/{option_code}", response_model=Option)
def update_option(
    module_code: str, option_code: str, option_update: OptionUpdate, session: Session = Depends(get_db_session)
) -> Option:
    """
    Update an existing option.

    - **module_code**: Module code
    - **option_code**: Option code
    - Only provided fields are updated
    """
    option = session.exec(
        select(Option).where(Option.module ==
                             module_code, Option.code == option_code)
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    update_data = option_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(option, key, value)

    # Actualizar timestamp
    option.updated_at = datetime.utcnow()

    session.add(option)
    session.commit()
    session.refresh(option)
    logger.info(f"Option updated: {module_code}/{option_code}")
    return option


@router.delete("/{module_code}/{option_code}", response_model=Option, status_code=200)
def delete_option(module_code: str, option_code: str, session: Session = Depends(get_db_session)) -> Option:
    """
    Delete an option (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **module_code**: Module code
    - **option_code**: Option code
    """
    option = session.exec(
        select(Option).where(Option.module ==
                             module_code, Option.code == option_code)
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    # Check if already inactive
    if not option.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Option with module '{module_code}' and code '{option_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    option.is_active = False
    option.updated_at = datetime.utcnow()

    session.add(option)
    session.commit()
    session.refresh(option)
    logger.info(
        f"Option deactivated (logical delete): {module_code}/{option_code}")
    return option
