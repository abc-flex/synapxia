"""Models for the Support module (bug reports)."""
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON
from typing import Optional, List
from datetime import datetime

# Server-side caps (Constitution IV/V: bound request size, never trust the client).
MAX_DESCRIPTION_LENGTH = 5000
MAX_ATTACHMENTS = 3
# Base64 data-URLs run ~33% larger than the underlying binary; ~2MB of image data
# becomes roughly this many characters once encoded.
MAX_IMAGE_DATA_URL_LENGTH = 2_800_000


class BugReportBase(SQLModel):
    description: str = Field(max_length=MAX_DESCRIPTION_LENGTH)
    page_url: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    screenshot: Optional[str] = Field(default=None)
    attachments: Optional[List[str]] = Field(
        default=None, sa_column=Column("attachments", JSON))
    status: str = Field(default="OPEN", max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class BugReport(BugReportBase, table=True):
    __tablename__ = "bug_reports"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")


class BugReportCreate(SQLModel):
    # No max_length here — kept unbounded so an over-cap submission gets the
    # route's explicit 400 (with a clear message) instead of pydantic's 422.
    description: str = Field(description="What went wrong")
    page_url: Optional[str] = Field(
        default=None, description="The page the user was on")
    user_agent: Optional[str] = Field(
        default=None, description="Reporting browser's user agent")
    screenshot: Optional[str] = Field(
        default=None, description="Base64 data-URL of the (optionally annotated) screenshot")
    attachments: Optional[List[str]] = Field(
        default=None, description="Extra base64 data-URL images (max 3)")


class BugReportRead(SQLModel):
    """Listing shape — omits the heavy screenshot/attachments blobs."""
    id: int
    user_id: int
    description: str
    page_url: Optional[str]
    status: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
