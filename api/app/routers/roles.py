import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Role, RoleCreate, RoleUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.post("/", response_model=Role, status_code=201)
def create_role(
    role: RoleCreate, session: Session = Depends(get_db_session)
) -> Role:
    """
    Crear un nuevo rol.
    
    - **code**: Código único del rol (requerido)
    - **name**: Nombre del rol (requerido)
    - **description**: Descripción opcional del rol
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el código no exista
    existing_role = session.get(Role, role.code)
    if existing_role:
        raise HTTPException(
            status_code=409,
            detail=f"Role with code '{role.code}' already exists"
        )
    
    try:
        db_role = Role.model_validate(role)
        session.add(db_role)
        session.commit()
        session.refresh(db_role)
        logger.info(f"Role created: {role.code}")
        return db_role
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating role {role.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Role with code '{role.code}' already exists"
        )


@router.get("/", response_model=List[Role])
def list_roles(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db_session),
) -> List[Role]:
    """
    Listar todos los roles con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    roles = session.exec(select(Role).offset(skip).limit(limit).order_by(Role.name)).all()
    return roles


@router.get("/{role_code}", response_model=Role)
def get_role(role_code: str, session: Session = Depends(get_db_session)) -> Role:
    """
    Obtener un rol por su código.
    
    - **role_code**: Código único del rol
    """
    role = session.get(Role, role_code)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.put("/{role_code}", response_model=Role)
def update_role(
    role_code: str, role_update: RoleUpdate, session: Session = Depends(get_db_session)
) -> Role:
    """
    Actualizar un rol existente.
    
    - **role_code**: Código único del rol a actualizar
    - Solo se actualizan los campos proporcionados
    """
    role = session.get(Role, role_code)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    update_data = role_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(role, key, value)
    
    # Actualizar timestamp
    role.updated_at = datetime.utcnow()

    session.add(role)
    session.commit()
    session.refresh(role)
    logger.info(f"Role updated: {role_code}")
    return role


@router.delete("/{role_code}", response_model=Role, status_code=200)
def delete_role(role_code: str, session: Session = Depends(get_db_session)) -> Role:
    """
    Eliminar un rol (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **role_code**: Código único del rol a eliminar
    """
    role = session.get(Role, role_code)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Verificar si ya está inactivo
    if not role.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Role with code '{role_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    role.is_active = False
    role.updated_at = datetime.utcnow()
    
    session.add(role)
    session.commit()
    session.refresh(role)
    logger.info(f"Role deactivated (logical delete): {role_code}")
    return role
