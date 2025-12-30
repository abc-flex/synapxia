import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Module, ModuleCreate, ModuleUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/modules", tags=["modules"])


@router.post("/", response_model=Module, status_code=201)
def create_module(module: ModuleCreate, session: Session = Depends(get_db_session)) -> Module:
    """
    Crear un nuevo módulo.
    
    - **code**: Código único del módulo (requerido)
    - **name**: Nombre del módulo (requerido)
    - **description**: Descripción opcional del módulo
    - **sort_order**: Orden de visualización (default: 0)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el código no exista
    existing_module = session.get(Module, module.code)
    if existing_module:
        raise HTTPException(
            status_code=409,
            detail=f"Module with code '{module.code}' already exists"
        )
    
    try:
        db_module = Module.model_validate(module)
        session.add(db_module)
        session.commit()
        session.refresh(db_module)
        logger.info(f"Module created: {module.code}")
        return db_module
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating module {module.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Module with code '{module.code}' already exists"
        )


@router.get("/", response_model=List[Module])
def list_modules(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Module]:
    """
    Listar todos los módulos con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    modules = session.exec(select(Module).offset(skip).limit(limit).order_by(Module.sort_order, Module.name)).all()
    return modules


@router.get("/{module_code}", response_model=Module)
def get_module(module_code: str, session: Session = Depends(get_db_session)) -> Module:
    """
    Obtener un módulo por su código.
    
    - **module_code**: Código único del módulo
    """
    module = session.get(Module, module_code)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module


@router.put("/{module_code}", response_model=Module)
def update_module(module_code: str, module_update: ModuleUpdate, session: Session = Depends(get_db_session)) -> Module:
    """
    Actualizar un módulo existente.
    
    - **module_code**: Código único del módulo a actualizar
    - Solo se actualizan los campos proporcionados
    """
    module = session.get(Module, module_code)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    update_data = module_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(module, key, value)
    
    # Actualizar timestamp
    module.updated_at = datetime.utcnow()

    session.add(module)
    session.commit()
    session.refresh(module)
    logger.info(f"Module updated: {module_code}")
    return module


@router.delete("/{module_code}", response_model=Module, status_code=200)
def delete_module(module_code: str, session: Session = Depends(get_db_session)) -> Module:
    """
    Eliminar un módulo (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **module_code**: Código único del módulo a eliminar
    """
    module = session.get(Module, module_code)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Verificar si ya está inactivo
    if not module.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Module with code '{module_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    module.is_active = False
    module.updated_at = datetime.utcnow()
    
    session.add(module)
    session.commit()
    session.refresh(module)
    logger.info(f"Module deactivated (logical delete): {module_code}")
    return module