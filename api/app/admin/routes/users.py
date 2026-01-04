import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import User, UserCreate, UserUpdate, Role, Unit
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/", response_model=User, status_code=201)
def create_user(user: UserCreate, session: Session = Depends(get_db_session)) -> User:
    """
    Crear un nuevo usuario.
    
    - **username**: Nombre de usuario único (requerido)
    - **email**: Correo electrónico único (requerido)
    - **password_hash**: Hash de la contraseña (requerido)
    - **first_name**: Nombre (requerido)
    - **last_name**: Apellido (requerido)
    - **menu_role**: Código del rol (requerido)
    - **unit**: Código de la unidad (requerido)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el username no exista
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        raise HTTPException(
            status_code=409,
            detail=f"User with username '{user.username}' already exists"
        )
    
    # Validar que el email no exista
    existing_email = session.exec(select(User).where(User.email == user.email)).first()
    if existing_email:
        raise HTTPException(
            status_code=409,
            detail=f"User with email '{user.email}' already exists"
        )
    
    # Validar que el rol exista
    role = session.get(Role, user.menu_role)
    if not role:
        raise HTTPException(
            status_code=400,
            detail=f"Role with code '{user.menu_role}' does not exist"
        )
    
    # Validar que la unidad exista
    unit = session.get(Unit, user.unit)
    if not unit:
        raise HTTPException(
            status_code=400,
            detail=f"Unit with code '{user.unit}' does not exist"
        )
    
    try:
        db_user = User.model_validate(user)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        logger.info(f"User created: {user.username}")
        return db_user
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating user {user.username}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"User with username '{user.username}' or email '{user.email}' already exists"
        )


@router.get("/", response_model=List[User])
def list_users(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[User]:
    """
    Listar todos los usuarios con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    users = session.exec(select(User).offset(skip).limit(limit).order_by(User.username)).all()
    return users


@router.get("/{user_id}", response_model=User)
def get_user(user_id: int, session: Session = Depends(get_db_session)) -> User:
    """
    Obtener un usuario por su ID.
    
    - **user_id**: ID único del usuario
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=User)
def update_user(user_id: int, user_update: UserUpdate, session: Session = Depends(get_db_session)) -> User:
    """
    Actualizar un usuario existente.
    
    - **user_id**: ID único del usuario a actualizar
    - Solo se actualizan los campos proporcionados
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validar que el email no exista si se está actualizando
    if user_update.email is not None and user_update.email != user.email:
        existing_email = session.exec(select(User).where(User.email == user_update.email)).first()
        if existing_email:
            raise HTTPException(
                status_code=409,
                detail=f"User with email '{user_update.email}' already exists"
            )
    
    # Validar que el rol exista si se proporciona
    if user_update.menu_role is not None:
        role = session.get(Role, user_update.menu_role)
        if not role:
            raise HTTPException(
                status_code=400,
                detail=f"Role with code '{user_update.menu_role}' does not exist"
            )
    
    # Validar que la unidad exista si se proporciona
    if user_update.unit is not None:
        unit = session.get(Unit, user_update.unit)
        if not unit:
            raise HTTPException(
                status_code=400,
                detail=f"Unit with code '{user_update.unit}' does not exist"
            )

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    # Actualizar timestamp
    user.updated_at = datetime.utcnow()

    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"User updated: {user_id}")
    return user


@router.delete("/{user_id}", response_model=User, status_code=200)
def delete_user(user_id: int, session: Session = Depends(get_db_session)) -> User:
    """
    Eliminar un usuario (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **user_id**: ID único del usuario a eliminar
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verificar si ya está inactivo
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"User with id '{user_id}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    user.is_active = False
    user.updated_at = datetime.utcnow()
    
    session.add(user)
    session.commit()
    session.refresh(user)
    logger.info(f"User deactivated (logical delete): {user_id}")
    return user

