"""Models for Taxonomy module - Categories, Features, Specifications"""
from sqlmodel import Field, SQLModel, Column, String, ForeignKey
from typing import Optional
from datetime import datetime

# Categories Models


class CategoryBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    parent: Optional[str] = Field(default=None, foreign_key="categories.code")
    icon: Optional[str] = Field(default=None)
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
    icon: Optional[str] = Field(
        default=None, description="Icon (Heroicon path or identifier)")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the category is active")


class CategoryUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Category name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Category description")
    parent: Optional[str] = Field(
        default=None, max_length=50, description="Parent category code")
    icon: Optional[str] = Field(
        default=None, description="Icon (Heroicon path or identifier)")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the category is active")

# Features Models


class FeatureBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: Optional[str] = Field(default=None, max_length=100)
    list: Optional[str] = Field(default=None, max_length=50)
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
    type: Optional[str] = Field(default=None, max_length=100, description="Feature type")
    list: Optional[str] = Field(
        default=None, max_length=50, description="List code (references lists.code where type='FEATURE')")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the feature is active")


class FeatureUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Feature name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Feature description")
    type: Optional[str] = Field(
        default=None, max_length=100, description="Feature type")
    list: Optional[str] = Field(
        default=None, max_length=50, description="List code (references lists.code where type='FEATURE')")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the feature is active")

# Specifications Models


class SpecificationBase(SQLModel):
    category: str = Field(sa_column=Column(
        'category', String, ForeignKey('categories.code'), primary_key=True))
    feature: str = Field(sa_column=Column(
        'feature', String, ForeignKey('features.code'), primary_key=True))
    default_value: Optional[str] = Field(default=None)
    required: bool = Field(default=False)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Specification(SpecificationBase, table=True):
    __tablename__ = "specifications"


class SpecificationCreate(SQLModel):
    category: str = Field(max_length=50, description="Category code")
    feature: str = Field(max_length=50, description="Feature code")
    default_value: Optional[str] = Field(
        default=None, description="Default value (Any or a List_items.value)")
    required: Optional[bool] = Field(
        default=False, description="Whether this feature is required for the category")
    sort_order: Optional[int] = Field(
        default=0, description="Display order of this feature within its category")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the specification is active")


class SpecificationUpdate(SQLModel):
    default_value: Optional[str] = Field(
        default=None, description="Default value (Any or a List_items.value)")
    required: Optional[bool] = Field(
        default=None, description="Whether this feature is required for the category")
    sort_order: Optional[int] = Field(
        default=None, description="Display order of this feature within its category")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the specification is active")
