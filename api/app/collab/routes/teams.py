import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Team, TeamCreate, TeamUpdate
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.post("/", response_model=Team, status_code=201)
def create_team(team: TeamCreate, session: Session = Depends(get_db_session)) -> Team:
    """
    Crear un nuevo equipo.
    
    - **code**: Código único del equipo (requerido)
    - **name**: Nombre del equipo (requerido)
    - **description**: Descripción opcional
    - **lead**: ID del líder del equipo (opcional)
    - **chat_channel_url**: URL del canal de chat (opcional)
    - **kanban_board_url**: URL del tablero Kanban (opcional)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el código no exista
    existing_team = session.get(Team, team.code)
    if existing_team:
        raise HTTPException(
            status_code=409,
            detail=f"Team with code '{team.code}' already exists"
        )
    
    try:
        db_team = Team.model_validate(team)
        session.add(db_team)
        session.commit()
        session.refresh(db_team)
        logger.info(f"Team created: {team.code}")
        return db_team
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating team {team.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Team with code '{team.code}' already exists"
        )


@router.get("/", response_model=List[Team])
def list_teams(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Team]:
    """
    Listar todos los equipos con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    teams = session.exec(select(Team).offset(skip).limit(limit).order_by(Team.name)).all()
    return teams


@router.get("/{team_code}", response_model=Team)
def get_team(team_code: str, session: Session = Depends(get_db_session)) -> Team:
    """
    Obtener un equipo por su código.
    
    - **team_code**: Código único del equipo
    """
    team = session.get(Team, team_code)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.put("/{team_code}", response_model=Team)
def update_team(team_code: str, team_update: TeamUpdate, session: Session = Depends(get_db_session)) -> Team:
    """
    Actualizar un equipo existente.
    
    - **team_code**: Código único del equipo a actualizar
    - Solo se actualizan los campos proporcionados
    """
    team = session.get(Team, team_code)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    update_data = team_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(team, key, value)
    
    # Actualizar timestamp
    team.updated_at = datetime.utcnow()

    session.add(team)
    session.commit()
    session.refresh(team)
    logger.info(f"Team updated: {team_code}")
    return team


@router.delete("/{team_code}", response_model=Team, status_code=200)
def delete_team(team_code: str, session: Session = Depends(get_db_session)) -> Team:
    """
    Eliminar un equipo (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **team_code**: Código único del equipo a eliminar
    """
    team = session.get(Team, team_code)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verificar si ya está inactivo
    if not team.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Team with code '{team_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    team.is_active = False
    team.updated_at = datetime.utcnow()
    
    session.add(team)
    session.commit()
    session.refresh(team)
    logger.info(f"Team deactivated (logical delete): {team_code}")
    return team

