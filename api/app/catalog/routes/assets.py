import logging
from typing import List
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Asset, AssetCreate, AssetUpdate, Category
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.post("/", response_model=Asset, status_code=201)
def create_asset(asset: AssetCreate, session: Session = Depends(get_db_session)) -> Asset:
    """
    Crear un nuevo activo.
    
    - **code**: Código único del activo (requerido)
    - **name**: Nombre del activo (requerido)
    - **type**: Tipo de activo (requerido)
    - **status**: Estado del activo (requerido)
    - **visibility**: Visibilidad del activo (requerido)
    - **description**: Descripción opcional
    - **category**: Código de la categoría (opcional)
    - **reference**: Referencia del activo (opcional)
    - **tags**: Tags del activo en formato JSON (opcional)
    - **details**: Detalles del activo en formato JSON (opcional)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el código no exista
    existing_asset = session.get(Asset, asset.code)
    if existing_asset:
        raise HTTPException(
            status_code=409,
            detail=f"Asset with code '{asset.code}' already exists"
        )
    
    # Validar que la categoría exista si se proporciona
    if asset.category:
        category = session.get(Category, asset.category)
        if not category:
            raise HTTPException(
                status_code=400,
                detail=f"Category with code '{asset.category}' does not exist"
            )
    
    try:
        # Convertir tags y details a JSON string si son dict
        asset_data = asset.model_dump()
        if asset_data.get('tags') and isinstance(asset_data['tags'], dict):
            asset_data['tags'] = json.dumps(asset_data['tags'])
        if asset_data.get('details') and isinstance(asset_data['details'], dict):
            asset_data['details'] = json.dumps(asset_data['details'])
        
        db_asset = Asset.model_validate(asset_data)
        session.add(db_asset)
        session.commit()
        session.refresh(db_asset)
        logger.info(f"Asset created: {asset.code}")
        return db_asset
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating asset {asset.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Asset with code '{asset.code}' already exists"
        )


@router.get("/", response_model=List[Asset])
def list_assets(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Asset]:
    """
    Listar todos los activos con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    assets = session.exec(select(Asset).offset(skip).limit(limit).order_by(Asset.name)).all()
    return assets


@router.get("/{asset_code}", response_model=Asset)
def get_asset(asset_code: str, session: Session = Depends(get_db_session)) -> Asset:
    """
    Obtener un activo por su código.
    
    - **asset_code**: Código único del activo
    """
    asset = session.get(Asset, asset_code)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/{asset_code}", response_model=Asset)
def update_asset(asset_code: str, asset_update: AssetUpdate, session: Session = Depends(get_db_session)) -> Asset:
    """
    Actualizar un activo existente.
    
    - **asset_code**: Código único del activo a actualizar
    - Solo se actualizan los campos proporcionados
    """
    asset = session.get(Asset, asset_code)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Validar que la categoría exista si se proporciona
    if asset_update.category is not None:
        category = session.get(Category, asset_update.category)
        if not category:
            raise HTTPException(
                status_code=400,
                detail=f"Category with code '{asset_update.category}' does not exist"
            )

    update_data = asset_update.model_dump(exclude_unset=True)
    # Convertir tags y details a JSON string si son dict
    if 'tags' in update_data and isinstance(update_data['tags'], dict):
        update_data['tags'] = json.dumps(update_data['tags'])
    if 'details' in update_data and isinstance(update_data['details'], dict):
        update_data['details'] = json.dumps(update_data['details'])
    
    for key, value in update_data.items():
        setattr(asset, key, value)
    
    # Actualizar timestamp
    asset.updated_at = datetime.utcnow()

    session.add(asset)
    session.commit()
    session.refresh(asset)
    logger.info(f"Asset updated: {asset_code}")
    return asset


@router.delete("/{asset_code}", response_model=Asset, status_code=200)
def delete_asset(asset_code: str, session: Session = Depends(get_db_session)) -> Asset:
    """
    Eliminar un activo (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **asset_code**: Código único del activo a eliminar
    """
    asset = session.get(Asset, asset_code)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Verificar si ya está inactivo
    if not asset.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with code '{asset_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    asset.is_active = False
    asset.updated_at = datetime.utcnow()
    
    session.add(asset)
    session.commit()
    session.refresh(asset)
    logger.info(f"Asset deactivated (logical delete): {asset_code}")
    return asset

