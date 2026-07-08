import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import (
    Action, ActionCreate, ActionUpdate, Asset, VoteRequest, VoteTally,
    ParticipationCreate, AnswerCreate, DiscussionItem, HistoryEntry,
    NotificationItem, WorkflowStage,
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
    except IntegrityError:
        session.rollback()
        logger.error(
            "Integrity error setting vote: user=%s asset=%s",
            payload.user_id, payload.asset)
        raise HTTPException(
            status_code=409,
            detail="Could not register vote due to a data conflict"
        )
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
    try:
        actions_service.set_vote(session, user_id, asset_id, None)
    except IntegrityError:
        session.rollback()
        logger.error(
            "Integrity error clearing vote: user=%s asset=%s",
            user_id, asset_id)
        raise HTTPException(
            status_code=409,
            detail="Could not clear vote due to a data conflict"
        )
    tally = actions_service.get_vote_tally(session, asset_id, user_id)
    return VoteTally(asset=asset_id, **tally)


# ---------------------------------------------------------------------------
# Foro (HU-LI06) — comments / questions / answers as actions. Registered BEFORE
# the composite `/{id}` route so the literal segments aren't parsed as an id.
# Logical delete reuses the existing DELETE /api/actions/{id}.
# ---------------------------------------------------------------------------


@router.get("/discussion/asset/{asset_id}", response_model=List[DiscussionItem])
def get_discussion(
    asset_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=False))
) -> List[DiscussionItem]:
    """
    The discussion (comments + questions + answers) for an asset, oldest first,
    each enriched with the author's username. Answers carry the question id in
    ``parent`` so the client can thread them.

    - **asset_id**: Asset id
    """
    if not actions_service.asset_exists(session, asset_id):
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    return actions_service.list_discussion(session, asset_id)


@router.post("/comments", response_model=DiscussionItem, status_code=201)
def add_comment(
    payload: ParticipationCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=True))
) -> DiscussionItem:
    """Post a comment on an asset (an ``actions`` row of type COMMENT)."""
    return _create_participation(
        session, "comment",
        lambda: actions_service.add_comment(
            session, payload.user_id, payload.asset, payload.content),
        payload.asset)


@router.post("/questions", response_model=DiscussionItem, status_code=201)
def add_question(
    payload: ParticipationCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=True))
) -> DiscussionItem:
    """Ask a question on an asset (an ``actions`` row of type QUESTION)."""
    return _create_participation(
        session, "question",
        lambda: actions_service.add_question(
            session, payload.user_id, payload.asset, payload.content),
        payload.asset)


@router.post("/answers", response_model=DiscussionItem, status_code=201)
def add_answer(
    payload: AnswerCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=True))
) -> DiscussionItem:
    """Answer a question (``actions`` row of type ANSWER, ``parent`` = question
    id). The parent must be an active question on the same asset (else 400)."""
    return _create_participation(
        session, "answer",
        lambda: actions_service.add_answer(
            session, payload.user_id, payload.asset, payload.content,
            payload.parent),
        payload.asset)


def _create_participation(session, label, create_fn, asset_id):
    """Shared body for the comment/question/answer POST handlers: validate the
    asset, run the service create, and map ValueError→400 / IntegrityError→409
    (never a raw 500). Returns the enriched discussion item."""
    if not actions_service.asset_exists(session, asset_id):
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    try:
        action = create_fn()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error adding %s on asset=%s", label, asset_id)
        raise HTTPException(
            status_code=409,
            detail=f"Could not add {label} due to a data conflict"
        )
    return actions_service.discussion_item(session, action)


# ---------------------------------------------------------------------------
# History (HU-LI10) — read-only activity timeline over the asset's actions.
# Registered BEFORE the composite `/{id}` route so "history" isn't parsed as an
# action id.
# ---------------------------------------------------------------------------


@router.get("/history/asset/{asset_id}", response_model=List[HistoryEntry])
def get_history(
    asset_id: int, skip: int = 0, limit: int = 100,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=False))
) -> List[HistoryEntry]:
    """
    The activity timeline for an asset (newest first): every active action
    (votes, comments, questions, answers, and any review-workflow actions) plus
    a synthetic CREATED marker, each enriched with the actor's username.

    - **asset_id**: Asset id
    - **skip** / **limit**: pagination over the timeline
    """
    if not actions_service.asset_exists(session, asset_id):
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    entries = actions_service.get_asset_history(session, asset_id)
    return entries[skip:skip + limit]


@router.get("/workflow/asset/{asset_id}", response_model=Optional[WorkflowStage])
def get_workflow_stage(
    asset_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=False))
) -> Optional[WorkflowStage]:
    """
    The asset's current review stage: the latest review-workflow action
    (PROPOSAL/REVIEW/PUBLICATION/…) with its ``workflow_status`` (assigned /
    notified / finished). Read-only and distinct from ``asset.status``.
    Returns ``null`` when the asset has no workflow actions.

    - **asset_id**: Asset id
    """
    if not actions_service.asset_exists(session, asset_id):
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    stage = actions_service.get_workflow_stage(session, asset_id)
    return stage


# ---------------------------------------------------------------------------
# Notifications (HU-LI11) — workflow assignments for the current user (from JWT).
# Registered BEFORE the composite `/{id}` route so "notifications" isn't parsed
# as an action id. Transitions insert successive workflow_status rows.
# ---------------------------------------------------------------------------


def _own_notification(session: Session, action_id: int, current: User) -> Action:
    """Load a workflow action that belongs to the current user, or 404. Keeps
    one user from advancing another user's assignment (per-user isolation)."""
    action = session.get(Action, action_id)
    if (
        not action
        or action.user_id != current.id
        or action.type not in actions_service.NOTIFICATION_TYPES
    ):
        raise HTTPException(status_code=404, detail="Notification not found")
    return action


@router.get("/notifications", response_model=List[NotificationItem])
def get_notifications(
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=False))
) -> List[NotificationItem]:
    """
    The current user's open workflow notifications (newest first): the latest row
    of each (asset, type) assignment thread whose status is ASSIGNED or NOTIFIED.
    The user is taken from the JWT — a user only ever sees their own.
    """
    return actions_service.list_notifications(session, current.id)


@router.get("/reviews", response_model=List[NotificationItem])
def get_review_requests(
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=False))
) -> List[NotificationItem]:
    """
    The current user's open REVIEW assignments (newest first) — a persistent,
    browsable queue backing the "Review Requests" page, independent of whatever
    has been opened/dismissed in the notification bell.
    """
    return actions_service.list_review_requests(session, current.id)


@router.get("/modifications", response_model=List[NotificationItem])
def get_pending_modifications(
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=False))
) -> List[NotificationItem]:
    """
    The current user's open MODIFICATION assignments (newest first) — a
    persistent, browsable queue backing the "My Modifications" page.
    """
    return actions_service.list_pending_modifications(session, current.id)


@router.post("/notifications/{id}/notified", response_model=Action)
def mark_notification_notified(
    id: int, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=True))
) -> Action:
    """
    Mark an ASSIGNED notification as seen (NOTIFIED) — removes the bold style.
    Idempotent: a no-op if the thread is already past ASSIGNED.

    - **id**: The notification's latest action id (from GET /notifications)
    """
    action = _own_notification(session, id, current)
    try:
        return actions_service.mark_notified(session, action)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Could not update the notification due to a data conflict")


@router.post("/notifications/{id}/dismiss", response_model=Action)
def dismiss_notification(
    id: int, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ACTIONS", can_edit=True))
) -> Action:
    """
    Dismiss a notification (insert a FINISHED row) — removes it from the list.
    Only PUBLICATION/REJECTION (informational) notifications can be dismissed;
    REVIEW/MODIFICATION must be resolved via review/resubmit instead (400).

    - **id**: The notification's latest action id (from GET /notifications)
    """
    action = _own_notification(session, id, current)
    try:
        return actions_service.dismiss_notification(session, action)
    except actions_service.NotificationNotDismissible as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Could not dismiss the notification due to a data conflict")


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
