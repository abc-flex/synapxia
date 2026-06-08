import logging
from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import ListItem, ListItemCreate, ListItemUpdate, List as ListModel, ItemTranslation, User
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import check_privilege

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/list_items", tags=["list_items"])


@router.get("/", response_model=List[ListItem])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LIST_ITEMS", can_edit=False))
) -> List[ListItem]:
    """
    Listar todos los elementos de lista con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    items = session.exec(select(ListItem).where(ListItem.is_active == True)
                         .offset(skip).limit(limit)
                         .order_by(ListItem.list, ListItem.sort_order, ListItem.value)).all()
    return items


@router.get("/list/{list_code}", response_model=List[ListItem])
def get_by_list(
    list_code: str, 
    session: Session = Depends(get_db_session)
) -> List[ListItem]:
    """
    Obtener todos los elementos de una lista específica.
    
    - **list_code**: Código de la lista para filtrar
    """
    # Validar primero si la lista existe (opcional, pero recomendado por integridad)
    list_exists = session.get(ListModel, list_code)
    if not list_exists:
        raise HTTPException(
            status_code=404, 
            detail=f"List with code '{list_code}' does not exist"
        )
    items = session.exec(
        select(ListItem)
        .where(ListItem.list == list_code)
        .order_by(ListItem.sort_order, ListItem.label)
    ).all()
    return items

@router.get("/{list_code}/{value}", response_model=ListItem)
def get(
    list_code: str, value: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LIST_ITEMS", can_edit=False))
) -> ListItem:
    """
    Obtener un elemento de lista por su código de lista y valor.
    
    - **list_code**: Código de la lista
    - **value**: Valor del elemento
    """
    item = session.exec(select(ListItem).where(ListItem.list == list_code, ListItem.value == value)).first()
    if not item:
        raise HTTPException(status_code=404, detail="List item not found")
    elif not item.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"List item with list '{list_code}' and value '{value}' is inactive"
        )
    return item


@router.get("/list/{list_code}/with-translations", response_model=List[Dict[str, Any]])
def get_with_translations(
    list_code: str,
    session: Session = Depends(get_db_session)
) -> List[Dict[str, Any]]:
    """
    Obtener todos los elementos de una lista con sus traducciones (maestro-detalle).
    
    - **list_code**: Código de la lista para filtrar
    """
    # Validar que la lista existe
    list_exists = session.get(ListModel, list_code)
    if not list_exists:
        raise HTTPException(
            status_code=404,
            detail=f"List with code '{list_code}' does not exist"
        )
    
    # Obtener todos los items activos
    items = session.exec(
        select(ListItem)
        .where(ListItem.list == list_code, ListItem.is_active == True)
        .order_by(ListItem.sort_order, ListItem.label)
    ).all()
    
    # Construir respuesta con traducciones
    result = []
    for item in items:
        # Obtener traducciones para este item
        translations = session.exec(
            select(ItemTranslation)
            .where(
                ItemTranslation.list == list_code,
                ItemTranslation.value == item.value,
                ItemTranslation.is_active == True
            )
            .order_by(ItemTranslation.lang)
        ).all()
        
        # Construir lista de traducciones
        translations_list = [
            {
                "lang": t.lang,
                "label": t.label,
                "is_active": t.is_active
            }
            for t in translations
        ]
        
        # Agregar item con traducciones
        result.append({
            "list": item.list,
            "value": item.value,
            "label": item.label,
            "sort_order": item.sort_order,
            "is_active": item.is_active,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "translations": translations_list
        })
    
    return result


@router.get("/{list_code}/{value}/with-translations", response_model=Dict[str, Any])
def get_single_with_translations(
    list_code: str,
    value: str,
    session: Session = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Obtener un elemento de lista con todas sus traducciones (maestro-detalle).
    
    - **list_code**: Código de la lista
    - **value**: Valor del elemento
    """
    # Obtener el item
    item = session.exec(
        select(ListItem)
        .where(ListItem.list == list_code, ListItem.value == value)
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="List item not found")
    elif not item.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"List item with list '{list_code}' and value '{value}' is inactive"
        )
    
    # Obtener traducciones para este item
    translations = session.exec(
        select(ItemTranslation)
        .where(
            ItemTranslation.list == list_code,
            ItemTranslation.value == value,
            ItemTranslation.is_active == True
        )
        .order_by(ItemTranslation.lang)
    ).all()
    
    # Construir lista de traducciones
    translations_list = [
        {
            "lang": t.lang,
            "label": t.label,
            "is_active": t.is_active
        }
        for t in translations
    ]
    
    return {
        "list": item.list,
        "value": item.value,
        "label": item.label,
        "sort_order": item.sort_order,
        "is_active": item.is_active,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "translations": translations_list
    }


@router.post("/", response_model=ListItem, status_code=201)
def create(
    item_data: ListItemCreate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LIST_ITEMS", can_edit=True))
) -> ListItem:
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


@router.put("/{list_code}/{value}", response_model=ListItem)
def update(
    list_code: str, value: str, item_update: ListItemUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LIST_ITEMS", can_edit=True))
) -> ListItem:
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
    for key, val in update_data.items():
        setattr(item, key, val)
    
    # Actualizar timestamp
    item.updated_at = datetime.utcnow()

    session.add(item)
    session.commit()
    session.refresh(item)
    logger.info(f"List item updated: {list_code}/{value}")
    return item


@router.delete("/{list_code}/{value}", response_model=ListItem, status_code=200)
def delete(
    list_code: str, value: str, session: Session = Depends(get_db_session),
    _: User = Depends(lambda: check_privilege("ADMIN", "LIST_ITEMS", can_edit=True))
) -> ListItem:
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

