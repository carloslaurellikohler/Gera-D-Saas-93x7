"""Rotas de metodologia/calibração versionada (Fase 7). Escrita restrita a ADMIN;
leitura liberada a qualquer usuário autenticado."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, get_methodology_service, require_role
from app.models.user import User, UserRole
from app.schemas.methodology import (
    CreateMethodologyDraftRequest,
    MethodologyDetail,
    MethodologyDraftIn,
    MethodologyPromptPreview,
    MethodologySummary,
)
from app.services.methodology_service import (
    MethodologyAnchorMismatchError,
    MethodologyBandCoverageError,
    MethodologyCalibratorMismatchError,
    MethodologyCategoryMismatchError,
    MethodologyNotDraftError,
    MethodologyNotFoundError,
    MethodologyService,
    MethodologyStillReferencedError,
    MethodologyWeightSumError,
)

# Toda falha de validação semântica do publish é conflito de estado (409), não 422: o
# payload é sintaticamente válido, o que não bate é a consistência da versão.
_PUBLISH_CONFLICTS = (
    MethodologyNotDraftError,
    MethodologyCategoryMismatchError,
    MethodologyCalibratorMismatchError,
    MethodologyAnchorMismatchError,
    MethodologyWeightSumError,
    MethodologyBandCoverageError,
)

router = APIRouter(prefix="/methodology", tags=["methodology"])


@router.get("", response_model=list[MethodologySummary])
def list_methodologies(
    service: MethodologyService = Depends(get_methodology_service),
    current_user: User = Depends(get_current_user),
):
    return service.list_summaries()


@router.get("/published", response_model=MethodologyDetail)
def get_published_methodology(
    service: MethodologyService = Depends(get_methodology_service),
    current_user: User = Depends(get_current_user),
):
    methodology = service.get_published()
    if methodology is None:
        raise HTTPException(status_code=404, detail="Nenhuma metodologia publicada.")
    return methodology


@router.get("/{methodology_id}", response_model=MethodologyDetail)
def get_methodology(
    methodology_id: uuid.UUID,
    service: MethodologyService = Depends(get_methodology_service),
    current_user: User = Depends(get_current_user),
):
    methodology = service.get(methodology_id)
    if methodology is None:
        raise HTTPException(status_code=404, detail="Versão de metodologia não encontrada.")
    return methodology


@router.get("/{methodology_id}/prompt-preview", response_model=MethodologyPromptPreview)
def get_methodology_prompt_preview(
    methodology_id: uuid.UUID,
    service: MethodologyService = Depends(get_methodology_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Mostra o system prompt exato que a engine receberá com esta versão — é como o
    ADMIN confere a régua compilada (âncoras, exemplos, elegibilidade) antes de publicar,
    em vez de descobrir o resultado numa análise paga."""
    methodology = service.get(methodology_id)
    if methodology is None:
        raise HTTPException(status_code=404, detail="Versão de metodologia não encontrada.")
    try:
        return service.build_prompt_preview(methodology)
    except KeyError as exc:
        # content incompleto numa versão antiga, anterior à validação de MethodologyContentIn
        raise HTTPException(
            status_code=409,
            detail=f"Esta versão não tem o campo {exc} e não consegue gerar o prompt.",
        ) from exc


@router.post("/draft", response_model=MethodologyDetail, status_code=201)
def create_methodology_draft(
    request: CreateMethodologyDraftRequest,
    service: MethodologyService = Depends(get_methodology_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.create_draft(from_id=request.from_id, actor=current_user)
    except MethodologyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{methodology_id}", response_model=MethodologyDetail)
def update_methodology_draft(
    methodology_id: uuid.UUID,
    payload: MethodologyDraftIn,
    service: MethodologyService = Depends(get_methodology_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.update_draft(methodology_id, payload)
    except MethodologyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MethodologyNotDraftError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{methodology_id}/publish", response_model=MethodologyDetail)
def publish_methodology(
    methodology_id: uuid.UUID,
    service: MethodologyService = Depends(get_methodology_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.publish(methodology_id)
    except MethodologyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except _PUBLISH_CONFLICTS as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{methodology_id}", status_code=204)
def delete_methodology_draft(
    methodology_id: uuid.UUID,
    service: MethodologyService = Depends(get_methodology_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        service.delete_draft(methodology_id)
    except (MethodologyNotDraftError, MethodologyStillReferencedError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
