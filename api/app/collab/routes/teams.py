import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy.exc import IntegrityError

from ..internal.models import Team, TeamCreate, TeamUpdate
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/teams", tags=["teams"])

#Model for teamm select options
class TeamBasic(SQLModel):
    value: str
    label: str

@router.get("/select", response_model=List[TeamBasic])
def get_list(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "TEAMS", can_edit=False))
) -> List[TeamBasic]:
    """
    Returns a teams list optimized for selects with value (code) and label (name). 
    Only active teams.
    """
    statement = (
        select(
            Team.code.label("value"), 
            Team.name.label("label")
        )
        .where(Team.is_active == True)
        .order_by(Team.name)
    )
    return session.exec(statement).all()


@router.get("/", response_model=List[Team])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "TEAMS", can_edit=False))
) -> List[Team]:
    """
    List all teams actives with pagination (*Only active teams).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    teams = session.exec(select(Team).where(Team.is_active == True)
                         .offset(skip).limit(limit)
                         .order_by(Team.name)).all()
    return teams


@router.get("/{code}", response_model=Team)
def get(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "TEAMS", can_edit=False))
) -> Team:
    """
    Get a team by its code.

    - **code**: Unique team code
    """
    team = session.get(Team, code)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if not team.is_active:
        raise HTTPException(status_code=400, detail=f"Team with code '{code}' is inactive")
    return team


@router.post("/", response_model=Team, status_code=201)
def create(
    team: TeamCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "TEAMS", can_edit=True))
) -> Team:
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
    existing = session.get(Team, team.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Team with code '{team.code}' already exists"
        )

    try:
        db = Team.model_validate(team)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Team created: {team.code}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating team {team.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Team with code '{team.code}' already exists"
        )


@router.put("/{code}", response_model=Team)
def update(
    code: str, team_update: TeamUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "TEAMS", can_edit=True))
) -> Team:
    """
    Update an existing team.

    - **code**: Unique team code to update
    - Only provided fields are updated
    """
    team = session.get(Team, code)
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
    logger.info(f"Team updated: {code}")
    return team


@router.delete("/{code}", response_model=Team, status_code=200)
def delete(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "TEAMS", can_edit=True))
) -> Team:
    """
    Delete a team (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique team code to delete
    """
    team = session.get(Team, code)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if already inactive
    if not team.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Team with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    team.is_active = False
    team.updated_at = datetime.utcnow()

    session.add(team)
    session.commit()
    session.refresh(team)
    logger.info(f"Team deactivated (logical delete): {code}")
    return team
