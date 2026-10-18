"""Rotas da configuração operacional editável em runtime. Tudo restrito a ADMIN.

`require_role(UserRole.ADMIN)` devolve 403, e não o 404 do padrão dono-ou-ADMIN: aquele padrão
existe para não revelar a existência de IDs de outro usuário, o que não se aplica a uma
configuração global — mesmo argumento das rotas do FinAI.

O banco vence o `.env`: o que for salvo aqui passa a valer na próxima análise/pergunta, sem
restart. `POST /test-model` chama a OpenAI de verdade e **não** é contabilizado no FinAI (o
porquê está em services/model_probe.py).

Não há DELETE: a configuração é uma linha única que sempre existe conceitualmente. Remover a
linha à mão devolve o sistema aos defaults do ambiente, em silêncio — é o fallback por design.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_runtime_settings_service, require_role
from app.models.user import User, UserRole
from app.schemas.runtime_settings import (
    ModelTestRequest,
    ModelTestResponse,
    RuntimeSettingsIn,
    RuntimeSettingsResponse,
)
from app.services.model_probe import ModelProbeError
from app.services.runtime_settings_service import RuntimeSettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=RuntimeSettingsResponse)
def get_runtime_settings(
    service: RuntimeSettingsService = Depends(get_runtime_settings_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return service.get_config()


@router.put("", response_model=RuntimeSettingsResponse)
def update_runtime_settings(
    payload: RuntimeSettingsIn,
    service: RuntimeSettingsService = Depends(get_runtime_settings_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return service.update_config(current_user=current_user, payload=payload)


@router.post("/test-model", response_model=ModelTestResponse)
def test_model(
    payload: ModelTestRequest,
    service: RuntimeSettingsService = Depends(get_runtime_settings_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Valida um nome de modelo digitado antes de salvar. Nada é persistido aqui."""
    try:
        service.test_model(model=payload.model_name, temperature=payload.temperature)
    except ModelProbeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ModelTestResponse(ok=True, message="O modelo respondeu normalmente.")
