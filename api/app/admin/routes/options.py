import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Option, OptionCreate, OptionUpdate, Module
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/options", tags=["options"])


@router.post("/", response_model=Option, status_code=201)
def create_option(option: OptionCreate, session: Session = Depends(get_db_session)) -> Option:
    """
    Crear una nueva opción.
    
    - **module**: Código del módulo (requerido)
    - **code**: Código único de la opción (requerido)
    - **name**: Nombre de la opción (requerido)
    - **type**: Tipo de opción (requerido)
    - **description**: Descripción opcional
    - **path**: Ruta de la opción (opcional)
    - **icon**: Icono de la opción (opcional)
    - **sort_order**: Orden de visualización (default: 0)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el módulo exista
    module = session.get(Module, option.module)
    if not module:
        raise HTTPException(
            status_code=400,
            detail=f"Module with code '{option.module}' does not exist"
        )
    
    # Validar que la opción no exista ya
    existing_option = session.exec(
        select(Option).where(
            Option.module == option.module,
            Option.code == option.code
        )
    ).first()
    if existing_option:
        raise HTTPException(
            status_code=409,
            detail=f"Option with module '{option.module}' and code '{option.code}' already exists"
        )
    
    try:
        db_option = Option.model_validate(option)
        session.add(db_option)
        session.commit()
        session.refresh(db_option)
        logger.info(f"Option created: {option.module}/{option.code}")
        return db_option
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating option {option.module}/{option.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Option with module '{option.module}' and code '{option.code}' already exists"
        )


@router.get("/", response_model=List[Option])
def list_options(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Option]:
    """
    Listar todas las opciones con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    options = session.exec(select(Option).offset(skip).limit(limit).order_by(Option.module, Option.sort_order, Option.name)).all()
    return options


@router.get("/{module_code}/{option_code}", response_model=Option)
def get_option(module_code: str, option_code: str, session: Session = Depends(get_db_session)) -> Option:
    """
    Obtener una opción por su módulo y código.
    
    - **module_code**: Código del módulo
    - **option_code**: Código de la opción
    """
    option = session.exec(
        select(Option).where(Option.module == module_code, Option.code == option_code)
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    return option


@router.put("/{module_code}/{option_code}", response_model=Option)
def update_option(
    module_code: str, option_code: str, option_update: OptionUpdate, session: Session = Depends(get_db_session)
) -> Option:
    """
    Actualizar una opción existente.
    
    - **module_code**: Código del módulo
    - **option_code**: Código de la opción
    - Solo se actualizan los campos proporcionados
    """
    option = session.exec(
        select(Option).where(Option.module == module_code, Option.code == option_code)
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    update_data = option_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(option, key, value)
    
    # Actualizar timestamp
    option.updated_at = datetime.utcnow()

    session.add(option)
    session.commit()
    session.refresh(option)
    logger.info(f"Option updated: {module_code}/{option_code}")
    return option


@router.delete("/{module_code}/{option_code}", response_model=Option, status_code=200)
def delete_option(module_code: str, option_code: str, session: Session = Depends(get_db_session)) -> Option:
    """
    Eliminar una opción (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **module_code**: Código del módulo
    - **option_code**: Código de la opción
    """
    option = session.exec(
        select(Option).where(Option.module == module_code, Option.code == option_code)
    ).first()
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    
    # Verificar si ya está inactiva
    if not option.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Option with module '{module_code}' and code '{option_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    option.is_active = False
    option.updated_at = datetime.utcnow()
    
    session.add(option)
    session.commit()
    session.refresh(option)
    logger.info(f"Option deactivated (logical delete): {module_code}/{option_code}")
    return option

