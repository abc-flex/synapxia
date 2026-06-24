import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import (
    Action, ActionCreate, ActionUpdate, Asset, VoteRequest, VoteTally,
)
from ..internal import actions_service
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


# ---------------------------------------------------------------------------
# Votes (HU-LI05) — actions of type VOTE, one active vote per (user, asset).
# Registered BEFORE the composite `/{id}` route so the literal "votes" segment
# is not parsed as an integer action id.
# ---------------------------------------------------------------------------


@router.get("/votes/asset/{asset_id}", response_model=VoteTally)
def get_vote_tally(
    asset_id: int, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=False))
) -> VoteTally:
    """
    Vote tally for an asset (positive/negative counts + net score), plus the
    current user's own vote in ``my_vote``.

    - **asset_id**: Asset id
    """
    if not actions_service.asset_exists(session, asset_id):
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    tally = actions_service.get_vote_tally(session, asset_id, current.id)
    return VoteTally(asset=asset_id, **tally)


@router.get("/votes/{user_id}/{asset_id}", response_model=Action)
def get_user_vote(
    user_id: int, asset_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=False))
) -> Action:
    """
    Get a user's active vote on an asset.

    - **user_id**: User ID
    - **asset_id**: Asset id
    """
    vote = actions_service.get_user_vote(session, user_id, asset_id)
    if not vote or not vote.is_active:
        raise HTTPException(status_code=404, detail="Vote not found")
    return vote


@router.post("/votes", response_model=VoteTally, status_code=200)
def set_vote(
    payload: VoteRequest, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=True))
) -> VoteTally:
    """
    Set or flip a user's vote on an asset. Re-sending the same value toggles it
    off (clears the vote). Votes are stored as ``actions`` rows of type VOTE.

    - **user_id**: User ID (required)
    - **asset**: Asset id (required)
    - **content**: POSITIVE or NEGATIVE (required)
    """
    if not actions_service.asset_exists(session, payload.asset):
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{payload.asset}' does not exist"
        )
    try:
        actions_service.set_vote(
            session, payload.user_id, payload.asset, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    tally = actions_service.get_vote_tally(
        session, payload.asset, payload.user_id)
    return VoteTally(asset=payload.asset, **tally)


@router.delete("/votes/{user_id}/{asset_id}", response_model=VoteTally, status_code=200)
def clear_vote(
    user_id: int, asset_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=True))
) -> VoteTally:
    """
    Clear a user's vote on an asset (logical delete of the VOTE action).

    - **user_id**: User ID
    - **asset_id**: Asset id
    """
    vote = actions_service.get_user_vote(session, user_id, asset_id)
    if not vote or not vote.is_active:
        raise HTTPException(status_code=404, detail="Vote not found")
    actions_service.set_vote(session, user_id, asset_id, None)
    tally = actions_service.get_vote_tally(session, asset_id, user_id)
    return VoteTally(asset=asset_id, **tally)


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
    - **detail**: Additional detail (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the asset exists
    asset = session.get(Asset, action.asset)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{action.asset}' does not exist"
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
        db = Action.model_validate(action)
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
