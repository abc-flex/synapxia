import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Project, ProjectCreate, ProjectUpdate, Team
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=Project, status_code=201)
def create_project(project: ProjectCreate, session: Session = Depends(get_db_session)) -> Project:
    """
    Crear un nuevo proyecto.
    
    - **code**: Código único del proyecto (requerido)
    - **name**: Nombre del proyecto (requerido)
    - **status**: Estado del proyecto (requerido)
    - **description**: Descripción opcional
    - **team**: Código del equipo (opcional)
    - **repo_url**: URL del repositorio (opcional)
    - **start_date**: Fecha de inicio (opcional)
    - **end_date**: Fecha de fin (opcional)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que el código no exista
    existing_project = session.get(Project, project.code)
    if existing_project:
        raise HTTPException(
            status_code=409,
            detail=f"Project with code '{project.code}' already exists"
        )
    
    # Validar que el equipo exista si se proporciona
    if project.team:
        team = session.get(Team, project.team)
        if not team:
            raise HTTPException(
                status_code=400,
                detail=f"Team with code '{project.team}' does not exist"
            )
    
    try:
        db_project = Project.model_validate(project)
        session.add(db_project)
        session.commit()
        session.refresh(db_project)
        logger.info(f"Project created: {project.code}")
        return db_project
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating project {project.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Project with code '{project.code}' already exists"
        )


@router.get("/", response_model=List[Project])
def list_projects(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Project]:
    """
    Listar todos los proyectos con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    projects = session.exec(select(Project).offset(skip).limit(limit).order_by(Project.name)).all()
    return projects


@router.get("/{project_code}", response_model=Project)
def get_project(project_code: str, session: Session = Depends(get_db_session)) -> Project:
    """
    Obtener un proyecto por su código.
    
    - **project_code**: Código único del proyecto
    """
    project = session.get(Project, project_code)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_code}", response_model=Project)
def update_project(project_code: str, project_update: ProjectUpdate, session: Session = Depends(get_db_session)) -> Project:
    """
    Actualizar un proyecto existente.
    
    - **project_code**: Código único del proyecto a actualizar
    - Solo se actualizan los campos proporcionados
    """
    project = session.get(Project, project_code)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validar que el equipo exista si se proporciona
    if project_update.team is not None:
        team = session.get(Team, project_update.team)
        if not team:
            raise HTTPException(
                status_code=400,
                detail=f"Team with code '{project_update.team}' does not exist"
            )

    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    
    # Actualizar timestamp
    project.updated_at = datetime.utcnow()

    session.add(project)
    session.commit()
    session.refresh(project)
    logger.info(f"Project updated: {project_code}")
    return project


@router.delete("/{project_code}", response_model=Project, status_code=200)
def delete_project(project_code: str, session: Session = Depends(get_db_session)) -> Project:
    """
    Eliminar un proyecto (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **project_code**: Código único del proyecto a eliminar
    """
    project = session.get(Project, project_code)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verificar si ya está inactivo
    if not project.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Project with code '{project_code}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    project.is_active = False
    project.updated_at = datetime.utcnow()
    
    session.add(project)
    session.commit()
    session.refresh(project)
    logger.info(f"Project deactivated (logical delete): {project_code}")
    return project

