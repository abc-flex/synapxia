import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Privilege, PrivilegeCreate, PrivilegeUpdate, Role, Option
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/privileges", tags=["privileges"])


@router.post("/", response_model=Privilege, status_code=201)
def create_privilege(privilege: PrivilegeCreate, session: Session = Depends(get_db_session)) -> Privilege:
    """
    Crear un nuevo privilegio.
    
    - **role**: Código del rol (requerido)
    - **module**: Código del módulo (requerido)
    - **option**: Código de la opción (requerido)
    - **can_edit**: Indica si puede editar (default: True)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el rol exista
    role = session.get(Role, privilege.role)
    if not role:
        raise HTTPException(
            status_code=400,
            detail=f"Role with code '{privilege.role}' does not exist"
        )
    
    # Validar que la opción exista
    option = session.exec(
        select(Option).where(
            Option.module == privilege.module,
            Option.code == privilege.option
        )
    ).first()
    if not option:
        raise HTTPException(
            status_code=400,
            detail=f"Option with module '{privilege.module}' and code '{privilege.option}' does not exist"
        )
    
    # Validar que el privilegio no exista ya
    existing_privilege = session.exec(
        select(Privilege).where(
            Privilege.role == privilege.role,
            Privilege.module == privilege.module,
            Privilege.option == privilege.option
        )
    ).first()
    if existing_privilege:
        raise HTTPException(
            status_code=409,
            detail=f"Privilege with role '{privilege.role}', module '{privilege.module}' and option '{privilege.option}' already exists"
        )
    
    try:
        db_privilege = Privilege.model_validate(privilege)
        session.add(db_privilege)
        session.commit()
        session.refresh(db_privilege)
        logger.info(f"Privilege created: {privilege.role}/{privilege.module}/{privilege.option}")
        return db_privilege
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating privilege {privilege.role}/{privilege.module}/{privilege.option}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Privilege with role '{privilege.role}', module '{privilege.module}' and option '{privilege.option}' already exists"
        )


@router.get("/", response_model=List[Privilege])
def list_privileges(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Privilege]:
    """
    Listar todos los privilegios con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    privileges = session.exec(select(Privilege).offset(skip).limit(limit).order_by(Privilege.role, Privilege.module, Privilege.option)).all()
    return privileges


@router.get("/{role_code}/{module_code}/{option_code}", response_model=Privilege)
def get_privilege(role_code: str, module_code: str, option_code: str, session: Session = Depends(get_db_session)) -> Privilege:
    """
    Obtener un privilegio por su rol, módulo y opción.
    
    - **role_code**: Código del rol
    - **module_code**: Código del módulo
    - **option_code**: Código de la opción
    """
    privilege = session.exec(
        select(Privilege).where(
            Privilege.role == role_code,
            Privilege.module == module_code,
            Privilege.option == option_code
        )
    ).first()
    if not privilege:
        raise HTTPException(status_code=404, detail="Privilege not found")
    return privilege


@router.put("/{role_code}/{module_code}/{option_code}", response_model=Privilege)
def update_privilege(
    role_code: str, module_code: str, option_code: str, privilege_update: PrivilegeUpdate, session: Session = Depends(get_db_session)
) -> Privilege:
    """
    Actualizar un privilegio existente.
    
    - **role_code**: Código del rol
    - **module_code**: Código del módulo
    - **option_code**: Código de la opción
    - Solo se actualizan los campos proporcionados
    """
    privilege = session.exec(
        select(Privilege).where(
            Privilege.role == role_code,
            Privilege.module == module_code,
            Privilege.option == option_code
        )
    ).first()
    if not privilege:
        raise HTTPException(status_code=404, detail="Privilege not found")

    update_data = privilege_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(privilege, key, value)
    
    # Actualizar timestamp
    privilege.updated_at = datetime.utcnow()

    session.add(privilege)
    session.commit()
    session.refresh(privilege)
    logger.info(f"Privilege updated: {role_code}/{module_code}/{option_code}")
    return privilege


@router.delete("/{role_code}/{module_code}/{option_code}", response_model=Privilege, status_code=200)
def delete_privilege(role_code: str, module_code: str, option_code: str, session: Session = Depends(get_db_session)) -> Privilege:
    """
    Eliminar un privilegio (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **role_code**: Código del rol
    - **module_code**: Código del módulo
    - **option_code**: Código de la opción
    """
    privilege = session.exec(
        select(Privilege).where(
            Privilege.role == role_code,
            Privilege.module == module_code,
            Privilege.option == option_code
        )
    ).first()
    if not privilege:
        raise HTTPException(status_code=404, detail="Privilege not found")
    
    # Verificar si ya está inactivo
    if not privilege.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Privilege with role '{role_code}', module '{module_code}' and option '{option_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    privilege.is_active = False
    privilege.updated_at = datetime.utcnow()
    
    session.add(privilege)
    session.commit()
    session.refresh(privilege)
    logger.info(f"Privilege deactivated (logical delete): {role_code}/{module_code}/{option_code}")
    return privilege

