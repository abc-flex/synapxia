import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy import case

from ..internal.models import Category, CategoryCreate, CategoryUpdate
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege
from ...admin.internal.models import User
from ...lib.internal.models import  Asset

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/categories", tags=["categories"])

#Model for module select options
class CategoryBasic(SQLModel):
    value: str
    label: str

class CategoryWithAssets(SQLModel):
    code: str
    name: str
    description: str | None = None
    parent: str | None = None
    option: str | None = None
    assets_count: int

@router.get("/select", response_model=List[CategoryBasic])
def get_list(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "CATEGORIES", can_edit=False))
) -> List[CategoryBasic]:
    """
    Returns a categories list optimized for selects with value (code) and label (name). 
    Only active categories.
    """
    statement = (
        select(
            Category.code.label("value"), 
            Category.name.label("label")
        )
        .where(Category.is_active == True)
        .order_by(Category.name)
    )
    return session.exec(statement).all()


@router.get("/assets", response_model=List[CategoryWithAssets])
def get_with_assets_count(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "CATEGORIES", can_edit=False))
) -> List[CategoryWithAssets]:
    """
    Returns all the active categories with the total count of associated assets,
    ordered alphabetically by name.
    """
    statement = (
        select(
            Category.code,
            Category.name,
            Category.description,
            Category.parent,
            Category.option,
            func.count(Asset.id).label("assets_count")
        )
        .outerjoin(Asset, Asset.category == Category.code)
        .where(Category.is_active == True)
        # Agrupamos por los campos seleccionados para evitar restricciones de SQL estricto
        .group_by(Category.code, Category.name, Category.parent, Category.option)
        # Ordenamos alfabéticamente por el nombre de la categoría
        .order_by(Category.name.asc())
        .offset(skip)
        .limit(limit)
    )

    results = session.exec(statement).all()
    
    return [
        CategoryWithAssets(
            code=row.code,
            name=row.name,
            description=row.description,
            parent=row.parent,
            option=row.option,
            assets_count=row.assets_count
        )
        for row in results
    ]


@router.get("/", response_model=List[Category])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "CATEGORIES", can_edit=False))
) -> List[Category]:
    """
    List all categories with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    categories = session.exec(
        select(Category)
        .where(Category.is_active == True)
        .order_by(
            # 1. Si es padre, el orden es su propio ID; si es hijo, es el ID del padre
            # COALESCE(parent, code)
            case((Category.parent == None, Category.code), else_=Category.parent),
            
            # 2. Asegura que los padres (NULL en parent) aparezcan antes que los hijos
            (Category.parent != None),
            
            # 3. Orden alfabético final
            Category.name
        )
        .offset(skip)
        .limit(limit)
    ).all() 
    return categories


@router.get("/{code}", response_model=Category)
def get(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "CATEGORIES", can_edit=False))
) -> Category:
    """
    Get a category by its code.

    - **code**: Unique category code
    """
    category = session.get(Category, code)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    elif not category.is_active:
        raise HTTPException(status_code=400, detail=f"Category with code '{code}' is inactive")
    return category


@router.post("/", response_model=Category, status_code=201)
def create(
    category: CategoryCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "CATEGORIES", can_edit=True))
) -> Category:
    """
    Create a new category.

    - **code**: Unique category code (required)
    - **name**: Category name (required)
    - **description**: Optional description
    - **parent**: Parent category code (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing = session.get(Category, category.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Category with code '{category.code}' already exists"
        )

    # Validate that the parent category exists if provided
    if category.parent:
        parent = session.get(Category, category.parent)
        if not parent:
            raise HTTPException(
                status_code=400,
                detail=f"Parent category with code '{category.parent}' does not exist"
            )

    try:
        db = Category.model_validate(category)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Category created: {category.code}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating category {category.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Category with code '{category.code}' already exists"
        )


@router.put("/{code}", response_model=Category)
def update(
    code: str, update: CategoryUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "CATEGORIES", can_edit=True))
) -> Category:
    """
    Update an existing category.

    - **code**: Unique category code to update
    - Only provided fields are updated
    """
    category = session.get(Category, code)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Validate that the parent category exists if provided
    if update.parent is not None:
        parent = session.get(Category, update.parent)
        if not parent:
            raise HTTPException(
                status_code=400,
                detail=f"Parent category with code '{update.parent}' does not exist"
            )

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    # Update timestamp
    category.updated_at = datetime.utcnow()

    session.add(category)
    session.commit()
    session.refresh(category)
    logger.info(f"Category updated: {code}")
    return category


@router.delete("/{code}", response_model=Category, status_code=200)
def delete(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("TAXO", "CATEGORIES", can_edit=True))
) -> Category:
    """
    Delete a category (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique category code to delete
    """
    category = session.get(Category, code)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if already inactive
    if not category.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Category with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    category.is_active = False
    category.updated_at = datetime.utcnow()

    session.add(category)
    session.commit()
    session.refresh(category)
    logger.info(f"Category deactivated (logical delete): {code}")
    return category
