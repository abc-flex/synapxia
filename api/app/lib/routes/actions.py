import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import (
    Action, ActionCreate, ActionUpdate, Asset, VoteRequest, VoteTally,
    ParticipationCreate, AnswerCreate, DiscussionItem, HistoryEntry,
    NotificationItem, NotificationFeed, AssetRequest, WorkflowStage,
    UsageRequest, UsageTally,
)
from ..internal import actions_service
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege, check_any_privilege
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
    current: User = Depends(current_active_user),
) -> VoteTally:
    """
    Vote tally for an asset (positive/negative counts + net score), plus the
    current user's own vote in ``my_vote``.

    Read access: `LIB/ASSETS` OR a privilege on the asset's own category (same
    rule as `assets.get`) — lets a catalog viewer (COLLABORATOR/REVIEWER) read
    the vote bar without holding `LIB/ASSETS`.

    - **asset_id**: Asset id
    """
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([asset.category] if asset.category else []),
    )
    tally = actions_service.get_vote_tally(session, asset_id, current.id)
    return VoteTally(asset=asset_id, **tally)


@router.get("/votes/{user_id}/{asset_id}", response_model=Action)
def get_user_vote(
    user_id: int, asset_id: int, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> Action:
    """
    Get a user's active vote on an asset.

    Read access: `LIB/ASSETS` OR a privilege on the asset's own category (same
    rule as `assets.get`).

    - **user_id**: User ID
    - **asset_id**: Asset id
    """
    asset = session.get(Asset, asset_id)
    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([asset.category] if asset and asset.category else []),
    )
    vote = actions_service.get_user_vote(session, user_id, asset_id)
    if not vote or not vote.is_active:
        raise HTTPException(status_code=404, detail="Vote not found")
    return vote


@router.post("/votes", response_model=VoteTally, status_code=200)
def set_vote(
    payload: VoteRequest, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> VoteTally:
    """
    Set or flip a user's vote on an asset. Re-sending the same value toggles it
    off (clears the vote). Votes are stored as ``actions`` rows of type VOTE.

    Write access: `LIB/ASSETS` OR a privilege on the asset's own category with
    edit intent (same rule as `assets.get`, but requiring `can_edit=True` —
    COLLABORATOR/REVIEWER hold their catalog options with edit rights, which is
    what lets them vote/participate on a published asset without holding
    `LIB/ASSETS`).

    - **user_id**: User ID (required)
    - **asset**: Asset id (required)
    - **content**: POSITIVE or NEGATIVE (required)
    """
    asset = session.get(Asset, payload.asset)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{payload.asset}' does not exist"
        )
    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([asset.category] if asset.category else []),
        can_edit=True,
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
    current: User = Depends(current_active_user),
) -> VoteTally:
    """
    Clear a user's vote on an asset (logical delete of the VOTE action).

    Write access: same rule as `set_vote` (`LIB/ASSETS` OR the asset's category
    with edit intent).

    - **user_id**: User ID
    - **asset_id**: Asset id
    """
    asset = session.get(Asset, asset_id)
    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([asset.category] if asset and asset.category else []),
        can_edit=True,
    )
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
    current: User = Depends(current_active_user),
) -> List[DiscussionItem]:
    """
    The discussion (comments + questions + answers) for an asset, oldest first,
    each enriched with the author's username. Answers carry the question id in
    ``parent`` so the client can thread them.

    Read access: `LIB/ASSETS` OR a privilege on the asset's own category (same
    rule as `assets.get`).

    - **asset_id**: Asset id
    """
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([asset.category] if asset.category else []),
    )
    return actions_service.list_discussion(session, asset_id)


@router.post("/comments", response_model=DiscussionItem, status_code=201)
def add_comment(
    payload: ParticipationCreate, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> DiscussionItem:
    """Post a comment on an asset (an ``actions`` row of type COMMENT).

    Write access: `LIB/ASSETS` OR a privilege on the asset's own category with
    edit intent (same rule as `set_vote`)."""
    return _create_participation(
        session, current, "comment",
        lambda: actions_service.add_comment(
            session, payload.user_id, payload.asset, payload.content),
        payload.asset)


@router.post("/questions", response_model=DiscussionItem, status_code=201)
def add_question(
    payload: ParticipationCreate, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> DiscussionItem:
    """Ask a question on an asset (an ``actions`` row of type QUESTION).

    Write access: same rule as `add_comment`."""
    return _create_participation(
        session, current, "question",
        lambda: actions_service.add_question(
            session, payload.user_id, payload.asset, payload.content),
        payload.asset)


@router.post("/answers", response_model=DiscussionItem, status_code=201)
def add_answer(
    payload: AnswerCreate, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> DiscussionItem:
    """Answer a question (``actions`` row of type ANSWER, ``parent`` = question
    id). The parent must be an active question on the same asset (else 400).

    Write access: same rule as `add_comment`."""
    return _create_participation(
        session, current, "answer",
        lambda: actions_service.add_answer(
            session, payload.user_id, payload.asset, payload.content,
            payload.parent),
        payload.asset)


def _create_participation(session, current_user, label, create_fn, asset_id):
    """Shared body for the comment/question/answer POST handlers: validate the
    asset, check write access (`LIB/ASSETS` OR the asset's category, with edit
    intent — same rule as `set_vote`), run the service create, and map
    ValueError→400 / IntegrityError→409 (never a raw 500). Returns the
    enriched discussion item."""
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    check_any_privilege(
        session, current_user, "LIB",
        ["ASSETS"] + ([asset.category] if asset.category else []),
        can_edit=True,
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
# Usage tracking (HU-LI07) — actions of type USAGE.
# Registered BEFORE the composite `/{id}` route so the literal "usage" segment
# is not parsed as an integer action id.
# ---------------------------------------------------------------------------


def _usage_readable_asset(session: Session, current: User, asset_id: int) -> Asset:
    """Resolve the asset and assert the caller may *read* it.

    Read intent (`can_edit=False`) on purpose, unlike votes/comments: copying a
    characteristic is consumption, not participation. A VIEW-only audience that
    can legitimately open the asset must still have its usage counted, otherwise
    the metric silently under-reports exactly the users it exists to measure.
    """
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([asset.category] if asset.category else []),
    )
    return asset


@router.get("/usage/asset/{asset_id}", response_model=UsageTally)
def get_usage_tally(
    asset_id: int, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> UsageTally:
    """
    How many times an asset has been used (copied). USAGE actions are counted
    here and deliberately excluded from the asset history timeline.

    Read access: `LIB/ASSETS` OR a privilege on the asset's own category.

    - **asset_id**: Asset id
    """
    _usage_readable_asset(session, current, asset_id)
    return UsageTally(
        asset=asset_id, count=actions_service.count_usage(session, asset_id))


@router.post("/usage", response_model=UsageTally, status_code=201)
def record_usage(
    payload: UsageRequest, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> UsageTally:
    """
    Record one usage event on an asset and return the updated count.

    Every call is its own event (no per-user dedup): the count answers "how many
    times has this asset been used?". The actor is always the authenticated
    caller — the body carries no `user_id`, so usage cannot be attributed to
    somebody else.

    - **asset**: Asset id (required)
    - **feature**: characterization feature code that was copied (optional)
    """
    _usage_readable_asset(session, current, payload.asset)
    try:
        actions_service.record_usage(
            session, current.id, payload.asset, payload.feature)
    except IntegrityError:
        session.rollback()
        logger.error(
            "Integrity error recording usage: user=%s asset=%s",
            current.id, payload.asset)
        raise HTTPException(
            status_code=409,
            detail="Could not register usage due to a data conflict"
        )
    return UsageTally(
        asset=payload.asset,
        count=actions_service.count_usage(session, payload.asset),
    )


# ---------------------------------------------------------------------------
# History (HU-LI10) — read-only activity timeline over the asset's actions.
# Registered BEFORE the composite `/{id}` route so "history" isn't parsed as an
# action id.
# ---------------------------------------------------------------------------


@router.get("/history/asset/{asset_id}", response_model=List[HistoryEntry])
def get_history(
    asset_id: int, skip: int = 0, limit: int = 100,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> List[HistoryEntry]:
    """
    The activity timeline for an asset (newest first): every active action
    (votes, comments, questions, answers, and any review-workflow actions) plus
    a synthetic CREATED marker, each enriched with the actor's username.

    Read access: `LIB/ASSETS` OR a privilege on the asset's own category (same
    rule as `assets.get`).

    - **asset_id**: Asset id
    - **skip** / **limit**: pagination over the timeline
    """
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([asset.category] if asset.category else []),
    )
    entries = actions_service.get_asset_history(session, asset_id)
    return entries[skip:skip + limit]


@router.get("/workflow/asset/{asset_id}", response_model=Optional[WorkflowStage])
def get_workflow_stage(
    asset_id: int, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> Optional[WorkflowStage]:
    """
    The asset's current review stage: the latest review-workflow action
    (PROPOSAL/REVIEW/PUBLICATION/…) with its ``workflow_status`` (assigned /
    notified / finished). Read-only and distinct from ``asset.status``.
    Returns ``null`` when the asset has no workflow actions.

    Read access: `LIB/ASSETS` OR a privilege on the asset's own category (same
    rule as `assets.get`).

    - **asset_id**: Asset id
    """
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' does not exist"
        )
    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([asset.category] if asset.category else []),
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


@router.get("/requests", response_model=List[AssetRequest])
def get_asset_requests(
    state: str = "PENDING",
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_db_session),
    # Any authenticated user, with no module privilege gate: this reads only the
    # caller's own rows (scoped by current.id), so there is nothing a privilege
    # could usefully protect. The LIB/ACTIONS option these endpoints used to gate
    # on has no privilege row for ANY profile, so it 403'd every real account.
    current: User = Depends(current_active_user)
) -> List[AssetRequest]:
    """
    Every asset the current user has taken part in — requests directed at them
    plus assets they proposed — one entry per asset, newest change first.

    Backs the "My Asset Requests" page. The user is taken from the JWT; a user
    only ever sees their own.

    - **state**: `PENDING` (still in motion) or `HANDLED` (closed)
    - **skip** / **limit**: pagination, applied after grouping so the bounds
      count entries the caller sees rather than raw rows
    """
    return actions_service.list_participations(
        session, current.id, state=state, skip=skip, limit=limit)


@router.get("/notifications", response_model=NotificationFeed)
def get_notifications(
    limit: int = 5,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user)
) -> NotificationFeed:
    """
    The current user's attention feed: exactly the requests still awaiting THEM.

    A strict subset of GET /requests — anything waiting on someone else
    (an asset the caller proposed, say) is deliberately absent, because nothing
    is being asked of them. `total` reports how many are outstanding so the panel
    can cap `items` at `limit` and still show that more exist.
    """
    return actions_service.list_notifications(session, current.id, limit=limit)


@router.post("/notifications/{id}/acknowledge", response_model=Action)
def acknowledge_notification(
    id: int, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user)
) -> Action:
    """
    Acknowledge an outcome notice — the caller has taken note, so it is handled.

    Only PUBLICATION/REJECTION qualify: they are informational, and reading them
    IS resolving them. REVIEW/MODIFICATION are resolved by reviewing or
    resubmitting and return 400 here — writing the terminal row for one of those
    would consume the assignee's turn without the work being done.

    - **id**: The pending action's id (from GET /notifications or /requests)
    """
    action = _own_notification(session, id, current)
    try:
        return actions_service.acknowledge_notification(session, action)
    except actions_service.NotificationNotAcknowledgeable as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Could not acknowledge the notification due to a data conflict")


@router.get("/{id}", response_model=Action)
def get(
    id: int, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user)
) -> Action:
    """
    Get an action by its ID — restricted to the caller's own action (or any
    action for a superuser). Every current consumer (the Review/Modify/Show
    Action pages, resolving a bell notification's `?action=` id) only ever
    reads the caller's own row; a non-owner gets 404 (not 403) so this
    doesn't disclose whether another user's action id exists. Like
    `/notifications`, `/reviews`, `/modifications`, this used to gate on
    `require_privilege("LIB","ACTIONS")` — a privilege row no profile has
    ever held — which 403'd this for every non-superuser, including a
    REVIEWER opening their own assigned review ("This review could not be
    found").

    - **id**: Unique action ID
    """
    action = session.get(Action, id)
    if not action or (not current.is_superuser and action.user_id != current.id):
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
    current: User = Depends(current_active_user),
) -> Action:
    """
    Delete an action (logical delete). Also backs the Foro discussion's
    comment/question delete (`deleteParticipation`).

    Performs a logical delete by setting is_active=False instead of removing the record.

    Write access: `LIB/ASSETS` OR a privilege on the action's own asset's
    category, with edit intent (same rule as `set_vote`/`add_comment`).

    - **id**: Unique action ID to delete
    """
    action = session.get(Action, id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    asset = session.get(Asset, action.asset) if action.asset else None
    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([asset.category] if asset and asset.category else []),
        can_edit=True,
    )

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
