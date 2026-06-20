import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy.exc import IntegrityError

from ..internal.models import Criteria, CriteriaCreate, CriteriaUpdate
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/criterias", tags=["criterias"])

#Model for module select options
class CriteriaBasic(SQLModel):
    value: str
    label: str

@router.get("/select", response_model=List[CriteriaBasic])
def get_list(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "CRITERIAS", can_edit=False))
) -> List[CriteriaBasic]:
    """
    Returns a criterias list optimized for selects with value (code) and label (name). 
    Only active criterias.
    """
    statement = (
        select(
            Criteria.code.label("value"), 
            Criteria.name.label("label")
        )
        .where(Criteria.is_active == True)
        .order_by(Criteria.name)
    )
    return session.exec(statement).all()


@router.get("/", response_model=List[Criteria])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "CRITERIAS", can_edit=False))
) -> List[Criteria]:
    """
    List all criterias with pagination (*Only active criterias).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    criterias = session.exec(select(Criteria).where(Criteria.is_active == True)
                            .offset(skip).limit(limit)
                            .order_by(Criteria.name)).all()
    return criterias


@router.get("/{code}", response_model=Criteria)
def get(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "CRITERIAS", can_edit=False))
) -> Criteria:
    """
    Get a criteria by its code.

    - **code**: Unique criteria code
    """
    criteria = session.get(Criteria, code)
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")
    elif not criteria.is_active:
        raise HTTPException(status_code=400, detail=f"Criteria with code '{code}' is inactive")
    return criteria


@router.post("/", response_model=Criteria, status_code=201)
def create(
    criteria: CriteriaCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "CRITERIAS", can_edit=True))
) -> Criteria:
    """
    Create a new criteria.

    - **code**: Unique criteria code (required)
    - **name**: Criteria name (required)
    - **list**: Criteria list (required)
    - **description**: Optional description
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing = session.get(Criteria, criteria.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Criteria with code '{criteria.code}' already exists"
        )

    # If list is empty, "null" or "none", convert to None
    if criteria.list is not None and criteria.list in ["", "null", "none"]:
        criteria.list = None

    try:
        db = Criteria.model_validate(criteria)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Criteria created: {criteria.code}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating criteria {criteria.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Criteria with code '{criteria.code}' already exists"
        )


@router.put("/{code}", response_model=Criteria)
def update(
    code: str, criteria_update: CriteriaUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "CRITERIAS", can_edit=True))
) -> Criteria:
    """
    Update an existing criteria.

    - **code**: Unique criteria code to update
    - Only provided fields are updated
    """
    criteria = session.get(Criteria, code)
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")

    update_data = criteria_update.model_dump(exclude_unset=True)
    
    # Validate list field - if list is empty, "null" or "none", convert to None
    if "list" in update_data and update_data["list"] in ["", "null", "none"]:
        update_data["list"] = None
    
    for key, value in update_data.items():
        setattr(criteria, key, value)

    # Update timestamp
    criteria.updated_at = datetime.utcnow()

    session.add(criteria)
    session.commit()
    session.refresh(criteria)
    logger.info(f"Criteria updated: {code}")
    return criteria


@router.delete("/{code}", response_model=Criteria, status_code=200)
def delete(
    code: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "CRITERIAS", can_edit=True))
) -> Criteria:
    """
    Delete a criteria (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique criteria code to delete
    """
    criteria = session.get(Criteria, code)
    if not criteria:
        raise HTTPException(status_code=404, detail="Criteria not found")

    # Check if already inactive
    if not criteria.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Criteria with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    criteria.is_active = False
    criteria.updated_at = datetime.utcnow()

    session.add(criteria)
    session.commit()
    session.refresh(criteria)
    logger.info(
        f"Criteria deactivated (logical delete): {code}")
    return criteria
