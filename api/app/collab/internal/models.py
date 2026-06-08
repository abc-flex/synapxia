"""Models for Collaboration module"""
from sqlmodel import Field, SQLModel, Column, String, ForeignKey
from typing import Optional
from datetime import datetime, date

# Roles Models

class RoleBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    icon: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Role(RoleBase, table=True):
    __tablename__ = "roles"


class RoleCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique role code")
    name: str = Field(max_length=100, description="Role name")
    description: Optional[str] = Field(
        default=None, max_length=255, description="Role description")
    icon: Optional[str] = Field(
        default=None, max_length=255, description="Icon name or path")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the role is active")


class RoleUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Role name")
    description: Optional[str] = Field(
        default=None, max_length=255, description="Role description")
    icon: Optional[str] = Field(
        default=None, max_length=255, description="Icon name or path")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the role is active")


# Teams Models


class TeamBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    lead: Optional[int] = Field(default=None, foreign_key="users.id")
    chat_channel_url: Optional[str] = Field(default=None, max_length=500)
    kanban_board_url: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Team(TeamBase, table=True):
    __tablename__ = "teams"


class TeamCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique team code")
    name: str = Field(max_length=100, description="Team name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Team description")
    lead: Optional[int] = Field(default=None, description="Team leader ID")
    chat_channel_url: Optional[str] = Field(
        default=None, max_length=500, description="Chat channel URL")
    kanban_board_url: Optional[str] = Field(
        default=None, max_length=500, description="Kanban board URL")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the team is active")


class TeamUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Team name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Team description")
    lead: Optional[int] = Field(default=None, description="Team leader ID")
    chat_channel_url: Optional[str] = Field(
        default=None, max_length=500, description="Chat channel URL")
    kanban_board_url: Optional[str] = Field(
        default=None, max_length=500, description="Kanban board URL")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the team is active")

# Assignments Models


class AssignmentBase(SQLModel):
    team: Optional[str] = Field(default=None, foreign_key="teams.code")
    user_id: int = Field(foreign_key="users.id")
    role: str = Field(max_length=50, foreign_key="roles.code")
    observation: Optional[str] = Field(default=None, max_length=500)
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: Optional[datetime] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Assignment(AssignmentBase, table=True):
    __tablename__ = "assignments"
    id: Optional[int] = Field(default=None, primary_key=True)


class AssignmentCreate(SQLModel):
    team: Optional[str] = Field(
        default=None, max_length=50, description="Team code")
    user_id: int = Field(description="User ID")
    role: str = Field(max_length=50, description="Role code")
    observation: Optional[str] = Field(
        default=None, max_length=500, description="Observation")
    valid_from: Optional[datetime] = Field(
        default=None, description="Validity start date")
    valid_to: Optional[datetime] = Field(
        default=None, description="Validity end date")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the assignment is active")


class AssignmentUpdate(SQLModel):
    team: Optional[str] = Field(
        default=None, max_length=50, description="Team code")
    role: Optional[str] = Field(
        default=None, max_length=50, description="Role code")
    observation: Optional[str] = Field(
        default=None, max_length=500, description="Observation")
    valid_from: Optional[datetime] = Field(
        default=None, description="Validity start date")
    valid_to: Optional[datetime] = Field(
        default=None, description="Validity end date")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the assignment is active")

# Projects Models


class ProjectBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    team: Optional[str] = Field(default=None, foreign_key="teams.code")
    repo_url: Optional[str] = Field(default=None, max_length=500)
    status: str = Field(max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Project(ProjectBase, table=True):
    __tablename__ = "projects"


class ProjectCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique project code")
    name: str = Field(max_length=100, description="Project name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Project description")
    team: Optional[str] = Field(
        default=None, max_length=50, description="Team code")
    repo_url: Optional[str] = Field(
        default=None, max_length=500, description="Repository URL")
    status: str = Field(max_length=100, description="Project status")
    start_date: Optional[date] = Field(default=None, description="Start date")
    end_date: Optional[date] = Field(default=None, description="End date")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the project is active")


class ProjectUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Project name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Project description")
    team: Optional[str] = Field(
        default=None, max_length=50, description="Team code")
    repo_url: Optional[str] = Field(
        default=None, max_length=500, description="Repository URL")
    status: Optional[str] = Field(
        default=None, max_length=100, description="Project status")
    start_date: Optional[date] = Field(default=None, description="Start date")
    end_date: Optional[date] = Field(default=None, description="End date")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the project is active")

# Dimensions Models


class DimensionBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    scale: Optional[str] = Field(default=None, foreign_key="lists.code")
    unit: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Dimension(DimensionBase, table=True):
    __tablename__ = "dimensions"


class DimensionCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique dimension code")
    name: str = Field(max_length=100, description="Dimension name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Dimension description")
    scale: Optional[str] = Field(
        default=None, max_length=50, description="Scale code (list)")
    unit: Optional[str] = Field(
        default=None, max_length=100, description="Unit of measure")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the dimension is active")


class DimensionUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Dimension name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Dimension description")
    scale: Optional[str] = Field(
        default=None, max_length=50, description="Scale code (list)")
    unit: Optional[str] = Field(
        default=None, max_length=100, description="Unit of measure")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the dimension is active")

# Metrics Models


class MetricBase(SQLModel):
    dimension: str = Field(max_length=50, foreign_key="dimensions.code")
    assignment: int = Field(foreign_key="assignments.id")
    value: str = Field(max_length=100)
    observation: Optional[str] = Field(default=None, max_length=500)
    measured_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Metric(MetricBase, table=True):
    __tablename__ = "metrics"
    id: Optional[int] = Field(default=None, primary_key=True)


class MetricCreate(SQLModel):
    dimension: str = Field(max_length=50, description="Dimension code")
    assignment: int = Field(description="Assignment ID")
    value: str = Field(max_length=100, description="Metric value")
    observation: Optional[str] = Field(
        default=None, max_length=500, description="Observation")
    measured_at: Optional[datetime] = Field(
        default=None, description="Measurement date")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the metric is active")


class MetricUpdate(SQLModel):
    value: Optional[str] = Field(
        default=None, max_length=100, description="Metric value")
    observation: Optional[str] = Field(
        default=None, max_length=500, description="Observation")
    measured_at: Optional[datetime] = Field(
        default=None, description="Measurement date")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the metric is active")
