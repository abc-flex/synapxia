import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Unit, UnitCreate, UnitUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/units", tags=["units"])


@router.post("/", response_model=Unit, status_code=201)
def create_unit(unit: UnitCreate, session: Session = Depends(get_db_session)) -> Unit:
    """
    Crear una nueva unidad organizacional.
    
    - **code**: Código único de la unidad (requerido)
    - **name**: Nombre de la unidad (requerido)
    - **description**: Descripción opcional
    - **type**: Tipo de unidad (opcional)
    - **parent**: Código de la unidad padre (opcional)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el código no exista
    existing_unit = session.get(Unit, unit.code)
    if existing_unit:
        raise HTTPException(
            status_code=409,
            detail=f"Unit with code '{unit.code}' already exists"
        )
    
    # Validar que la unidad padre exista si se proporciona
    if unit.parent_unit:
        parent_unit = session.get(Unit, unit.parent_unit)
        if not parent_unit:
            raise HTTPException(
                status_code=400,
                detail=f"Parent unit with code '{unit.parent_unit}' does not exist"
            )
    
    try:
        db_unit = Unit.model_validate(unit)
        session.add(db_unit)
        session.commit()
        session.refresh(db_unit)
        logger.info(f"Unit created: {unit.code}")
        return db_unit
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating unit {unit.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Unit with code '{unit.code}' already exists"
        )


@router.get("/", response_model=List[Unit])
def list_units(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Unit]:
    """
    Listar todas las unidades con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    units = session.exec(select(Unit).offset(skip).limit(limit).order_by(Unit.name)).all()
    return units


@router.get("/{unit_code}", response_model=Unit)
def get_unit(unit_code: str, session: Session = Depends(get_db_session)) -> Unit:
    """
    Obtener una unidad por su código.
    
    - **unit_code**: Código único de la unidad
    """
    unit = session.get(Unit, unit_code)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.put("/{unit_code}", response_model=Unit)
def update_unit(unit_code: str, unit_update: UnitUpdate, session: Session = Depends(get_db_session)) -> Unit:
    """
    Actualizar una unidad existente.
    
    - **unit_code**: Código único de la unidad a actualizar
    - Solo se actualizan los campos proporcionados
    """
    unit = session.get(Unit, unit_code)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Validar que la unidad padre exista si se proporciona
    if unit_update.parent_unit is not None:
        parent_unit = session.get(Unit, unit_update.parent_unit)
        if not parent_unit:
            raise HTTPException(
                status_code=400,
                detail=f"Parent unit with code '{unit_update.parent_unit}' does not exist"
            )

    update_data = unit_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(unit, key, value)
    
    # Actualizar timestamp
    unit.updated_at = datetime.utcnow()

    session.add(unit)
    session.commit()
    session.refresh(unit)
    logger.info(f"Unit updated: {unit_code}")
    return unit


@router.delete("/{unit_code}", response_model=Unit, status_code=200)
def delete_unit(unit_code: str, session: Session = Depends(get_db_session)) -> Unit:
    """
    Eliminar una unidad (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **unit_code**: Código único de la unidad a eliminar
    """
    unit = session.get(Unit, unit_code)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    # Verificar si ya está inactiva
    if not unit.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Unit with code '{unit_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    unit.is_active = False
    unit.updated_at = datetime.utcnow()
    
    session.add(unit)
    session.commit()
    session.refresh(unit)
    logger.info(f"Unit deactivated (logical delete): {unit_code}")
    return unit

