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
    Create a new team.

    - **code**: Unique team code (required)
    - **name**: Team name (required)
    - **description**: Optional description
    - **lead**: Team leader ID (optional)
    - **chat_channel_url**: Chat channel URL (optional)
    - **kanban_board_url**: Kanban board URL (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
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
    List all teams with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    teams = session.exec(select(Team).offset(
        skip).limit(limit).order_by(Team.name)).all()
    return teams


@router.get("/{team_code}", response_model=Team)
def get_team(team_code: str, session: Session = Depends(get_db_session)) -> Team:
    """
    Get a team by its code.

    - **team_code**: Unique team code
    """
    team = session.get(Team, team_code)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.put("/{team_code}", response_model=Team)
def update_team(team_code: str, team_update: TeamUpdate, session: Session = Depends(get_db_session)) -> Team:
    """
    Update an existing team.

    - **team_code**: Unique team code to update
    - Only provided fields are updated
    """
    team = session.get(Team, team_code)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    update_data = team_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(team, key, value)

    # Update timestamp
    team.updated_at = datetime.utcnow()

    session.add(team)
    session.commit()
    session.refresh(team)
    logger.info(f"Team updated: {team_code}")
    return team


@router.delete("/{team_code}", response_model=Team, status_code=200)
def delete_team(team_code: str, session: Session = Depends(get_db_session)) -> Team:
    """
    Delete a team (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **team_code**: Unique team code to delete
    """
    team = session.get(Team, team_code)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if already inactive
    if not team.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Team with code '{team_code}' is already inactive"
        )

    # Logical delete: update is_active to False
    team.is_active = False
    team.updated_at = datetime.utcnow()

    session.add(team)
    session.commit()
    session.refresh(team)
    logger.info(f"Team deactivated (logical delete): {team_code}")
    return team
