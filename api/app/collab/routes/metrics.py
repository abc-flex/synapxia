import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import Metric, MetricCreate, MetricUpdate, Dimension, Assignment
from ..internal.dependencies import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.post("/", response_model=Metric, status_code=201)
def create_metric(metric: MetricCreate, session: Session = Depends(get_db_session)) -> Metric:
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
    metric_data = metric.model_dump()
    if not metric_data.get('measured_at'):
        metric_data['measured_at'] = datetime.utcnow()

    try:
        db_metric = Metric.model_validate(metric_data)
        session.add(db_metric)
        session.commit()
        session.refresh(db_metric)
        logger.info(f"Metric created: {db_metric.id}")
        return db_metric
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating metric: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error creating metric"
        )


@router.get("/", response_model=List[Metric])
def list_metrics(skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)) -> List[Metric]:
    """
    List all metrics with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    metrics = session.exec(select(Metric).offset(skip).limit(
        limit).order_by(Metric.measured_at.desc())).all()
    return metrics


@router.get("/{metric_id}", response_model=Metric)
def get_metric(metric_id: int, session: Session = Depends(get_db_session)) -> Metric:
    """
    Get a metric by its ID.

    - **metric_id**: Unique metric ID
    """
    metric = session.get(Metric, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric


@router.put("/{metric_id}", response_model=Metric)
def update_metric(metric_id: int, metric_update: MetricUpdate, session: Session = Depends(get_db_session)) -> Metric:
    """
    Update an existing metric.

    - **metric_id**: Unique metric ID to update
    - Only provided fields are updated
    """
    metric = session.get(Metric, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    update_data = metric_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(metric, key, value)

    # Update timestamp
    metric.updated_at = datetime.utcnow()

    session.add(metric)
    session.commit()
    session.refresh(metric)
    logger.info(f"Metric updated: {metric_id}")
    return metric


@router.delete("/{metric_id}", response_model=Metric, status_code=200)
def delete_metric(metric_id: int, session: Session = Depends(get_db_session)) -> Metric:
    """
    Delete a metric (logical delete).

    Performs a logical delete by setting is_active=False instead of deleting the record.

    - **metric_id**: Unique metric ID to delete
    """
    metric = session.get(Metric, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    # Check if already inactive
    if not metric.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Metric with id '{metric_id}' is already inactive"
        )

    # Logical delete: update is_active to False
    metric.is_active = False
    metric.updated_at = datetime.utcnow()

    session.add(metric)
    session.commit()
    session.refresh(metric)
    logger.info(f"Metric deactivated (logical delete): {metric_id}")
    return metric
