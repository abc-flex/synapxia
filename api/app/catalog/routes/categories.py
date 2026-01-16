import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Category, CategoryCreate, CategoryUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.post("/", response_model=Category, status_code=201)
def create_category(category: CategoryCreate, session: Session = Depends(get_db_session)) -> Category:
    """
    Create a new category.

    - **code**: Unique category code (required)
    - **name**: Category name (required)
    - **description**: Optional description
    - **parent**: Parent category code (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing_category = session.get(Category, category.code)
    if existing_category:
        raise HTTPException(
            status_code=409,
            detail=f"Category with code '{category.code}' already exists"
        )

    # Validate that the parent category exists if provided
    if category.parent:
        parent_category = session.get(Category, category.parent)
        if not parent_category:
            raise HTTPException(
                status_code=400,
                detail=f"Parent category with code '{category.parent}' does not exist"
            )

    try:
        db_category = Category.model_validate(category)
        session.add(db_category)
        session.commit()
        session.refresh(db_category)
        logger.info(f"Category created: {category.code}")
        return db_category
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating category {category.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Category with code '{category.code}' already exists"
        )


@router.get("/", response_model=List[Category])
def list_categories(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Category]:
    """
    List all categories with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    categories = session.exec(select(Category).offset(
        skip).limit(limit).order_by(Category.name)).all()
    return categories


@router.get("/{category_code}", response_model=Category)
def get_category(category_code: str, session: Session = Depends(get_db_session)) -> Category:
    """
    Get a category by its code.

    - **category_code**: Unique category code
    """
    category = session.get(Category, category_code)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_code}", response_model=Category)
def update_category(category_code: str, category_update: CategoryUpdate, session: Session = Depends(get_db_session)) -> Category:
    """
    Update an existing category.

    - **category_code**: Unique category code to update
    - Only provided fields are updated
    """
    category = session.get(Category, category_code)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Validate that the parent category exists if provided
    if category_update.parent is not None:
        parent_category = session.get(Category, category_update.parent)
        if not parent_category:
            raise HTTPException(
                status_code=400,
                detail=f"Parent category with code '{category_update.parent}' does not exist"
            )

    update_data = category_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    # Update timestamp
    category.updated_at = datetime.utcnow()

    session.add(category)
    session.commit()
    session.refresh(category)
    logger.info(f"Category updated: {category_code}")
    return category


@router.delete("/{category_code}", response_model=Category, status_code=200)
def delete_category(category_code: str, session: Session = Depends(get_db_session)) -> Category:
    """
    Delete a category (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **category_code**: Unique category code to delete
    """
    category = session.get(Category, category_code)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if already inactive
    if not category.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Category with code '{category_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    category.is_active = False
    category.updated_at = datetime.utcnow()

    session.add(category)
    session.commit()
    session.refresh(category)
    logger.info(f"Category deactivated (logical delete): {category_code}")
    return category
