"""Models for Initiatives module"""
from sqlmodel import Field, SQLModel, Column, String, ForeignKey
from typing import Optional
from datetime import datetime

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
