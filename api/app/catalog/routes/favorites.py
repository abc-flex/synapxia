import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Favorite, FavoriteCreate, FavoriteUpdate, Asset
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.post("/", response_model=Favorite, status_code=201)
def create_favorite(favorite: FavoriteCreate, session: Session = Depends(get_db_session)) -> Favorite:
    """
    Crear un nuevo favorito.
    
    - **user_id**: ID del usuario (requerido)
    - **asset**: Código del activo (requerido)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el activo exista
    asset = session.get(Asset, favorite.asset)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with code '{favorite.asset}' does not exist"
        )
    
    # Validar que el favorito no exista ya
    existing_favorite = session.exec(
        select(Favorite).where(
            Favorite.user_id == favorite.user_id,
            Favorite.asset == favorite.asset
        )
    ).first()
    if existing_favorite:
        raise HTTPException(
            status_code=409,
            detail=f"Favorite with user_id '{favorite.user_id}' and asset '{favorite.asset}' already exists"
        )
    
    try:
        db_favorite = Favorite.model_validate(favorite)
        session.add(db_favorite)
        session.commit()
        session.refresh(db_favorite)
        logger.info(f"Favorite created: {favorite.user_id}/{favorite.asset}")
        return db_favorite
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating favorite {favorite.user_id}/{favorite.asset}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Favorite with user_id '{favorite.user_id}' and asset '{favorite.asset}' already exists"
        )


@router.get("/", response_model=List[Favorite])
def list_favorites(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Favorite]:
    """
    Listar todos los favoritos con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    favorites = session.exec(select(Favorite).offset(skip).limit(limit).order_by(Favorite.user_id, Favorite.asset)).all()
    return favorites


@router.get("/{user_id}/{asset_code}", response_model=Favorite)
def get_favorite(user_id: int, asset_code: str, session: Session = Depends(get_db_session)) -> Favorite:
    """
    Obtener un favorito por su usuario y activo.
    
    - **user_id**: ID del usuario
    - **asset_code**: Código del activo
    """
    favorite = session.exec(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.asset == asset_code
        )
    ).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return favorite


@router.put("/{user_id}/{asset_code}", response_model=Favorite)
def update_favorite(
    user_id: int, asset_code: str, favorite_update: FavoriteUpdate, session: Session = Depends(get_db_session)
) -> Favorite:
    """
    Actualizar un favorito existente.
    
    - **user_id**: ID del usuario
    - **asset_code**: Código del activo
    - Solo se actualizan los campos proporcionados
    """
    favorite = session.exec(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.asset == asset_code
        )
    ).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    update_data = favorite_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(favorite, key, value)
    
    # Actualizar timestamp
    favorite.updated_at = datetime.utcnow()

    session.add(favorite)
    session.commit()
    session.refresh(favorite)
    logger.info(f"Favorite updated: {user_id}/{asset_code}")
    return favorite


@router.delete("/{user_id}/{asset_code}", response_model=Favorite, status_code=200)
def delete_favorite(user_id: int, asset_code: str, session: Session = Depends(get_db_session)) -> Favorite:
    """
    Eliminar un favorito (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **user_id**: ID del usuario
    - **asset_code**: Código del activo
    """
    favorite = session.exec(
        select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.asset == asset_code
        )
    ).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    # Verificar si ya está inactivo
    if not favorite.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Favorite with user_id '{user_id}' and asset '{asset_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    favorite.is_active = False
    favorite.updated_at = datetime.utcnow()
    
    session.add(favorite)
    session.commit()
    session.refresh(favorite)
    logger.info(f"Favorite deactivated (logical delete): {user_id}/{asset_code}")
    return favorite

