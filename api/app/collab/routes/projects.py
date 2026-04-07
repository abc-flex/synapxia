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


@router.get("/", response_model=List[Project])
def get_all(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Project]:
    """
    List all projects with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    projects = session.exec(select(Project).where(Project.is_active == True)
                            .offset(skip).limit(limit)
                            .order_by(Project.name)).all()
    return projects


@router.get("/{code}", response_model=Project)
def get(code: str, session: Session = Depends(get_db_session)) -> Project:
    """
    Get a project by its code.

    - **code**: Unique project code
    """
    project = session.get(Project, code)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.is_active:
        raise HTTPException(status_code=400, detail=f"Project with code '{code}' is inactive")
    return project


@router.post("/", response_model=Project, status_code=201)
def create(project: ProjectCreate, session: Session = Depends(get_db_session)) -> Project:
    """
    Create a new project.

    - **code**: Unique project code (required)
    - **name**: Project name (required)
    - **status**: Project status (required)
    - **description**: Optional description
    - **team**: Team code (optional)
    - **repo_url**: Repository URL (optional)
    - **start_date**: Start date (optional)
    - **end_date**: End date (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the code does not exist
    existing = session.get(Project, project.code)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Project with code '{project.code}' already exists"
        )

    # Validate that the team exists if provided
    if project.team:
        team = session.get(Team, project.team)
        if not team:
            raise HTTPException(
                status_code=400,
                detail=f"Team with code '{project.team}' does not exist"
            )

    try:
        db = Project.model_validate(project)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Project created: {project.code}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating project {project.code}: {e}")
        raise HTTPException(
            status_code=409,
            detail=f"Project with code '{project.code}' already exists"
        )


@router.put("/{code}", response_model=Project)
def update(code: str, update: ProjectUpdate, session: Session = Depends(get_db_session)) -> Project:
    """
    Update an existing project.

    - **code**: Unique project code to update
    - Only provided fields are updated
    """
    project = session.get(Project, code)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate that the team exists if provided
    if update.team is not None:
        team = session.get(Team, update.team)
        if not team:
            raise HTTPException(
                status_code=400,
                detail=f"Team with code '{update.team}' does not exist"
            )

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    # Update timestamp
    project.updated_at = datetime.utcnow()

    session.add(project)
    session.commit()
    session.refresh(project)
    logger.info(f"Project updated: {code}")
    return project


@router.delete("/{code}", response_model=Project, status_code=200)
def delete(code: str, session: Session = Depends(get_db_session)) -> Project:
    """
    Delete a project (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **code**: Unique project code to delete
    """
    project = session.get(Project, code)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if already inactive
    if not project.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Project with code '{code}' is already inactive"
        )

    # Logical delete: update is_active to False
    project.is_active = False
    project.updated_at = datetime.utcnow()

    session.add(project)
    session.commit()
    session.refresh(project)
    logger.info(f"Project deactivated (logical delete): {code}")
    return project
