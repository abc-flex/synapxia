import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Assignment, AssignmentCreate, AssignmentUpdate, Team, Role
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@router.get("/", response_model=List[Assignment])
def get_all(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Assignment]:
    """
    List all assignments with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    assignments = session.exec(select(Assignment).where(Assignment.is_active == True)
                               .offset(skip).limit(limit)
                               .order_by(Assignment.created_at.desc())).all()
    return assignments


@router.get("/{id}", response_model=Assignment)
def get(id: int, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Get an assignment by its ID.

    - **id**: Unique assignment ID
    """
    assignment = session.get(Assignment, id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    elif not assignment.is_active:
        raise HTTPException(status_code=400, detail=f"Assignment with id '{id}' is inactive")
    return assignment


@router.post("/", response_model=Assignment, status_code=201)
def create(assignment: AssignmentCreate, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Create a new assignment.

    - **team**: Team code (optional)
    - **user_id**: User ID (required)
    - **role**: Role code (required)
    - **observation**: Observation (optional)
    - **valid_from**: Start date of validity (optional, default: now)
    - **valid_to**: End date of validity (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the team exists if provided
    if assignment.team:
        team = session.get(Team, assignment.team)
        if not team:
            raise HTTPException(
                status_code=400,
                detail=f"Team with code '{assignment.team}' does not exist"
            )

    # Validate that the role exists
    role = session.get(Role, assignment.role)
    if not role:
        raise HTTPException(
            status_code=400,
            detail=f"Role with code '{assignment.role}' does not exist"
        )

    # Si no se proporciona valid_from, usar ahora
    data = assignment.model_dump()
    if not data.get('valid_from'):
        data['valid_from'] = datetime.utcnow()

    try:
        db = Assignment.model_validate(data)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Assignment created: {db.id}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating assignment: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error creating assignment"
        )


@router.put("/{id}", response_model=Assignment)
def update(id: int, update: AssignmentUpdate, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Update an existing assignment.

    - **id**: Unique assignment ID to update
    - Only provided fields are updated
    """
    assignment = session.get(Assignment, id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Validate that the team exists if provided
    if update.team is not None:
        team = session.get(Team, update.team)
        if not team:
            raise HTTPException(
                status_code=400,
                detail=f"Team with code '{update.team}' does not exist"
            )

    # Validate that the role exists if provided
    if update.role is not None:
        role = session.get(Role, update.role)
        if not role:
            raise HTTPException(
                status_code=400,
                detail=f"Role with code '{update.role}' does not exist"
            )

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(assignment, key, value)

    # Update timestamp
    assignment.updated_at = datetime.utcnow()

    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    logger.info(f"Assignment updated: {id}")
    return assignment


@router.delete("/{id}", response_model=Assignment, status_code=200)
def delete(id: int, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Delete an assignment (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **id**: Unique assignment ID to delete
    """
    assignment = session.get(Assignment, id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check if already inactive
    if not assignment.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Assignment with id '{id}' is already inactive"
        )

    # Logical delete: update is_active to False
    assignment.is_active = False
    assignment.updated_at = datetime.utcnow()

    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    logger.info(f"Assignment deactivated (logical delete): {id}")
    return assignment
