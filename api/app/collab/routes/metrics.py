import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Metric, MetricCreate, MetricUpdate, Dimension, Assignment
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/", response_model=List[Metric])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "METRICS", can_edit=False))
) -> List[Metric]:
    """
    List all metrics with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    metrics = session.exec(select(Metric).where(Metric.is_active == True)
                           .offset(skip).limit(limit)
                           .order_by(Metric.measured_at.desc())).all()
    return metrics


@router.get("/{id}", response_model=Metric)
def get(
    id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "METRICS", can_edit=False))
) -> Metric:
    """
    Get a metric by its ID.

    - **id**: Unique metric ID
    """
    metric = session.get(Metric, id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    elif not metric.is_active:
        raise HTTPException(status_code=400, detail=f"Metric with id '{id}' is inactive")
    return metric


@router.post("/", response_model=Metric, status_code=201)
def create(
    metric: MetricCreate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "METRICS", can_edit=True))
) -> Metric:
    """
    Create a new metric.

    - **dimension**: Dimension code (required)
    - **assignment**: Assignment ID (required)
    - **value**: Metric value (required)
    - **observation**: Observation (optional)
    - **measured_at**: Measurement date (optional, default: now)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the dimension exists
    dimension = session.get(Dimension, metric.dimension)
    if not dimension:
        raise HTTPException(
            status_code=400,
            detail=f"Dimension with code '{metric.dimension}' does not exist"
        )

    # Validate that the assignment exists
    assignment = session.get(Assignment, metric.assignment)
    if not assignment:
        raise HTTPException(
            status_code=400,
            detail=f"Assignment with id '{metric.assignment}' does not exist"
        )

    # Si no se proporciona measured_at, usar ahora
    data = metric.model_dump()
    if not data.get('measured_at'):
        data['measured_at'] = datetime.utcnow()

    try:
        db = Metric.model_validate(data)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(f"Metric created: {db.id}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating metric: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error creating metric"
        )


@router.put("/{id}", response_model=Metric)
def update(
    id: int, update: MetricUpdate, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "METRICS", can_edit=True))
) -> Metric:
    """
    Update an existing metric.

    - **id**: Unique metric ID to update
    - Only provided fields are updated
    """
    metric = session.get(Metric, id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(metric, key, value)

    # Update timestamp
    metric.updated_at = datetime.utcnow()

    session.add(metric)
    session.commit()
    session.refresh(metric)
    logger.info(f"Metric updated: {id}")
    return metric


@router.delete("/{id}", response_model=Metric, status_code=200)
def delete(
    id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("COLLAB", "METRICS", can_edit=True))
) -> Metric:
    """
    Delete a metric (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **id**: Unique metric ID to delete
    """
    metric = session.get(Metric, id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    # Check if already inactive
    if not metric.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Metric with id '{id}' is already inactive"
        )

    # Logical delete: update is_active to False
    metric.is_active = False
    metric.updated_at = datetime.utcnow()

    session.add(metric)
    session.commit()
    session.refresh(metric)
    logger.info(f"Metric deactivated (logical delete): {id}")
    return metric
