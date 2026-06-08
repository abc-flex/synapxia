import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy.exc import IntegrityError

from ..internal.models import List as ListModel, ListCreate, ListUpdate, Module, User
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import check_privilege

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/lists", tags=["lists"])

#Model for module select options
class ListBasic(SQLModel):
    value: str
    label: str

@router.get("/select", response_model=List[ListBasic])
def get_list(
    session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LISTS", can_edit=False))
) -> List[ListBasic]:
    """
    Returns a lists list optimized for selects with value (code) and label (name). 
    Only active lists.
    """
    statement = (
        select(
            ListModel.code.label("value"), 
            ListModel.name.label("label")
        )
        .where(ListModel.is_active == True)
        .order_by(ListModel.name)
    )
    return session.exec(statement).all()


@router.get("/", response_model=List[ListModel])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LISTS", can_edit=False))
) -> List[ListModel]:
    """
    List all lists with pagination (*Only active lists).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    lists = session.exec(select(ListModel).where(ListModel.is_active == True)
                         .offset(skip).limit(limit)
                         .order_by(ListModel.name)).all()
    return lists


@router.get("/type/{list_type}", response_model=List[ListModel])
def get_by_type(
    list_type: str, 
    session: Session = Depends(get_db_session)
) -> List[ListModel]:
    """
    Obtener todos los elementos de una lista específica.
    Si no existen registros para el tipo indicado, devuelve una lista vacía.

    - **list_type**: Tipo de la lista para filtrar
    """
    items = session.exec(
        select(ListModel)
        .where(ListModel.type == list_type, ListModel.is_active == True)
        .order_by(ListModel.name)
    ).all()
    return items


@router.get("/{code}", response_model=ListModel)
def get(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LISTS", can_edit=False))
) -> ListModel:
    """
    Get a list by its code.

    - **code**: Unique list code
    """
    list_item = session.get(ListModel, code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")
    elif not list_item.is_active:
        raise HTTPException(status_code=400, detail=f"List with code '{code}' is inactive") 
    return list_item


@router.post("/", response_model=ListModel, status_code=201)
def create(
    list_data: ListCreate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LISTS", can_edit=True))
) -> ListModel:
    """
    Create a new list.

    - **code**: Unique list code (required)
    - **name**: List name (required)
    - **type**: List type (required)
    - **description**: Optional description
    - **module**: Associated module code (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing = session.get(ListModel, list_data.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"List with code '{list_data.code}' already exists"
        )

    # Validate that the module exists if provided
    if list_data.module:
        module = session.get(Module, list_data.module)
        if not module:
            raise HTTPException(
                status_code=400,
                detail=f"Module with code '{list_data.module}' does not exist"
            )

    try:
        db = ListModel.model_validate(list_data)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"List created: {list_data.code}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating list {list_data.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"List with code '{list_data.code}' already exists"
        )


@router.put("/{code}", response_model=ListModel)
def update(
    code: str, list_update: ListUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LISTS", can_edit=True))
) -> ListModel:
    """
    Update an existing list.

    - **code**: Unique list code to update
    - Only provided fields are updated
    """
    list_item = session.get(ListModel, code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")

    # Validate that the module exists if provided
    if list_update.module is not None:
        module = session.get(Module, list_update.module)
        if not module:
            raise HTTPException(
                status_code=400,
                detail=f"Module with code '{list_update.module}' does not exist"
            )

    update_data = list_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(list_item, key, value)

    # Update timestamp
    list_item.updated_at = datetime.utcnow()

    session.add(list_item)
    session.commit()
    session.refresh(list_item)
    logger.info(f"List updated: {code}")
    return list_item


@router.delete("/{code}", response_model=ListModel, status_code=200)
def delete(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LISTS", can_edit=True))
) -> ListModel:
    """
    Delete a list (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique list code to delete
    """
    list_item = session.get(ListModel, code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")

    # Check if already inactive
    if not list_item.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"List with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    list_item.is_active = False
    list_item.updated_at = datetime.utcnow()

    session.add(list_item)
    session.commit()
    session.refresh(list_item)
    logger.info(f"List deactivated (logical delete): {code}")
    return list_item
