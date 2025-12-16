from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime

class RoleBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Role(RoleBase, table=True):
    __tablename__ = "roles"

class RoleCreate(SQLModel):
    code: str
    name: str
    description: Optional[str] = None

class RoleUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None