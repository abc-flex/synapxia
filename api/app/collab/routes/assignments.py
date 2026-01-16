import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Assignment, AssignmentCreate, AssignmentUpdate, Team
from ...admin.internal.models import Role
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@router.post("/", response_model=Assignment, status_code=201)
def create_assignment(assignment: AssignmentCreate, session: Session = Depends(get_db_session)) -> Assignment:
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
    assignment_data = assignment.model_dump()
    if not assignment_data.get('valid_from'):
        assignment_data['valid_from'] = datetime.utcnow()

    try:
        db_assignment = Assignment.model_validate(assignment_data)
        session.add(db_assignment)
        session.commit()
        session.refresh(db_assignment)
        logger.info(f"Assignment created: {db_assignment.id}")
        return db_assignment
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating assignment: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error creating assignment"
        )


@router.get("/", response_model=List[Assignment])
def list_assignments(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Assignment]:
    """
    List all assignments with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    assignments = session.exec(select(Assignment).offset(skip).limit(
        limit).order_by(Assignment.created_at.desc())).all()
    return assignments


@router.get("/{assignment_id}", response_model=Assignment)
def get_assignment(assignment_id: int, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Get an assignment by its ID.

    - **assignment_id**: Unique assignment ID
    """
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.put("/{assignment_id}", response_model=Assignment)
def update_assignment(assignment_id: int, assignment_update: AssignmentUpdate, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Update an existing assignment.

    - **assignment_id**: Unique assignment ID to update
    - Only provided fields are updated
    """
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Validate that the team exists if provided
    if assignment_update.team is not None:
        team = session.get(Team, assignment_update.team)
        if not team:
            raise HTTPException(
                status_code=400,
                detail=f"Team with code '{assignment_update.team}' does not exist"
            )

    # Validate that the role exists if provided
    if assignment_update.role is not None:
        role = session.get(Role, assignment_update.role)
        if not role:
            raise HTTPException(
                status_code=400,
                detail=f"Role with code '{assignment_update.role}' does not exist"
            )

    update_data = assignment_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(assignment, key, value)

    # Update timestamp
    assignment.updated_at = datetime.utcnow()

    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    logger.info(f"Assignment updated: {assignment_id}")
    return assignment


@router.delete("/{assignment_id}", response_model=Assignment, status_code=200)
def delete_assignment(assignment_id: int, session: Session = Depends(get_db_session)) -> Assignment:
    """
    Delete an assignment (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **assignment_id**: Unique assignment ID to delete
    """
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check if already inactive
    if not assignment.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Assignment with id '{assignment_id}' is already inactive"
        )

    # Logical delete: update is_active to False
    assignment.is_active = False
    assignment.updated_at = datetime.utcnow()

    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    logger.info(f"Assignment deactivated (logical delete): {assignment_id}")
    return assignment
