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
    Crear una nueva categoría.
    
    - **code**: Código único de la categoría (requerido)
    - **name**: Nombre de la categoría (requerido)
    - **description**: Descripción opcional
    - **parent**: Código de la categoría padre (opcional)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el código no exista
    existing_category = session.get(Category, category.code)
    if existing_category:
        raise HTTPException(
            status_code=409,
            detail=f"Category with code '{category.code}' already exists"
        )
    
    # Validar que la categoría padre exista si se proporciona
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
    Listar todas las categorías con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    categories = session.exec(select(Category).offset(skip).limit(limit).order_by(Category.name)).all()
    return categories


@router.get("/{category_code}", response_model=Category)
def get_category(category_code: str, session: Session = Depends(get_db_session)) -> Category:
    """
    Obtener una categoría por su código.
    
    - **category_code**: Código único de la categoría
    """
    category = session.get(Category, category_code)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_code}", response_model=Category)
def update_category(category_code: str, category_update: CategoryUpdate, session: Session = Depends(get_db_session)) -> Category:
    """
    Actualizar una categoría existente.
    
    - **category_code**: Código único de la categoría a actualizar
    - Solo se actualizan los campos proporcionados
    """
    category = session.get(Category, category_code)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Validar que la categoría padre exista si se proporciona
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
    
    # Actualizar timestamp
    category.updated_at = datetime.utcnow()

    session.add(category)
    session.commit()
    session.refresh(category)
    logger.info(f"Category updated: {category_code}")
    return category


@router.delete("/{category_code}", response_model=Category, status_code=200)
def delete_category(category_code: str, session: Session = Depends(get_db_session)) -> Category:
    """
    Eliminar una categoría (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **category_code**: Código único de la categoría a eliminar
    """
    category = session.get(Category, category_code)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Verificar si ya está inactiva
    if not category.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Category with code '{category_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    category.is_active = False
    category.updated_at = datetime.utcnow()
    
    session.add(category)
    session.commit()
    session.refresh(category)
    logger.info(f"Category deactivated (logical delete): {category_code}")
    return category

