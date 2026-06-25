"""Models for Asset Library module"""
from sqlmodel import Field, SQLModel, Column, String, ForeignKey
from sqlalchemy import JSON, BigInteger
from typing import Optional, Dict, Any, List
from datetime import datetime

# Assets Models


class AssetBase(SQLModel):
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(
        default=None, foreign_key="categories.code")
    reference: Optional[str] = Field(default=None)
    status: str = Field(max_length=100)
    tags: Optional[Any] = Field(
        default=None, sa_column=Column("tags", JSON))
    detail: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Asset(AssetBase, table=True):
    __tablename__ = "assets"
    id: Optional[int] = Field(default=None, primary_key=True)


class AssetCreate(SQLModel):
    name: str = Field(max_length=100, description="Asset name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Asset description")
    category: Optional[str] = Field(
        default=None, max_length=50, description="Category code")
    reference: Optional[str] = Field(
        default=None, description="Asset reference")
    status: str = Field(max_length=100, description="Asset status")
    tags: Optional[Any] = Field(
        default=None, description="Asset tags (JSON)")
    detail: Optional[str] = Field(
        default=None, description="Asset detail")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the asset is active")


class AssetUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Asset name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Asset description")
    category: Optional[str] = Field(
        default=None, max_length=50, description="Category code")
    reference: Optional[str] = Field(
        default=None, description="Asset reference")
    status: Optional[str] = Field(
        default=None, max_length=100, description="Asset status")
    tags: Optional[Any] = Field(
        default=None, description="Asset tags (JSON)")
    detail: Optional[str] = Field(
        default=None, description="Asset detail")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the asset is active")

# Characterizations Models


class CharacterizationBase(SQLModel):
    # `asset` is BIGINT (FK to assets.id) per the DDL; was incorrectly typed
    # as str/assets.code which caused SELECTs to fail with column type
    # mismatches. Also: DB column is `detail` (singular), not `details`.
    asset: int = Field(sa_column=Column(
        'asset', BigInteger, ForeignKey('assets.id'), primary_key=True))
    feature: str = Field(sa_column=Column(
        'feature', String, ForeignKey('features.code'), primary_key=True))
    value: Optional[str] = Field(default=None)
    detail: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Characterization(CharacterizationBase, table=True):
    __tablename__ = "characterizations"


class CharacterizationCreate(SQLModel):
    asset: int = Field(description="Asset id (FK to assets.id)")
    feature: str = Field(
        max_length=50, description="Feature code")
    value: Optional[str] = Field(default=None, description="Characterization value")
    detail: Optional[str] = Field(
        default=None, description="Additional detail")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the characterization is active")


class CharacterizationUpdate(SQLModel):
    value: Optional[str] = Field(
        default=None, description="Characterization value")
    detail: Optional[str] = Field(
        default=None, description="Additional detail")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the characterization is active")

# Favorites Models


class FavoriteBase(SQLModel):
    # `asset` is BIGINT (FK to assets.id) per the DDL — assets has no `code`
    # column. DB table is `favorite_assets`, not `favorites`.
    user_id: int = Field(sa_column=Column(
        'user_id', BigInteger, ForeignKey('users.id'), primary_key=True))
    asset: int = Field(sa_column=Column(
        'asset', BigInteger, ForeignKey('assets.id'), primary_key=True))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Favorite(FavoriteBase, table=True):
    __tablename__ = "favorite_assets"


class FavoriteCreate(SQLModel):
    user_id: int = Field(description="User ID")
    asset: int = Field(description="Asset id (FK to assets.id)")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the favorite is active")


class FavoriteUpdate(SQLModel):
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the favorite is active")

# Actions Models


class ActionBase(SQLModel):
    # `asset` is BIGINT (FK to assets.id) per the DDL — assets has no `code`
    # column (seed inserts integer asset ids). The DB column is `detail` (TEXT,
    # singular); there is no `details` JSON column nor a `measured_at` column.
    asset: int = Field(sa_column=Column(
        'asset', BigInteger, ForeignKey('assets.id'), nullable=False))
    user_id: int = Field(foreign_key="users.id")
    type: str = Field(max_length=100)
    # `workflow_status` is a VARCHAR(100) nullable column already present in the
    # DDL (db/sql/41-lib-ddl.sql) referencing the WORKFLOW_STATUS list
    # (ASSIGNED/NOTIFIED/FINISHED). It drives the review workflow + notifications;
    # exposing it here is additive (no migration).
    workflow_status: Optional[str] = Field(default=None, max_length=100)
    content: Optional[str] = Field(default=None)
    reference: Optional[str] = Field(default=None)
    parent: Optional[int] = Field(default=None, foreign_key="actions.id")
    detail: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Action(ActionBase, table=True):
    __tablename__ = "actions"
    id: Optional[int] = Field(default=None, primary_key=True)


class ActionCreate(SQLModel):
    asset: int = Field(description="Asset id (FK to assets.id)")
    user_id: int = Field(description="User ID")
    type: str = Field(max_length=100, description="Action type")
    workflow_status: Optional[str] = Field(
        default=None, max_length=100,
        description="Workflow status (WORKFLOW_STATUS list value)")
    content: Optional[str] = Field(
        default=None, description="Action content")
    reference: Optional[str] = Field(
        default=None, description="Action reference")
    parent: Optional[int] = Field(default=None, description="Parent action ID")
    detail: Optional[str] = Field(
        default=None, description="Additional detail")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the action is active")


class ActionUpdate(SQLModel):
    workflow_status: Optional[str] = Field(
        default=None, max_length=100,
        description="Workflow status (WORKFLOW_STATUS list value)")
    content: Optional[str] = Field(
        default=None, description="Action content")
    reference: Optional[str] = Field(
        default=None, description="Action reference")
    parent: Optional[int] = Field(default=None, description="Parent action ID")
    detail: Optional[str] = Field(
        default=None, description="Additional detail")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the action is active")


# Vote DTOs (HU-LI05) — votes are `actions` rows of type VOTE with
# content POSITIVE/NEGATIVE. No new table: these are request/response shapes
# layered over the existing `actions` substrate.


class VoteRequest(SQLModel):
    """Body for setting/flipping a user's vote on an asset."""
    user_id: int = Field(description="User ID")
    asset: int = Field(description="Asset id (FK to assets.id)")
    content: str = Field(description="Vote value: POSITIVE or NEGATIVE")


class VoteTally(SQLModel):
    """Aggregated vote summary for an asset (+ the requester's own vote)."""
    asset: int
    positive: int = 0
    negative: int = 0
    score: int = 0
    my_vote: Optional[str] = None


# Foro DTOs (HU-LI06) — comments/questions/answers are `actions` rows of type
# COMMENT/QUESTION/ANSWER; answers thread to their question via `parent`. No new
# table: these are request/response shapes over the existing `actions` substrate.


class ParticipationCreate(SQLModel):
    """Body for posting a comment or question on an asset."""
    user_id: int = Field(description="User ID")
    asset: int = Field(description="Asset id (FK to assets.id)")
    content: str = Field(description="Comment/question text")


class AnswerCreate(SQLModel):
    """Body for answering a question (``parent`` = the QUESTION action id)."""
    user_id: int = Field(description="User ID")
    asset: int = Field(description="Asset id (FK to assets.id)")
    content: str = Field(description="Answer text")
    parent: int = Field(description="Parent QUESTION action id")


class DiscussionItem(SQLModel):
    """A participation row (comment/question/answer) enriched with the author's
    username — the read shape returned by the discussion endpoints."""
    id: int
    asset: int
    user_id: int
    author: Optional[str] = None
    type: str
    content: Optional[str] = None
    parent: Optional[int] = None
    created_at: datetime

# Asset Relations Models


class AssetRelationBase(SQLModel):
    # `source`/`target` are BIGINT (FK to assets.id) per the DDL — assets has
    # no `code` column. DB table is `related_assets`, not `asset_relations`,
    # and carries a `rationale` text column.
    source: int = Field(sa_column=Column(
        'source', BigInteger, ForeignKey('assets.id'), primary_key=True))
    target: int = Field(sa_column=Column(
        'target', BigInteger, ForeignKey('assets.id'), primary_key=True))
    type: str = Field(max_length=100)
    rationale: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class AssetRelation(AssetRelationBase, table=True):
    __tablename__ = "related_assets"


class AssetRelationCreate(SQLModel):
    source: int = Field(description="Source asset id (FK to assets.id)")
    target: int = Field(description="Target asset id (FK to assets.id)")
    type: str = Field(max_length=100, description="Relation type")
    rationale: Optional[str] = Field(
        default=None, description="Why the assets are related")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the relation is active")


class AssetRelationUpdate(SQLModel):
    type: Optional[str] = Field(
        default=None, max_length=100, description="Relation type")
    rationale: Optional[str] = Field(
        default=None, description="Why the assets are related")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the relation is active")


class RelatedAsset(SQLModel):
    """Read projection (HU-LI07): a related asset resolved from `related_assets`,
    carrying the relation metadata. `direction` is "outgoing" when the viewed
    asset is the relation's source (it references this asset) and "incoming"
    when it is the target (this asset is referenced by it)."""
    id: int = Field(description="Related asset id")
    name: str = Field(description="Related asset name")
    description: Optional[str] = Field(default=None, description="Related asset description")
    category: Optional[str] = Field(default=None, description="Related asset category code")
    status: str = Field(description="Related asset status")
    tags: Optional[Any] = Field(default=None, description="Related asset tags (JSON)")
    relation_type: str = Field(description="Relation type (RELATION_TYPE)")
    direction: str = Field(description='"outgoing" (this asset is the source) or "incoming" (this asset is the target)')
    rationale: Optional[str] = Field(default=None, description="Why the assets are related")


# Asset Permissions Models


class AssetPermissionBase(SQLModel):
    # `asset` is BIGINT (FK to assets.id). The PK is a surrogate `id`
    # (bigserial) — unlike relations' composite key. `target_type` /
    # `access_level` come from the TARGET_TYPE / ACCESS_LEVEL lists;
    # `target_code` is the target entity's id/code (literal "PUBLIC" when
    # target_type=PUBLIC). `valid_from`/`valid_to` carry optional temporal
    # validity; `is_active` drives logical delete (added in 43-lib-perms-active-ddl).
    asset: int = Field(sa_column=Column(
        'asset', BigInteger, ForeignKey('assets.id')))
    target_type: str = Field(max_length=100)
    target_code: str = Field(max_length=50)
    access_level: str = Field(max_length=100)
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: Optional[datetime] = None
    is_active: bool = Field(default=True)


class AssetPermission(AssetPermissionBase, table=True):
    __tablename__ = "asset_permissions"
    id: Optional[int] = Field(default=None, primary_key=True)


class AssetPermissionCreate(SQLModel):
    asset: int = Field(description="Asset id (FK to assets.id)")
    target_type: str = Field(
        max_length=100, description="Target type (TARGET_TYPE list value)")
    target_code: str = Field(
        max_length=50, description="Target id/code, or 'PUBLIC'")
    access_level: str = Field(
        max_length=100, description="Access level (ACCESS_LEVEL list value)")
    valid_to: Optional[datetime] = Field(
        default=None, description="Optional expiry timestamp")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the permission is active")


class AssetPermissionUpdate(SQLModel):
    target_type: Optional[str] = Field(default=None, max_length=100)
    target_code: Optional[str] = Field(default=None, max_length=50)
    access_level: Optional[str] = Field(default=None, max_length=100)
    valid_to: Optional[datetime] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class AssetWithAccessLevels(SQLModel):
    """Asset read projection augmented with an aggregated permission summary.

    `access_levels` holds the distinct active access levels granted on the asset
    (e.g. VIEW, MANAGE); `is_public` is true when any active permission targets
    PUBLIC. Read-only projection — does not change the `Asset` table contract.
    """
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    reference: Optional[str] = None
    status: str
    tags: Optional[Any] = None
    detail: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    access_levels: List[str] = Field(default_factory=list)
    is_public: bool = False
