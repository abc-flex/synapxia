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
    Crear una nueva lista.
    
    - **code**: Código único de la lista (requerido)
    - **name**: Nombre de la lista (requerido)
    - **type**: Tipo de lista (requerido)
    - **description**: Descripción opcional
    - **module**: Código del módulo asociado (opcional)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el código no exista
    existing_list = session.get(ListModel, list_data.code)
    if existing_list:
        raise HTTPException(
            status_code=409,
            detail=f"List with code '{list_data.code}' already exists"
        )
    
    # Validar que el módulo exista si se proporciona
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
    Listar todas las listas con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    lists = session.exec(select(ListModel).offset(skip).limit(limit).order_by(ListModel.name)).all()
    return lists


@router.get("/{list_code}", response_model=ListModel)
def get_list(list_code: str, session: Session = Depends(get_db_session)) -> ListModel:
    """
    Obtener una lista por su código.
    
    - **list_code**: Código único de la lista
    """
    list_item = session.get(ListModel, list_code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")
    return list_item


@router.put("/{list_code}", response_model=ListModel)
def update_list(list_code: str, list_update: ListUpdate, session: Session = Depends(get_db_session)) -> ListModel:
    """
    Actualizar una lista existente.
    
    - **list_code**: Código único de la lista a actualizar
    - Solo se actualizan los campos proporcionados
    """
    list_item = session.get(ListModel, list_code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")

    # Validar que el módulo exista si se proporciona
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
    
    # Actualizar timestamp
    list_item.updated_at = datetime.utcnow()

    session.add(list_item)
    session.commit()
    session.refresh(list_item)
    logger.info(f"List updated: {list_code}")
    return list_item


@router.delete("/{list_code}", response_model=ListModel, status_code=200)
def delete_list(list_code: str, session: Session = Depends(get_db_session)) -> ListModel:
    """
    Eliminar una lista (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **list_code**: Código único de la lista a eliminar
    """
    list_item = session.get(ListModel, list_code)
    if not list_item:
        raise HTTPException(status_code=404, detail="List not found")
    
    # Verificar si ya está inactiva
    if not list_item.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"List with code '{list_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    list_item.is_active = False
    list_item.updated_at = datetime.utcnow()
    
    session.add(list_item)
    session.commit()
    session.refresh(list_item)
    logger.info(f"List deactivated (logical delete): {list_code}")
    return list_item