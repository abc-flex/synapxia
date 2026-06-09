import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import ItemTranslation, ItemTranslationCreate, ItemTranslationUpdate, ListItem, User
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/item_translations", tags=["item_translations"])


@router.get("/", response_model=List[ItemTranslation])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "ITEM_TRANSLATIONS", can_edit=False))
) -> List[ItemTranslation]:
    """
    Listar todas las traducciones de elementos con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    translations = session.exec(
        select(ItemTranslation)
        .where(ItemTranslation.is_active == True)
        .offset(skip)
        .limit(limit)
        .order_by(ItemTranslation.list, ItemTranslation.value, ItemTranslation.lang)
    ).all()
    return translations


@router.get("/list/{list_code}", response_model=List[ItemTranslation])
def get_by_list(
    list_code: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "ITEM_TRANSLATIONS", can_edit=False))
) -> List[ItemTranslation]:
    """
    Obtener todas las traducciones de una lista específica.
    
    - **list_code**: Código de la lista para filtrar
    """
    translations = session.exec(
        select(ItemTranslation)
        .where(ItemTranslation.list == list_code)
        .order_by(ItemTranslation.value, ItemTranslation.lang)
    ).all()
    return translations


@router.get("/list/{list_code}/value/{value}", response_model=List[ItemTranslation])
def get_by_item(
    list_code: str,
    value: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "ITEM_TRANSLATIONS", can_edit=False))
) -> List[ItemTranslation]:
    """
    Obtener todas las traducciones de un elemento de lista específico.
    
    - **list_code**: Código de la lista
    - **value**: Valor del elemento
    """
    # Validar que el item existe
    item_exists = session.exec(
        select(ListItem).where(
            ListItem.list == list_code,
            ListItem.value == value
        )
    ).first()
    if not item_exists:
        raise HTTPException(
            status_code=404,
            detail=f"List item with list '{list_code}' and value '{value}' does not exist"
        )
    
    translations = session.exec(
        select(ItemTranslation)
        .where(
            ItemTranslation.list == list_code,
            ItemTranslation.value == value
        )
        .order_by(ItemTranslation.lang)
    ).all()
    return translations


@router.get("/list/{list_code}/value/{value}/{lang}", response_model=ItemTranslation)
def get(
    list_code: str,
    value: str,
    lang: str,
    session: Session = Depends(get_db_session)
) -> ItemTranslation:
    """
    Obtener una traducción específica de un elemento de lista.
    
    - **list_code**: Código de la lista
    - **value**: Valor del elemento
    - **lang**: Código de idioma
    """
    translation = session.exec(
        select(ItemTranslation).where(
            ItemTranslation.list == list_code,
            ItemTranslation.value == value,
            ItemTranslation.lang == lang
        )
    ).first()
    if not translation:
        raise HTTPException(
            status_code=404,
            detail=f"Translation not found for list '{list_code}', value '{value}', language '{lang}'"
        )
    elif not translation.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Translation for list '{list_code}', value '{value}', language '{lang}' is inactive"
        )
    return translation


@router.post("/", response_model=ItemTranslation, status_code=201)
def create(
    translation_data: ItemTranslationCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("ADMIN", "ITEM_TRANSLATIONS", can_edit=True))
) -> ItemTranslation:
    """
    Crear una nueva traducción para un elemento de lista.
    
    - **list**: Código de la lista (requerido)
    - **value**: Valor del elemento (requerido)
    - **lang**: Código de idioma (requerido)
    - **label**: Etiqueta traducida (requerido)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el item existe
    item_exists = session.exec(
        select(ListItem).where(
            ListItem.list == translation_data.list,
            ListItem.value == translation_data.value
        )
    ).first()
    if not item_exists:
        raise HTTPException(
            status_code=400,
            detail=f"List item with list '{translation_data.list}' and value '{translation_data.value}' does not exist"
        )
    
    # Validar que la traducción no exista ya
    existing_translation = session.exec(
        select(ItemTranslation).where(
            ItemTranslation.list == translation_data.list,
            ItemTranslation.value == translation_data.value,
            ItemTranslation.lang == translation_data.lang
        )
    ).first()
    if existing_translation:
        raise HTTPException(
            status_code=409,
            detail=f"Translation already exists for list '{translation_data.list}', value '{translation_data.value}', language '{translation_data.lang}'"
        )
    
    try:
        db_translation = ItemTranslation.model_validate(translation_data)
        session.add(db_translation)
        session.commit()
        session.refresh(db_translation)
        logger.info(f"Item translation created: {translation_data.list}/{translation_data.value}/{translation_data.lang}")
        return db_translation
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating translation {translation_data.list}/{translation_data.value}/{translation_data.lang}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Translation already exists for list '{translation_data.list}', value '{translation_data.value}', language '{translation_data.lang}'"
        )


@router.put("/list/{list_code}/value/{value}/{lang}", response_model=ItemTranslation)
def update(
    list_code: str,
    value: str,
    lang: str,
    translation_update: ItemTranslationUpdate,
    session: Session = Depends(get_db_session)
) -> ItemTranslation:
    """
    Actualizar una traducción existente.
    
    - **list_code**: Código de la lista
    - **value**: Valor del elemento
    - **lang**: Código de idioma
    - Solo se actualizan los campos proporcionados
    """
    translation = session.exec(
        select(ItemTranslation).where(
            ItemTranslation.list == list_code,
            ItemTranslation.value == value,
            ItemTranslation.lang == lang
        )
    ).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    update_data = translation_update.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(translation, key, val)
    
    # Actualizar timestamp
    translation.updated_at = datetime.utcnow()

    session.add(translation)
    session.commit()
    session.refresh(translation)
    logger.info(f"Item translation updated: {list_code}/{value}/{lang}")
    return translation


@router.delete("/list/{list_code}/value/{value}/{lang}", response_model=ItemTranslation, status_code=200)
def delete(
    list_code: str,
    value: str,
    lang: str,
    session: Session = Depends(get_db_session)
) -> ItemTranslation:
    """
    Eliminar una traducción (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **list_code**: Código de la lista
    - **value**: Valor del elemento
    - **lang**: Código de idioma
    """
    translation = session.exec(
        select(ItemTranslation).where(
            ItemTranslation.list == list_code,
            ItemTranslation.value == value,
            ItemTranslation.lang == lang
        )
    ).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    # Verificar si ya está inactivo
    if not translation.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Translation for list '{list_code}', value '{value}', language '{lang}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    translation.is_active = False
    translation.updated_at = datetime.utcnow()
    
    session.add(translation)
    session.commit()
    session.refresh(translation)
    logger.info(f"Item translation deactivated (logical delete): {list_code}/{value}/{lang}")
    return translation
