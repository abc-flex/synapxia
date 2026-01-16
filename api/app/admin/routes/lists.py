import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import List as ListModel, ListCreate, ListUpdate, Module
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/lists", tags=["lists"])


@router.post("/", response_model=ListModel, status_code=201)
def create_list(list_data: ListCreate, session: Session = Depends(get_db_session)) -> ListModel:
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
    existing_list = session.get(ListModel, list_data.code)
    if existing_list:
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
        db_list = ListModel.model_validate(list_data)
        session.add(db_list)
        session.commit()
        session.refresh(db_list)
        logger.info(f"List created: {list_data.code}")
        return db_list
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating list {list_data.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"List with code '{list_data.code}' already exists"
        )


@router.get("/", response_model=List[ListModel])
def list_lists(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[ListModel]:
    """
    List all lists with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    lists = session.exec(select(ListModel).offset(
        skip).limit(limit).order_by(ListModel.name)).all()
    return lists


@router.get("/{list_code}", response_model=ListModel)
def get_list(list_code: str, session: Session = Depends(get_db_session)) -> ListModel:
    """
    Get a list by its code.

    - **list_code**: Unique list code
    """
    list_item = session.get(ListModel, list_code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")
    return list_item


@router.put("/{list_code}", response_model=ListModel)
def update_list(list_code: str, list_update: ListUpdate, session: Session = Depends(get_db_session)) -> ListModel:
    """
    Update an existing list.

    - **list_code**: Unique list code to update
    - Only provided fields are updated
    """
    list_item = session.get(ListModel, list_code)
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
    logger.info(f"List updated: {list_code}")
    return list_item


@router.delete("/{list_code}", response_model=ListModel, status_code=200)
def delete_list(list_code: str, session: Session = Depends(get_db_session)) -> ListModel:
    """
    Delete a list (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **list_code**: Unique list code to delete
    """
    list_item = session.get(ListModel, list_code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")

    # Check if already inactive
    if not list_item.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"List with code '{list_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    list_item.is_active = False
    list_item.updated_at = datetime.utcnow()

    session.add(list_item)
    session.commit()
    session.refresh(list_item)
    logger.info(f"List deactivated (logical delete): {list_code}")
    return list_item
