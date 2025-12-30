import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import ListItem, ListItemCreate, ListItemUpdate, List as ListModel
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/list_items", tags=["list_items"])


@router.post("/", response_model=ListItem, status_code=201)
def create_list_item(item_data: ListItemCreate, session: Session = Depends(get_db_session)) -> ListItem:
    """
    Crear un nuevo elemento de lista.
    
    - **list**: Código de la lista (requerido)
    - **value**: Valor del elemento (requerido)
    - **label**: Etiqueta del elemento (requerido)
    - **sort_order**: Orden de visualización (default: 0)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que la lista exista
    list_obj = session.get(ListModel, item_data.list)
    if not list_obj:
        raise HTTPException(
            status_code=400,
            detail=f"List with code '{item_data.list}' does not exist"
        )
    
    # Validar que el elemento no exista ya
    existing_item = session.exec(
        select(ListItem).where(
            ListItem.list == item_data.list,
            ListItem.value == item_data.value
        )
    ).first()
    if existing_item:
        raise HTTPException(
            status_code=409,
            detail=f"List item with list '{item_data.list}' and value '{item_data.value}' already exists"
        )
    
    try:
        db_item = ListItem.model_validate(item_data)
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        logger.info(f"List item created: {item_data.list}/{item_data.value}")
        return db_item
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating list item {item_data.list}/{item_data.value}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"List item with list '{item_data.list}' and value '{item_data.value}' already exists"
        )


@router.get("/", response_model=List[ListItem])
def list_list_items(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[ListItem]:
    """
    Listar todos los elementos de lista con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    items = session.exec(select(ListItem).offset(skip).limit(limit).order_by(ListItem.list, ListItem.sort_order, ListItem.value)).all()
    return items


@router.get("/{list_code}/{value}", response_model=ListItem)
def get_list_item(list_code: str, value: str, session: Session = Depends(get_db_session)) -> ListItem:
    """
    Obtener un elemento de lista por su código de lista y valor.
    
    - **list_code**: Código de la lista
    - **value**: Valor del elemento
    """
    item = session.exec(select(ListItem).where(ListItem.list == list_code, ListItem.value == value)).first()
    if not item:
        raise HTTPException(status_code=404, detail="List item not found")
    return item


@router.put("/{list_code}/{value}", response_model=ListItem)
def update_list_item(list_code: str, value: str, item_update: ListItemUpdate, session: Session = Depends(get_db_session)) -> ListItem:
    """
    Actualizar un elemento de lista existente.
    
    - **list_code**: Código de la lista
    - **value**: Valor del elemento
    - Solo se actualizan los campos proporcionados
    """
    item = session.exec(select(ListItem).where(ListItem.list == list_code, ListItem.value == value)).first()
    if not item:
        raise HTTPException(status_code=404, detail="List item not found")

    update_data = item_update.model_dump(exclude_unset=True)
    for key, val in update_data.items():  # Corregido: usar 'val' en lugar de 'value'
        setattr(item, key, val)
    
    # Actualizar timestamp
    item.updated_at = datetime.utcnow()

    session.add(item)
    session.commit()
    session.refresh(item)
    logger.info(f"List item updated: {list_code}/{value}")
    return item


@router.delete("/{list_code}/{value}", response_model=ListItem, status_code=200)
def delete_list_item(list_code: str, value: str, session: Session = Depends(get_db_session)) -> ListItem:
    """
    Eliminar un elemento de lista (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **list_code**: Código de la lista
    - **value**: Valor del elemento
    """
    item = session.exec(select(ListItem).where(ListItem.list == list_code, ListItem.value == value)).first()
    if not item:
        raise HTTPException(status_code=404, detail="List item not found")
    
    # Verificar si ya está inactivo
    if not item.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"List item with list '{list_code}' and value '{value}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    item.is_active = False
    item.updated_at = datetime.utcnow()
    
    session.add(item)
    session.commit()
    session.refresh(item)
    logger.info(f"List item deactivated (logical delete): {list_code}/{value}")
    return item