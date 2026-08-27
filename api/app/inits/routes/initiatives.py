import logging
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy import cast, String

from ..internal.models import Initiative
from ..internal.dependencies import get_db_session
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/initiatives", tags=["initiatives"])

# Read-only router: listing/selecting existing initiatives, needed so an asset
# can be related to one (Asset Management's "Related Inits" tab, backed by
# asset_inits). Full initiative CRUD is future scope — see the note in
# api/app/inits/internal/models.py.


class InitiativeBasic(SQLModel):
    value: str
    label: str


@router.get("/select", response_model=List[InitiativeBasic])
def get_select(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=False))
) -> List[InitiativeBasic]:
    """
    Lightweight list of active initiatives for UI dropdowns: value = id, label = name.
    """
    rows = session.exec(
        select(
            cast(Initiative.id, String).label("value"),
            Initiative.name.label("label"),
        )
        .where(Initiative.is_active == True)
        .order_by(Initiative.name)
    ).all()
    return rows


@router.get("/", response_model=List[Initiative])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=False))
) -> List[Initiative]:
    """
    List all initiatives with pagination (active only).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    initiatives = session.exec(
        select(Initiative).where(Initiative.is_active == True)
        .offset(skip).limit(limit)
        .order_by(Initiative.name)
    ).all()
    return initiatives


@router.get("/{init_id}", response_model=Initiative)
def get(
    init_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=False))
) -> Initiative:
    """
    Get an initiative by its id.

    - **init_id**: Initiative id
    """
    initiative = session.get(Initiative, init_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    elif not initiative.is_active:
        raise HTTPException(status_code=400, detail=f"Initiative with id '{init_id}' is inactive")
    return initiative
