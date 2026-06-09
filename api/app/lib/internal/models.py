"""Models for Asset Library module"""
from sqlmodel import Field, SQLModel, Column, String, ForeignKey
from sqlalchemy import JSON, BigInteger
from typing import Optional, Dict, Any
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
    user_id: int = Field(sa_column=Column(
        'user_id', ForeignKey('users.id'), primary_key=True))
    asset: str = Field(sa_column=Column(
        'asset', String, ForeignKey('assets.code'), primary_key=True))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Favorite(FavoriteBase, table=True):
    __tablename__ = "favorites"


class FavoriteCreate(SQLModel):
    user_id: int = Field(description="User ID")
    asset: str = Field(max_length=50, description="Asset code")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the favorite is active")


class FavoriteUpdate(SQLModel):
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the favorite is active")

# Actions Models


class ActionBase(SQLModel):
    asset: str = Field(max_length=50, foreign_key="assets.code")
    user_id: int = Field(foreign_key="users.id")
    type: str = Field(max_length=100)
    content: Optional[str] = Field(default=None, max_length=500)
    reference: Optional[str] = Field(default=None, max_length=500)
    parent: Optional[int] = Field(default=None, foreign_key="actions.id")
    details: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column("details", JSON))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    measured_at: Optional[datetime] = None


class Action(ActionBase, table=True):
    __tablename__ = "actions"
    id: Optional[int] = Field(default=None, primary_key=True)


class ActionCreate(SQLModel):
    asset: str = Field(max_length=50, description="Asset code")
    user_id: int = Field(description="User ID")
    type: str = Field(max_length=100, description="Action type")
    content: Optional[str] = Field(
        default=None, max_length=500, description="Action content")
    reference: Optional[str] = Field(
        default=None, max_length=500, description="Action reference")
    parent: Optional[int] = Field(default=None, description="Parent action ID")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Action details (JSON)")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the action is active")


class ActionUpdate(SQLModel):
    content: Optional[str] = Field(
        default=None, max_length=500, description="Action content")
    reference: Optional[str] = Field(
        default=None, max_length=500, description="Action reference")
    parent: Optional[int] = Field(default=None, description="Parent action ID")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Action details (JSON)")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the action is active")

# Asset Relations Models


class AssetRelationBase(SQLModel):
    source: str = Field(sa_column=Column(
        'source', String, ForeignKey('assets.code'), primary_key=True))
    target: str = Field(sa_column=Column(
        'target', String, ForeignKey('assets.code'), primary_key=True))
    type: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class AssetRelation(AssetRelationBase, table=True):
    __tablename__ = "asset_relations"


class AssetRelationCreate(SQLModel):
    source: str = Field(max_length=50, description="Source asset code")
    target: str = Field(max_length=50, description="Target asset code")
    type: str = Field(max_length=100, description="Relation type")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the relation is active")


class AssetRelationUpdate(SQLModel):
    type: Optional[str] = Field(
        default=None, max_length=100, description="Relation type")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the relation is active")
