"""Models for Initiatives module"""
from sqlmodel import Field, SQLModel, Column, String, ForeignKey
from sqlalchemy import JSON, BigInteger
from typing import Optional, Any, Dict, List
from datetime import datetime

# Initiative Models
#
# Initiative Management (specs/004-initiative-management) edits existing
# initiatives — there is deliberately NO InitiativeCreate: initiatives are only
# ever proposed (a future propose flow), never created by hand. Status changes
# from the management surface are restricted to the owner moves in
# inits/internal/status_service.py; every other status belongs to the
# propose/diagnose/modify workflow.


class InitiativeBase(SQLModel):
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    expected_impact: str = Field(max_length=100)
    priority_level: str = Field(max_length=100)
    reference: Optional[str] = Field(default=None)
    status: str = Field(max_length=100)
    type: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[Any] = Field(default=None, sa_column=Column("tags", JSON))
    detail: Optional[str] = Field(default=None)
    score: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Initiative(InitiativeBase, table=True):
    __tablename__ = "initiatives"
    id: Optional[int] = Field(default=None, primary_key=True)


# Criterias Models

class CriteriaBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    list: Optional[str] = Field(default=None, foreign_key="criterias.code")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Criteria(CriteriaBase, table=True):
    __tablename__ = "criterias"


class CriteriaCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique criteria code")
    name: str = Field(max_length=100, description="Criteria name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Criteria description")
    list: Optional[str] = Field(
        default=None, max_length=50, description="List criteria code")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the criteria is active")


class CriteriaUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Criteria name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Criteria description")
    list: Optional[str] = Field(
        default=None, max_length=50, description="List criteria code")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the criteria is active")


class InitiativeUpdate(SQLModel):
    """Partial update from Initiative Management's Core Fields tab. `score` is
    absent on purpose — it is the diagnosis result, never hand-edited."""
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: Optional[str] = Field(
        default=None, max_length=100, description="INITIATIVE_TYPE list value")
    expected_impact: Optional[str] = Field(
        default=None, max_length=100, description="EXPECTED_IMPACT list value")
    priority_level: Optional[str] = Field(
        default=None, max_length=100, description="PRIORITY_LEVEL list value")
    reference: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    detail: Optional[str] = Field(default=None)
    status: Optional[str] = Field(
        default=None, max_length=100,
        description="INITIATIVE_STATUS list value — only owner moves are accepted")


class InitiativeWithAccess(InitiativeBase):
    """Initiative read projection for Initiative Management: the caller's own
    effective access, whether they favorited it, and the statuses the status
    control may offer (the current one plus its allowed owner moves)."""
    id: int
    my_access: str
    is_favorite: bool = False
    allowed_statuses: List[str] = Field(default_factory=list)
    # Scope types (USER/ROLE/TEAM/UNIT/PROJECT/PUBLIC) through which a live
    # grant reaches the caller — drives the list's privileges filter.
    permission_scopes: List[str] = Field(default_factory=list)


# Collaborations — the initiatives' activity substrate (the `inits` twin of
# lib's `actions`: `actions.asset` is NOT NULL, so initiative activity cannot
# live there). `type` is a COLLAB_TYPE value; `workflow_status` is
# PENDING/HANDLED for workflow rows and NULL for VOTE/COMMENT/QUESTION/ANSWER.


class Collaboration(SQLModel, table=True):
    __tablename__ = "collaborations"
    id: Optional[int] = Field(default=None, primary_key=True)
    init: int = Field(sa_column=Column(
        'init', BigInteger, ForeignKey('initiatives.id'), nullable=False))
    user_id: int = Field(foreign_key="users.id")
    type: str = Field(max_length=100)
    workflow_status: Optional[str] = Field(default=None, max_length=100)
    content: Optional[str] = Field(default=None)
    reference: Optional[str] = Field(default=None)
    parent: Optional[int] = Field(default=None, foreign_key="collaborations.id")
    detail: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class InitParticipationCreate(SQLModel):
    """Body for posting a comment or question. The author is the signed-in
    user — deliberately no `user_id` field."""
    init: int = Field(description="Initiative id")
    content: str = Field(description="Comment / question text")


class InitAnswerCreate(InitParticipationCreate):
    parent: int = Field(description="Id of the QUESTION collaboration being answered")


class InitDiscussionItem(SQLModel):
    """A comment/question/answer collaboration enriched with the author's
    username — the same shape as lib's DiscussionItem with `init` for `asset`."""
    id: int
    init: int
    user_id: int
    author: Optional[str] = None
    type: str
    content: Optional[str] = None
    parent: Optional[int] = None
    created_at: datetime


# Initiative permissions — per-resource grants following the asset_permissions
# model exactly (Constitution "Per-resource permissions"): MANAGE/VIEW, a
# validity window, and NO `is_active` flag — a grant is revoked by setting
# `valid_to`, never deleted.


class InitPermission(SQLModel, table=True):
    __tablename__ = "init_permissions"
    id: Optional[int] = Field(default=None, primary_key=True)
    init: int = Field(sa_column=Column(
        'init', BigInteger, ForeignKey('initiatives.id'), nullable=False))
    target_type: str = Field(max_length=100)
    target_code: str = Field(max_length=50)
    access_level: str = Field(max_length=100)
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: Optional[datetime] = None


class InitPermissionCreate(SQLModel):
    init: int = Field(description="Initiative id (FK to initiatives.id)")
    target_type: str = Field(
        max_length=100, description="Target type (TARGET_TYPE list value)")
    target_code: str = Field(
        max_length=50, description="Target id/code, or 'ALL' for PUBLIC")
    access_level: str = Field(
        max_length=100, description="Access level (ACCESS_LEVEL list value)")
    valid_from: Optional[datetime] = Field(
        default=None, description="Optional start timestamp (default: now)")
    valid_to: Optional[datetime] = Field(
        default=None, description="Optional expiry timestamp")


class InitPermissionUpdate(SQLModel):
    access_level: Optional[str] = Field(default=None, max_length=100)
    valid_from: Optional[datetime] = Field(default=None)
    valid_to: Optional[datetime] = Field(
        default=None, description="Expiry timestamp; DELETE revokes immediately")


# Diagnostics — one answer set per (initiative, criterion): the proposer's
# `creator_score` and, once diagnosed, the reviewer's `reviewer_score`. Scores
# are values of the criterion's own list (`criterias.list`). Read-only here.


class Diagnostic(SQLModel, table=True):
    __tablename__ = "diagnostics"
    init: int = Field(sa_column=Column(
        'init', BigInteger, ForeignKey('initiatives.id'), primary_key=True))
    criteria: str = Field(sa_column=Column(
        'criteria', String(50), ForeignKey('criterias.code'), primary_key=True))
    creator_score: int
    reviewer_score: Optional[int] = None
    rationale: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class DiagnosticRow(SQLModel):
    """One criterion of an initiative's diagnosis, with both answers resolved
    to labels of the criterion's own scale in the requested language."""
    criteria: str
    name: str
    description: Optional[str] = None
    list: Optional[str] = None
    is_active_criteria: bool = True
    creator_score: Optional[int] = None
    creator_label: Optional[str] = None
    reviewer_score: Optional[int] = None
    reviewer_label: Optional[str] = None
    rationale: Optional[str] = None


class DiagnosticsResponse(SQLModel):
    init: int
    score: Optional[int] = None
    # Overall score per party: the sum of that party's answers over the listed
    # criteria, plus how many criteria they answered. `reviewer_total` is null
    # while the reviewer has answered none.
    creator_total: Optional[int] = None
    creator_answered: int = 0
    reviewer_total: Optional[int] = None
    reviewer_answered: int = 0
    items: List[DiagnosticRow] = Field(default_factory=list)


class FavoriteState(SQLModel):
    init: int
    is_favorite: bool


# Favorite initiatives — read here only to flag the caller's favorites in the
# management list (favoriting itself belongs to Explore Initiatives).


class FavoriteInit(SQLModel, table=True):
    __tablename__ = "favorite_inits"
    user_id: int = Field(sa_column=Column(
        'user_id', BigInteger, ForeignKey('users.id'), primary_key=True))
    init: int = Field(sa_column=Column(
        'init', BigInteger, ForeignKey('initiatives.id'), primary_key=True))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


# Initiative ↔ asset links, seen from the initiative. Backed by lib's
# `AssetInit` (table asset_inits) — the same records the asset-side
# "Related Inits" tab shows. One link per (asset, initiative) pair.


class InitiativeAsset(SQLModel):
    asset: int
    asset_name: Optional[str] = None
    category: Optional[str] = None
    asset_status: Optional[str] = None
    type: str
    rationale: Optional[str] = None
    created_at: datetime


class InitiativeAssetCreate(SQLModel):
    asset: int = Field(description="Asset id (FK to assets.id)")
    type: str = Field(max_length=100, description="RELATION_TYPE list value")
    rationale: Optional[str] = Field(
        default=None, description="Why the initiative and asset are related")


# ── Contribution workflow (specs/005-explore-initiatives) ────────────────────
# Propose → Diagnose → Modify → Acknowledge on the `collaborations` substrate,
# plus the Explore listing. Actors always come from the session: none of these
# bodies carries a user id.


class DiagnosisAnswer(SQLModel):
    """The proposer's answer to one criterion: a value of the criterion's own
    scale plus an optional rationale."""
    score: int = Field(description="Value of the criterion's scale (criterias.list)")
    rationale: Optional[str] = Field(default=None, max_length=2000)


class ProposeAssetLink(SQLModel):
    asset: int = Field(description="Asset id (FK to assets.id)")
    type: str = Field(max_length=100, description="RELATION_TYPE list value")
    rationale: Optional[str] = Field(default=None, max_length=2000)


class InitiativeProposeRequest(SQLModel):
    """Body of POST /api/initiatives/propose. No `status` (always ACTIVATED) and
    no `score` (set by the diagnosis)."""
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: Optional[str] = Field(default=None, max_length=100)
    expected_impact: str = Field(max_length=100)
    priority_level: str = Field(max_length=100)
    reference: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    detail: Optional[str] = Field(default=None)
    reviewer_id: Optional[int] = Field(
        default=None, description="Eligible reviewer; omitted → auto-assigned")
    answers: Dict[str, DiagnosisAnswer] = Field(
        default_factory=dict, description="criteria code → proposer answer")
    assets: List[ProposeAssetLink] = Field(default_factory=list)


class InitiativeDiagnoseRequest(SQLModel):
    """Body of POST /api/initiatives/{id}/diagnose."""
    decision: str = Field(description="accept | reject | changes")
    feedback: Optional[str] = Field(default=None, max_length=2000)
    answers: Dict[str, int] = Field(
        default_factory=dict, description="criteria code → reviewer score")


class InitiativeResubmitRequest(SQLModel):
    """Body of POST /api/initiatives/{id}/resubmit — only sent keys apply."""
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: Optional[str] = Field(default=None, max_length=100)
    expected_impact: Optional[str] = Field(default=None, max_length=100)
    priority_level: Optional[str] = Field(default=None, max_length=100)
    reference: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    detail: Optional[str] = Field(default=None)
    answers: Optional[Dict[str, DiagnosisAnswer]] = Field(default=None)


class LinkableAsset(SQLModel):
    value: int
    label: str
    category: Optional[str] = None


class InitVoteTally(SQLModel):
    init: int
    positive: int = 0
    negative: int = 0
    score: int = 0
    my_vote: Optional[str] = None


class InitVoteRequest(SQLModel):
    content: str = Field(description="POSITIVE | NEGATIVE")


class InitiativeExploreItem(InitiativeBase):
    """An Explore Initiatives gallery row: the initiative plus the caller's
    access, favorite flag, grant scopes and the card's counters."""
    id: int
    my_access: str
    is_favorite: bool = False
    permission_scopes: List[str] = Field(default_factory=list)
    votes: InitVoteTally
    discussion_count: int = 0
    related_assets_count: int = 0


class InitiativeRequest(SQLModel):
    """One row of My Initiative Requests — one per initiative (lib's AssetRequest twin)."""
    init: int
    init_name: Optional[str] = None
    init_status: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    state: str
    awaited_party: Optional[str] = None
    pending_collab_id: Optional[int] = None
    pending_collab_type: Optional[str] = None
    last_change_at: datetime


class InitNotificationItem(SQLModel):
    id: int
    init: int
    init_name: Optional[str] = None
    type: str
    created_at: datetime


class InitNotificationFeed(SQLModel):
    items: List[InitNotificationItem] = Field(default_factory=list)
    total: int = 0


class CollaborationDetail(SQLModel):
    """A single collaboration row for its owner, with the initiative embedded so
    the action pages never need the INITIATIVES-only GET /api/initiatives/{id}."""
    id: int
    init: int
    user_id: int
    type: str
    workflow_status: Optional[str] = None
    content: Optional[str] = None
    reference: Optional[str] = None
    parent: Optional[int] = None
    detail: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    actor_name: Optional[str] = None
    initiative: Optional[Initiative] = None
    # The thread's CURRENT state (its newest row). The row itself never changes
    # status — resolving inserts a new row — so pages check this, not
    # `workflow_status`, to know whether the request is still pending.
    current_status: Optional[str] = None


class ScaleOption(SQLModel):
    value: int
    label: str


class DiagnosisForm(SQLModel):
    """Active criteria (unanswered) plus each scale's options — the questionnaire
    the Propose / Diagnose / Modify pages render."""
    items: List[DiagnosticRow] = Field(default_factory=list)
    scales: Dict[str, List[ScaleOption]] = Field(default_factory=dict)
