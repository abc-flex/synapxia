"""FastAPI-Users schemas for authentication."""
from typing import Optional
from fastapi_users import schemas
from datetime import datetime


class UserRead(schemas.BaseUser[int]):
    """User read schema for API responses."""
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    menu_role: str
    business_unit: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserCreate(schemas.BaseUserCreate):
    """User create schema - used for registration."""
    username: str
    email: str
    password: str
    first_name: str
    last_name: str
    menu_role: str
    business_unit: str


class UserUpdate(schemas.BaseUserUpdate):
    """User update schema."""
    email: Optional[str] = None
    password: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    menu_role: Optional[str] = None
    business_unit: Optional[str] = None
