import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import List, ListCreate, ListUpdate, Module
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/lists", tags=["lists"])


@router.get("/", response_model=List[List])
def get_all(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[List]:
    """
    List all lists with pagination (*Only active lists).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    lists = session.exec(select(List).where(List.is_active == True).offset(skip).limit(limit).
                         order_by(List.name)).all()
    return lists


@router.get("/{code}", response_model=List)
def get(code: str, session: Session = Depends(get_db_session)) -> List:
    """
    Get a list by its code.

    - **code**: Unique list code
    """
    list_item = session.get(List, code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")
    return list_item


@router.post("/", response_model=List, status_code=201)
def create(list_data: ListCreate, session: Session = Depends(get_db_session)) -> List:
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
    existing = session.get(List, list_data.code)
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
        db = List.model_validate(list_data)
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


@router.put("/{code}", response_model=List)
def update(code: str, list_update: ListUpdate, session: Session = Depends(get_db_session)) -> List:
    """
    Update an existing list.

    - **code**: Unique list code to update
    - Only provided fields are updated
    """
    list_item = session.get(List, code)
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


@router.delete("/{code}", response_model=List, status_code=200)
def delete(code: str, session: Session = Depends(get_db_session)) -> List:
    """
    Delete a list (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique list code to delete
    """
    list_item = session.get(List, code)
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
