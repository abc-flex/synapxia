import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy.exc import IntegrityError

from ..internal.models import Module, ModuleCreate, ModuleUpdate
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import check_privilege

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/modules", tags=["modules"])

#Model for module select options
class ModuleBasic(SQLModel):
    value: str
    label: str

@router.get("/select", response_model=List[ModuleBasic])
def get_list(
    session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "MODULES", can_edit=False))
) -> List[ModuleBasic]:
    """
    Returns a modules list optimized for selects with value (code) and label (name). 
    Only active modules.
    """
    statement = (
        select(
            Module.code.label("value"), 
            Module.name.label("label")
        )
        .where(Module.is_active == True)
        .order_by(Module.name)
    )
    return session.exec(statement).all()


@router.get("/", response_model=List[Module])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "MODULES", can_edit=False))
) -> List[Module]:
    """
    List all modules with pagination (*Only active modules).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    modules = session.exec(select(Module).where(Module.is_active == True)
                           .offset(skip).limit(limit)
                           .order_by(Module.sort_order, Module.name)).all()
    return modules


@router.get("/{code}", response_model=Module)
def get(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "MODULES", can_edit=False))
) -> Module:
    """
    Get a module by its code.

    - **code**: Unique module code
    """
    module = session.get(Module, code)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    elif not module.is_active:
        raise HTTPException(status_code=400, detail=f"Module with code '{code}' is inactive")
    return module


@router.post("/", response_model=Module, status_code=201)
def create(
    module: ModuleCreate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "MODULES", can_edit=True))
) -> Module:
    """
    Create a new module.

    - **code**: Unique module code (required)
    - **name**: Module name (required)
    - **description**: Optional module description
    - **icon**: Option icon (optional)
    - **sort_order**: Display order (default: 0)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing_module = session.get(Module, module.code)
    if existing_module:
        raise HTTPException(
            status_code=409,
            detail=f"Module with code '{module.code}' already exists"
        )

    try:
        db_module = Module.model_validate(module)
        session.add(db_module)
        session.commit()
        session.refresh(db_module)
        logger.info(f"Module created: {module.code}")
        return db_module
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating module {module.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Module with code '{module.code}' already exists"
        )


@router.put("/{code}", response_model=Module)
def update(
    code: str, module_update: ModuleUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "MODULES", can_edit=True))
) -> Module:
    """
    Update an existing module.

    - **code**: Unique module code to update
    - Only provided fields are updated
    """
    module = session.get(Module, code)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    update_data = module_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(module, key, value)

    # Update timestamp
    module.updated_at = datetime.utcnow()

    session.add(module)
    session.commit()
    session.refresh(module)
    logger.info(f"Module updated: {code}")
    return module


@router.delete("/{code}", response_model=Module, status_code=200)
def delete(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "MODULES", can_edit=True))
) -> Module:
    """
    Delete a module (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique module code to delete
    """
    module = session.get(Module, code)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Check if already inactive
    if not module.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Module with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    module.is_active = False
    module.updated_at = datetime.utcnow()

    session.add(module)
    session.commit()
    session.refresh(module)
    logger.info(f"Module deactivated (logical delete): {code}")
    return module
