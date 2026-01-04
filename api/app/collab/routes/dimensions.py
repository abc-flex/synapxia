import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Dimension, DimensionCreate, DimensionUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dimensions", tags=["dimensions"])


@router.post("/", response_model=Dimension, status_code=201)
def create_dimension(dimension: DimensionCreate, session: Session = Depends(get_db_session)) -> Dimension:
    """
    Crear una nueva dimensión.
    
    - **code**: Código único de la dimensión (requerido)
    - **name**: Nombre de la dimensión (requerido)
    - **description**: Descripción opcional
    - **scale**: Código de la escala (lista) (opcional)
    - **unit**: Unidad de medida (opcional)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el código no exista
    existing_dimension = session.get(Dimension, dimension.code)
    if existing_dimension:
        raise HTTPException(
            status_code=409,
            detail=f"Dimension with code '{dimension.code}' already exists"
        )
    
    try:
        db_dimension = Dimension.model_validate(dimension)
        session.add(db_dimension)
        session.commit()
        session.refresh(db_dimension)
        logger.info(f"Dimension created: {dimension.code}")
        return db_dimension
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating dimension {dimension.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Dimension with code '{dimension.code}' already exists"
        )


@router.get("/", response_model=List[Dimension])
def list_dimensions(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Dimension]:
    """
    Listar todas las dimensiones con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    dimensions = session.exec(select(Dimension).offset(skip).limit(limit).order_by(Dimension.name)).all()
    return dimensions


@router.get("/{dimension_code}", response_model=Dimension)
def get_dimension(dimension_code: str, session: Session = Depends(get_db_session)) -> Dimension:
    """
    Obtener una dimensión por su código.
    
    - **dimension_code**: Código único de la dimensión
    """
    dimension = session.get(Dimension, dimension_code)
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    return dimension


@router.put("/{dimension_code}", response_model=Dimension)
def update_dimension(dimension_code: str, dimension_update: DimensionUpdate, session: Session = Depends(get_db_session)) -> Dimension:
    """
    Actualizar una dimensión existente.
    
    - **dimension_code**: Código único de la dimensión a actualizar
    - Solo se actualizan los campos proporcionados
    """
    dimension = session.get(Dimension, dimension_code)
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")

    update_data = dimension_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dimension, key, value)
    
    # Actualizar timestamp
    dimension.updated_at = datetime.utcnow()

    session.add(dimension)
    session.commit()
    session.refresh(dimension)
    logger.info(f"Dimension updated: {dimension_code}")
    return dimension


@router.delete("/{dimension_code}", response_model=Dimension, status_code=200)
def delete_dimension(dimension_code: str, session: Session = Depends(get_db_session)) -> Dimension:
    """
    Eliminar una dimensión (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **dimension_code**: Código único de la dimensión a eliminar
    """
    dimension = session.get(Dimension, dimension_code)
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    
    # Verificar si ya está inactiva
    if not dimension.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Dimension with code '{dimension_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    dimension.is_active = False
    dimension.updated_at = datetime.utcnow()
    
    session.add(dimension)
    session.commit()
    session.refresh(dimension)
    logger.info(f"Dimension deactivated (logical delete): {dimension_code}")
    return dimension

