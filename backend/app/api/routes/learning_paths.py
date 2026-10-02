"""Rotas de trilhas de treinamento (LearningPath, Fase 5). Escrita restrita a ADMIN;
leitura e recomendação liberadas a qualquer usuário autenticado. A recomendação é
sempre pessoal — nunca agregada, mesmo para ADMIN (ver LearningPathService.get_recommended).
/recommended precisa ficar declarada antes de /{learning_path_id} para não ser
capturada pelo path param (mesmo cuidado de ordering de analyses.py)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, get_learning_path_service, require_role
from app.models.user import User, UserRole
from app.schemas.learning_path import (
    CreateLearningPathRequest,
    LearningPathDetail,
    LearningPathSummary,
)
from app.services.learning_path_service import LearningPathService

router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])


@router.post("", response_model=LearningPathDetail, status_code=201)
def create_learning_path(
    request: CreateLearningPathRequest,
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.create(request=request, created_by=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[LearningPathSummary])
def list_learning_paths(
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(get_current_user),
):
    return service.list_all()


@router.get("/recommended", response_model=list[LearningPathSummary])
def get_recommended_learning_paths(
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(get_current_user),
):
    return service.get_recommended(current_user=current_user)


@router.get("/{learning_path_id}", response_model=LearningPathDetail)
def get_learning_path(
    learning_path_id: uuid.UUID,
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(get_current_user),
):
    detail = service.get_detail(learning_path_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Trilha não encontrada.")
    return detail


@router.delete("/{learning_path_id}", status_code=204)
def delete_learning_path(
    learning_path_id: uuid.UUID,
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    service.delete(learning_path_id)
