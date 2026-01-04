"""Models for Collaboration module"""
from sqlmodel import Field, SQLModel, Column, String, ForeignKey
from typing import Optional
from datetime import datetime, date

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
    code: str = Field(max_length=50, description="Código único del equipo")
    name: str = Field(max_length=100, description="Nombre del equipo")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción del equipo")
    lead: Optional[int] = Field(default=None, description="ID del líder del equipo")
    chat_channel_url: Optional[str] = Field(default=None, max_length=500, description="URL del canal de chat")
    kanban_board_url: Optional[str] = Field(default=None, max_length=500, description="URL del tablero Kanban")
    is_active: Optional[bool] = Field(default=True, description="Indica si el equipo está activo")

class TeamUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre del equipo")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción del equipo")
    lead: Optional[int] = Field(default=None, description="ID del líder del equipo")
    chat_channel_url: Optional[str] = Field(default=None, max_length=500, description="URL del canal de chat")
    kanban_board_url: Optional[str] = Field(default=None, max_length=500, description="URL del tablero Kanban")
    is_active: Optional[bool] = Field(default=None, description="Indica si el equipo está activo")

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
    team: Optional[str] = Field(default=None, max_length=50, description="Código del equipo")
    user_id: int = Field(description="ID del usuario")
    role: str = Field(max_length=50, description="Código del rol")
    observation: Optional[str] = Field(default=None, max_length=500, description="Observación")
    valid_from: Optional[datetime] = Field(default=None, description="Fecha de inicio de validez")
    valid_to: Optional[datetime] = Field(default=None, description="Fecha de fin de validez")
    is_active: Optional[bool] = Field(default=True, description="Indica si la asignación está activa")

class AssignmentUpdate(SQLModel):
    team: Optional[str] = Field(default=None, max_length=50, description="Código del equipo")
    role: Optional[str] = Field(default=None, max_length=50, description="Código del rol")
    observation: Optional[str] = Field(default=None, max_length=500, description="Observación")
    valid_from: Optional[datetime] = Field(default=None, description="Fecha de inicio de validez")
    valid_to: Optional[datetime] = Field(default=None, description="Fecha de fin de validez")
    is_active: Optional[bool] = Field(default=None, description="Indica si la asignación está activa")

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
    code: str = Field(max_length=50, description="Código único del proyecto")
    name: str = Field(max_length=100, description="Nombre del proyecto")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción del proyecto")
    team: Optional[str] = Field(default=None, max_length=50, description="Código del equipo")
    repo_url: Optional[str] = Field(default=None, max_length=500, description="URL del repositorio")
    status: str = Field(max_length=100, description="Estado del proyecto")
    start_date: Optional[date] = Field(default=None, description="Fecha de inicio")
    end_date: Optional[date] = Field(default=None, description="Fecha de fin")
    is_active: Optional[bool] = Field(default=True, description="Indica si el proyecto está activo")

class ProjectUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre del proyecto")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción del proyecto")
    team: Optional[str] = Field(default=None, max_length=50, description="Código del equipo")
    repo_url: Optional[str] = Field(default=None, max_length=500, description="URL del repositorio")
    status: Optional[str] = Field(default=None, max_length=100, description="Estado del proyecto")
    start_date: Optional[date] = Field(default=None, description="Fecha de inicio")
    end_date: Optional[date] = Field(default=None, description="Fecha de fin")
    is_active: Optional[bool] = Field(default=None, description="Indica si el proyecto está activo")

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
    code: str = Field(max_length=50, description="Código único de la dimensión")
    name: str = Field(max_length=100, description="Nombre de la dimensión")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción de la dimensión")
    scale: Optional[str] = Field(default=None, max_length=50, description="Código de la escala (lista)")
    unit: Optional[str] = Field(default=None, max_length=100, description="Unidad de medida")
    is_active: Optional[bool] = Field(default=True, description="Indica si la dimensión está activa")

class DimensionUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre de la dimensión")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción de la dimensión")
    scale: Optional[str] = Field(default=None, max_length=50, description="Código de la escala (lista)")
    unit: Optional[str] = Field(default=None, max_length=100, description="Unidad de medida")
    is_active: Optional[bool] = Field(default=None, description="Indica si la dimensión está activa")

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
    dimension: str = Field(max_length=50, description="Código de la dimensión")
    assignment: int = Field(description="ID de la asignación")
    value: str = Field(max_length=100, description="Valor de la métrica")
    observation: Optional[str] = Field(default=None, max_length=500, description="Observación")
    measured_at: Optional[datetime] = Field(default=None, description="Fecha de medición")
    is_active: Optional[bool] = Field(default=True, description="Indica si la métrica está activa")

class MetricUpdate(SQLModel):
    value: Optional[str] = Field(default=None, max_length=100, description="Valor de la métrica")
    observation: Optional[str] = Field(default=None, max_length=500, description="Observación")
    measured_at: Optional[datetime] = Field(default=None, description="Fecha de medición")
    is_active: Optional[bool] = Field(default=None, description="Indica si la métrica está activa")
