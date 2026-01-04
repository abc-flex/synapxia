import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Assignment, AssignmentCreate, AssignmentUpdate, Team
from ...admin.internal.models import Role
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@router.post("/", response_model=Assignment, status_code=201)
def create_assignment(assignment: AssignmentCreate, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Crear una nueva asignación.
    
    - **team**: Código del equipo (opcional)
    - **user_id**: ID del usuario (requerido)
    - **role**: Código del rol (requerido)
    - **observation**: Observación (opcional)
    - **valid_from**: Fecha de inicio de validez (opcional, default: ahora)
    - **valid_to**: Fecha de fin de validez (opcional)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el equipo exista si se proporciona
    if assignment.team:
        team = session.get(Team, assignment.team)
        if not team:
            raise HTTPException(
                status_code=400,
                detail=f"Team with code '{assignment.team}' does not exist"
            )
    
    # Validar que el rol exista
    role = session.get(Role, assignment.role)
    if not role:
        raise HTTPException(
            status_code=400,
            detail=f"Role with code '{assignment.role}' does not exist"
        )
    
    # Si no se proporciona valid_from, usar ahora
    assignment_data = assignment.model_dump()
    if not assignment_data.get('valid_from'):
        assignment_data['valid_from'] = datetime.utcnow()
    
    try:
        db_assignment = Assignment.model_validate(assignment_data)
        session.add(db_assignment)
        session.commit()
        session.refresh(db_assignment)
        logger.info(f"Assignment created: {db_assignment.id}")
        return db_assignment
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating assignment: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error creating assignment"
        )


@router.get("/", response_model=List[Assignment])
def list_assignments(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Assignment]:
    """
    Listar todas las asignaciones con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    assignments = session.exec(select(Assignment).offset(skip).limit(limit).order_by(Assignment.created_at.desc())).all()
    return assignments


@router.get("/{assignment_id}", response_model=Assignment)
def get_assignment(assignment_id: int, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Obtener una asignación por su ID.
    
    - **assignment_id**: ID único de la asignación
    """
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.put("/{assignment_id}", response_model=Assignment)
def update_assignment(assignment_id: int, assignment_update: AssignmentUpdate, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Actualizar una asignación existente.
    
    - **assignment_id**: ID único de la asignación a actualizar
    - Solo se actualizan los campos proporcionados
    """
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Validar que el equipo exista si se proporciona
    if assignment_update.team is not None:
        team = session.get(Team, assignment_update.team)
        if not team:
            raise HTTPException(
                status_code=400,
                detail=f"Team with code '{assignment_update.team}' does not exist"
            )
    
    # Validar que el rol exista si se proporciona
    if assignment_update.role is not None:
        role = session.get(Role, assignment_update.role)
        if not role:
            raise HTTPException(
                status_code=400,
                detail=f"Role with code '{assignment_update.role}' does not exist"
            )

    update_data = assignment_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(assignment, key, value)
    
    # Actualizar timestamp
    assignment.updated_at = datetime.utcnow()

    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    logger.info(f"Assignment updated: {assignment_id}")
    return assignment


@router.delete("/{assignment_id}", response_model=Assignment, status_code=200)
def delete_assignment(assignment_id: int, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Eliminar una asignación (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **assignment_id**: ID único de la asignación a eliminar
    """
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Verificar si ya está inactiva
    if not assignment.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Assignment with id '{assignment_id}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    assignment.is_active = False
    assignment.updated_at = datetime.utcnow()
    
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    logger.info(f"Assignment deactivated (logical delete): {assignment_id}")
    return assignment

