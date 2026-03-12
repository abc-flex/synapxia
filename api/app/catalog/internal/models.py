"""Models for Digital Assets module"""
from sqlmodel import Field, SQLModel, Column, String, ForeignKey
from sqlalchemy import JSON
from typing import Optional, List, Dict, Any
from datetime import datetime

# Categories Models


class CategoryBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    parent: Optional[str] = Field(default=None, foreign_key="categories.code")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Category(CategoryBase, table=True):
    __tablename__ = "categories"


class CategoryCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique category code")
    name: str = Field(max_length=100, description="Category name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Category description")
    parent: Optional[str] = Field(
        default=None, max_length=50, description="Parent category code")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the category is active")


class CategoryUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Category name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Category description")
    parent: Optional[str] = Field(
        default=None, max_length=50, description="Parent category code")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the category is active")

# Features Models


class FeatureBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Feature(FeatureBase, table=True):
    __tablename__ = "features"


class FeatureCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique feature code")
    name: str = Field(max_length=100, description="Feature name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Feature description")
    type: str = Field(max_length=100, description="Feature type")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the feature is active")


class FeatureUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Feature name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Feature description")
    type: Optional[str] = Field(
        default=None, max_length=100, description="Feature type")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the feature is active")

# Assets Models


class AssetBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(
        default=None, foreign_key="categories.code")
    reference: Optional[str] = Field(default=None, max_length=500)
    type: str = Field(max_length=100)
    status: str = Field(max_length=100)
    visibility: str = Field(max_length=100)
    tags: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column("tags", JSON))
    details: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column("details", JSON))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Asset(AssetBase, table=True):
    __tablename__ = "assets"


class AssetCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique asset code")
    name: str = Field(max_length=100, description="Asset name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Asset description")
    category: Optional[str] = Field(
        default=None, max_length=50, description="Category code")
    reference: Optional[str] = Field(
        default=None, max_length=500, description="Asset reference")
    type: str = Field(max_length=100, description="Asset type")
    status: str = Field(max_length=100, description="Asset status")
    visibility: str = Field(max_length=100, description="Asset visibility")
    tags: Optional[Dict[str, Any]] = Field(
        default=None, description="Asset tags (JSON)")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Asset details (JSON)")
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
        default=None, max_length=500, description="Asset reference")
    type: Optional[str] = Field(
        default=None, max_length=100, description="Asset type")
    status: Optional[str] = Field(
        default=None, max_length=100, description="Asset status")
    visibility: Optional[str] = Field(
        default=None, max_length=100, description="Asset visibility")
    tags: Optional[Dict[str, Any]] = Field(
        default=None, description="Asset tags (JSON)")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Asset details (JSON)")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the asset is active")

# Characterizations Models


class CharacterizationBase(SQLModel):
    asset: str = Field(sa_column=Column(
        'asset', String, ForeignKey('assets.code'), primary_key=True))
    feature: str = Field(sa_column=Column(
        'feature', String, ForeignKey('features.code'), primary_key=True))
    value: str = Field(max_length=500)
    details: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Characterization(CharacterizationBase, table=True):
    __tablename__ = "characterizations"


class CharacterizationCreate(SQLModel):
    asset: str = Field(max_length=50, description="Asset code")
    feature: str = Field(
        max_length=50, description="Feature code")
    value: str = Field(max_length=500, description="Characterization value")
    details: Optional[str] = Field(
        default=None, max_length=500, description="Additional details")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the characterization is active")


class CharacterizationUpdate(SQLModel):
    value: Optional[str] = Field(
        default=None, max_length=500, description="Characterization value")
    details: Optional[str] = Field(
        default=None, max_length=500, description="Additional details")
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
