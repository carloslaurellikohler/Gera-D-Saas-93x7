from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_dashboard_service
from app.models.user import User
from app.schemas.dashboard import DashboardStatsResponse, Period
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def get_stats(
    period: Period = Query("6m"),
    service: DashboardService = Depends(get_dashboard_service),
    current_user: User = Depends(get_current_user),
):
    # O escopo (próprias análises vs. globais) vem sempre do usuário autenticado —
    # nunca de um parâmetro do cliente, para que um usuário comum não possa forjar
    # acesso a agregados de outra pessoa.
    return service.get_stats(current_user=current_user, period=period)
