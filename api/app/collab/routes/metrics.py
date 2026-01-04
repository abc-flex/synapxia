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
    Crear una nueva métrica.
    
    - **dimension**: Código de la dimensión (requerido)
    - **assignment**: ID de la asignación (requerido)
    - **value**: Valor de la métrica (requerido)
    - **observation**: Observación (opcional)
    - **measured_at**: Fecha de medición (opcional, default: ahora)
    - **is_active**: Estado activo/inactivo (default: True)
    """
    # Validar que la dimensión exista
    dimension = session.get(Dimension, metric.dimension)
    if not dimension:
        raise HTTPException(
            status_code=400,
            detail=f"Dimension with code '{metric.dimension}' does not exist"
        )
    
    # Validar que la asignación exista
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
    Listar todas las métricas con paginación.
    
    - **skip**: Número de registros a saltar (default: 0)
    - **limit**: Número máximo de registros a retornar (default: 100)
    """
    metrics = session.exec(select(Metric).offset(skip).limit(limit).order_by(Metric.measured_at.desc())).all()
    return metrics


@router.get("/{metric_id}", response_model=Metric)
def get_metric(metric_id: int, session: Session = Depends(get_db_session)) -> Metric:
    """
    Obtener una métrica por su ID.
    
    - **metric_id**: ID único de la métrica
    """
    metric = session.get(Metric, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric


@router.put("/{metric_id}", response_model=Metric)
def update_metric(metric_id: int, metric_update: MetricUpdate, session: Session = Depends(get_db_session)) -> Metric:
    """
    Actualizar una métrica existente.
    
    - **metric_id**: ID único de la métrica a actualizar
    - Solo se actualizan los campos proporcionados
    """
    metric = session.get(Metric, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    update_data = metric_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(metric, key, value)
    
    # Actualizar timestamp
    metric.updated_at = datetime.utcnow()

    session.add(metric)
    session.commit()
    session.refresh(metric)
    logger.info(f"Metric updated: {metric_id}")
    return metric


@router.delete("/{metric_id}", response_model=Metric, status_code=200)
def delete_metric(metric_id: int, session: Session = Depends(get_db_session)) -> Metric:
    """
    Eliminar una métrica (borrado lógico).
    
    Realiza un borrado lógico estableciendo is_active=False en lugar de eliminar el registro.
    
    - **metric_id**: ID único de la métrica a eliminar
    """
    metric = session.get(Metric, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    # Verificar si ya está inactiva
    if not metric.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Metric with id '{metric_id}' is already inactive"
        )

    # Borrado lógico: actualizar is_active a False
    metric.is_active = False
    metric.updated_at = datetime.utcnow()
    
    session.add(metric)
    session.commit()
    session.refresh(metric)
    logger.info(f"Metric deactivated (logical delete): {metric_id}")
    return metric

