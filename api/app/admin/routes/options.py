import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy.exc import IntegrityError

from ..internal.models import Option, OptionCreate, OptionUpdate, Module, User
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/options", tags=["options"])

#Model for option select options
class OptionBasic(SQLModel):
    value: str
    label: str

@router.get("/select", response_model=List[OptionBasic])
def get_list(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "OPTIONS", can_edit=False))
) -> List[OptionBasic]:
    """
    Returns an options list optimized for selects with value (code) and label (name). 
    Only active options.
    """
    statement = (
        select(
            Option.code.label("value"), 
            Option.name.label("label")
        )
        .where(Option.is_active == True)
        .order_by(Option.name)
    )
    return session.exec(statement).all()


@router.get("/", response_model=List[Option])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "OPTIONS", can_edit=False))
) -> List[Option]:
    """
    List all options with pagination (*Only active options).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    options = session.exec(select(Option).where(Option.is_active == True)
                           .offset(skip).limit(limit)
                           .order_by(Option.module, Option.sort_order, Option.name)).all()
    return options


@router.get("/{module_code}/{code}", response_model=Option)
def get(
    module_code: str, code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "OPTIONS", can_edit=False))
) -> Option:
    """
    Get an option by its module and code.

    - **module_code**: Module code
    - **code**: Option code
    """
    option = session.exec(
        select(Option).where(Option.module ==
                             module_code, Option.code == code)
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    elif not option.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Option with module '{module_code}' and code '{code}' is inactive"
        )
    return option


@router.post("/", response_model=Option, status_code=201)
def create(
    option: OptionCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "OPTIONS", can_edit=True))
) -> Option:
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
    existing = session.exec(
        select(Option).where(
            Option.module == option.module,
            Option.code == option.code
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Option with module '{option.module}' and code '{option.code}' already exists"
        )

    try:
        db = Option.model_validate(option)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Option created: {option.module}/{option.code}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating option {option.module}/{option.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Option with module '{option.module}' and code '{option.code}' already exists"
        )


@router.put("/{module_code}/{code}", response_model=Option)
def update(
    module_code: str, code: str, option_update: OptionUpdate, session: Session = Depends(get_db_session)
) -> Option:
    """
    Update an existing option.

    - **module_code**: Module code
    - **code**: Option code
    - Only provided fields are updated
    """
    option = session.exec(
        select(Option).where(Option.module ==
                             module_code, Option.code == code)
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
    logger.info(f"Option updated: {module_code}/{code}")
    return option


@router.delete("/{module_code}/{code}", response_model=Option, status_code=200)
def delete(
    module_code: str, code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "OPTIONS", can_edit=True))
) -> Option:
    """
    Delete an option (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **module_code**: Module code
    - **code**: Option code
    """
    option = session.exec(
        select(Option).where(Option.module ==
                             module_code, Option.code == code)
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    # Check if already inactive
    if not option.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Option with module '{module_code}' and code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    option.is_active = False
    option.updated_at = datetime.utcnow()

    session.add(option)
    session.commit()
    session.refresh(option)
    logger.info(
        f"Option deactivated (logical delete): {module_code}/{code}")
    return option
