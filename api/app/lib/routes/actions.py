import logging
from typing import List
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Action, ActionCreate, ActionUpdate, Asset
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.get("/", response_model=List[Action])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=False))
) -> List[Action]:
    """
    List all actions with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    actions = session.exec(select(Action).where(Action.is_active == True)
                           .offset(skip).limit(limit)
                           .order_by(Action.created_at.desc())).all()
    return actions


@router.get("/{id}", response_model=Action)
def get(
    id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=False))
) -> Action:
    """
    Get an action by its ID.

    - **id**: Unique action ID
    """
    action = session.get(Action, id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    elif not action.is_active:
        raise HTTPException(status_code=400, detail=f"Action with id '{id}' is inactive")
    return action


@router.post("/", response_model=Action, status_code=201)
def create(
    action: ActionCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=True))
) -> Action:
    """
    Create a new action.

    - **asset**: Asset code (required)
    - **user_id**: User ID (required)
    - **type**: Action type (required)
    - **content**: Action content (optional)
    - **reference**: Action reference (optional)
    - **parent**: Parent action ID (optional)
    - **details**: Action details in JSON format (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the asset exists
    asset = session.get(Asset, action.asset)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with code '{action.asset}' does not exist"
        )

    # Validate that the parent action exists if provided
    if action.parent:
        parent_action = session.get(Action, action.parent)
        if not parent_action:
            raise HTTPException(
                status_code=400,
                detail=f"Parent action with id '{action.parent}' does not exist"
            )

    try:
        # Convertir details a JSON string si es dict
        action_data = action.model_dump()
        if action_data.get('details') and isinstance(action_data['details'], dict):
            action_data['details'] = json.dumps(action_data['details'])

        db = Action.model_validate(action_data)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Action created: {db.id}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating action: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error creating action"
        )


@router.put("/{id}", response_model=Action)
def update(
    id: int, action_update: ActionUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=True))
) -> Action:
    """
    Update an existing action.

    - **id**: Unique action ID to update
    - Only provided fields are updated
    """
    action = session.get(Action, id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    # Validate that the parent action exists if provided
    if action_update.parent is not None:
        parent_action = session.get(Action, action_update.parent)
        if not parent_action:
            raise HTTPException(
                status_code=400,
                detail=f"Parent action with id '{action_update.parent}' does not exist"
            )

    update_data = action_update.model_dump(exclude_unset=True)
    # Convertir details a JSON string si es dict
    if 'details' in update_data and isinstance(update_data['details'], dict):
        update_data['details'] = json.dumps(update_data['details'])

    for key, value in update_data.items():
        setattr(action, key, value)

    # Update timestamp
    action.updated_at = datetime.utcnow()

    session.add(action)
    session.commit()
    session.refresh(action)
    logger.info(f"Action updated: {id}")
    return action


@router.delete("/{id}", response_model=Action, status_code=200)
def delete(
    id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=True))
) -> Action:
    """
    Delete an action (logical delete).

    Performs a logical delete by setting is_active=False instead of removing the record.

    - **id**: Unique action ID to delete
    """
    action = session.get(Action, id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    # Check if already inactive
    if not action.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Action with id '{id}' is already inactive"
        )

    # Logical delete: update is_active to False
    action.is_active = False
    action.updated_at = datetime.utcnow()

    session.add(action)
    session.commit()
    session.refresh(action)
    logger.info(f"Action deactivated (logical delete): {id}")
    return action
