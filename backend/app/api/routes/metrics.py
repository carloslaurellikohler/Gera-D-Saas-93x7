from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_metrics_service
from app.models.user import User
from app.schemas.metrics import MetricsEvolutionResponse, Period
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/evolution", response_model=MetricsEvolutionResponse)
def get_evolution(
    period: Period = Query("6m"),
    service: MetricsService = Depends(get_metrics_service),
    current_user: User = Depends(get_current_user),
) -> MetricsEvolutionResponse:
    # Escopo sempre derivado do usuário autenticado — nunca de query param
    # (mesmo contrato do /dashboard/stats).
    return service.get_evolution(current_user=current_user, period=period)
