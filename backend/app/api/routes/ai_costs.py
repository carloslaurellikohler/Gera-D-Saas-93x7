"""Rotas do FinAI — custo de IA. Tudo restrito a ADMIN, leitura e escrita.

Custo de operação é informação sensível do negócio: `require_role(UserRole.ADMIN)` devolve
403, e não o 404 do padrão dono-ou-ADMIN — aquele padrão existe para não revelar a
existência de IDs de outro usuário, o que não se aplica a um agregado global.

Não há DELETE de preço: preço é trilha de auditoria do custo já congelado nos eventos.
Corrigir é cadastrar uma vigência nova ou editar a existente (e, se quiser reescrever o
histórico, chamar /recalculate explicitamente).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_ai_cost_service, require_role
from app.models.user import User, UserRole
from app.schemas.ai_cost import (
    AiCostConfigIn,
    AiCostConfigResponse,
    AiCostSummaryResponse,
    AiModelPriceIn,
    AiModelPriceResponse,
    AiRecalculateResponse,
    AiUsageEventPage,
    Feature,
    Operation,
    Period,
)
from app.services.ai_cost_service import (
    AiCostService,
    AiPriceNotFoundError,
    DuplicatePriceVigenciaError,
    InvalidPricePayloadError,
)

router = APIRouter(prefix="/ai-costs", tags=["ai-costs"])


@router.get("/summary", response_model=AiCostSummaryResponse)
def get_summary(
    period: Period = Query("30d"),
    service: AiCostService = Depends(get_ai_cost_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return service.get_summary(period=period)


@router.get("/events", response_model=AiUsageEventPage)
def list_events(
    period: Period = Query("30d"),
    feature: Feature | None = Query(None),
    operation: Operation | None = Query(None),
    model: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    analysis_id: uuid.UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: AiCostService = Depends(get_ai_cost_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return service.list_events(
        period=period,
        feature=feature,
        operation=operation,
        model=model,
        user_id=user_id,
        analysis_id=analysis_id,
        offset=offset,
        limit=limit,
    )


@router.get("/prices", response_model=list[AiModelPriceResponse])
def list_prices(
    service: AiCostService = Depends(get_ai_cost_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return service.list_prices()


@router.post("/prices", response_model=AiModelPriceResponse, status_code=201)
def create_price(
    payload: AiModelPriceIn,
    service: AiCostService = Depends(get_ai_cost_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.create_price(current_user=current_user, payload=payload)
    except DuplicatePriceVigenciaError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidPricePayloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/prices/{price_id}", response_model=AiModelPriceResponse)
def update_price(
    price_id: uuid.UUID,
    payload: AiModelPriceIn,
    service: AiCostService = Depends(get_ai_cost_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.update_price(price_id, current_user=current_user, payload=payload)
    except AiPriceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicatePriceVigenciaError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidPricePayloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/prices/{price_id}/recalculate", response_model=AiRecalculateResponse)
def recalculate_price(
    price_id: uuid.UUID,
    service: AiCostService = Depends(get_ai_cost_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Reescreve o custo congelado dos eventos afetados por esta vigência. Explícito de
    propósito — ver AiCostService.recalculate_price."""
    try:
        return AiRecalculateResponse(updated=service.recalculate_price(price_id))
    except AiPriceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/config", response_model=AiCostConfigResponse)
def get_config(
    service: AiCostService = Depends(get_ai_cost_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return service.get_config()


@router.put("/config", response_model=AiCostConfigResponse)
def update_config(
    payload: AiCostConfigIn,
    service: AiCostService = Depends(get_ai_cost_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return service.update_config(
        current_user=current_user,
        warn_threshold_pct=payload.warn_threshold_pct,
        usd_to_brl_rate=payload.usd_to_brl_rate,
        budget_month=payload.budget_month,
        monthly_budget_usd=payload.monthly_budget_usd,
    )
