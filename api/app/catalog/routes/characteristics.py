import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Characteristic, CharacteristicCreate, CharacteristicUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/characteristics", tags=["characteristics"])


@router.post("/", response_model=Characteristic, status_code=201)
def create_characteristic(characteristic: CharacteristicCreate, session: Session = Depends(get_db_session)) -> Characteristic:
    """
    Crear una nueva característica.
    
    - **code**: Código único de la característica (requerido)
    - **name**: Nombre de la característica (requerido)
    - **type**: Tipo de característica (requerido)
    - **status**: Estado de la característica (requerido)
    - **description**: Descripción opcional
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el código no exista
    existing_characteristic = session.get(Characteristic, characteristic.code)
    if existing_characteristic:
        raise HTTPException(
            status_code=409,
            detail=f"Characteristic with code '{characteristic.code}' already exists"
        )
    
    try:
        db_characteristic = Characteristic.model_validate(characteristic)
        session.add(db_characteristic)
        session.commit()
        session.refresh(db_characteristic)
        logger.info(f"Characteristic created: {characteristic.code}")
        return db_characteristic
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating characteristic {characteristic.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Characteristic with code '{characteristic.code}' already exists"
        )


@router.get("/", response_model=List[Characteristic])
def list_characteristics(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Characteristic]:
    """
    Listar todas las características con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    characteristics = session.exec(select(Characteristic).offset(skip).limit(limit).order_by(Characteristic.name)).all()
    return characteristics


@router.get("/{characteristic_code}", response_model=Characteristic)
def get_characteristic(characteristic_code: str, session: Session = Depends(get_db_session)) -> Characteristic:
    """
    Obtener una característica por su código.
    
    - **characteristic_code**: Código único de la característica
    """
    characteristic = session.get(Characteristic, characteristic_code)
    if not characteristic:
        raise HTTPException(status_code=404, detail="Characteristic not found")
    return characteristic


@router.put("/{characteristic_code}", response_model=Characteristic)
def update_characteristic(characteristic_code: str, characteristic_update: CharacteristicUpdate, session: Session = Depends(get_db_session)) -> Characteristic:
    """
    Actualizar una característica existente.
    
    - **characteristic_code**: Código único de la característica a actualizar
    - Solo se actualizan los campos proporcionados
    """
    characteristic = session.get(Characteristic, characteristic_code)
    if not characteristic:
        raise HTTPException(status_code=404, detail="Characteristic not found")

    update_data = characteristic_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(characteristic, key, value)
    
    # Actualizar timestamp
    characteristic.updated_at = datetime.utcnow()

    session.add(characteristic)
    session.commit()
    session.refresh(characteristic)
    logger.info(f"Characteristic updated: {characteristic_code}")
    return characteristic


@router.delete("/{characteristic_code}", response_model=Characteristic, status_code=200)
def delete_characteristic(characteristic_code: str, session: Session = Depends(get_db_session)) -> Characteristic:
    """
    Eliminar una característica (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **characteristic_code**: Código único de la característica a eliminar
    """
    characteristic = session.get(Characteristic, characteristic_code)
    if not characteristic:
        raise HTTPException(status_code=404, detail="Characteristic not found")
    
    # Verificar si ya está inactiva
    if not characteristic.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Characteristic with code '{characteristic_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    characteristic.is_active = False
    characteristic.updated_at = datetime.utcnow()
    
    session.add(characteristic)
    session.commit()
    session.refresh(characteristic)
    logger.info(f"Characteristic deactivated (logical delete): {characteristic_code}")
    return characteristic

