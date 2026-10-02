"""Rotas de trilhas de treinamento (LearningPath, Fase 5). Escrita restrita a ADMIN;
leitura e recomendação liberadas a qualquer usuário autenticado. A recomendação é
sempre pessoal — nunca agregada, mesmo para ADMIN (ver LearningPathService.get_recommended).
Inscrição e conclusão de item também são sempre escopadas ao usuário atual, nunca
cross-user, mesmo para ADMIN — mesmo princípio. /recommended e /enrolled precisam
ficar declaradas antes de /{learning_path_id} para não serem capturadas pelo path
param (mesmo cuidado de ordering de analyses.py)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, get_learning_path_service, require_role
from app.models.user import User, UserRole
from app.schemas.learning_path import (
    CreateLearningPathRequest,
    EnrolledLearningPathSummary,
    EnrollmentResponse,
    LearningPathDetail,
    LearningPathSummary,
    UpdateLearningPathRequest,
)
from app.services.learning_path_service import (
    LearningPathItemNotFoundError,
    LearningPathService,
    NotEnrolledError,
)

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


@router.get("/enrolled", response_model=list[EnrolledLearningPathSummary])
def list_enrolled_learning_paths(
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(get_current_user),
):
    return service.list_enrolled(user=current_user)


@router.get("/{learning_path_id}", response_model=LearningPathDetail)
def get_learning_path(
    learning_path_id: uuid.UUID,
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(get_current_user),
):
    detail = service.get_detail(learning_path_id, current_user=current_user)
    if detail is None:
        raise HTTPException(status_code=404, detail="Trilha não encontrada.")
    return detail


@router.put("/{learning_path_id}", response_model=LearningPathDetail)
def update_learning_path(
    learning_path_id: uuid.UUID,
    request: UpdateLearningPathRequest,
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        detail = service.update(learning_path_id, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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


@router.post("/{learning_path_id}/enroll", response_model=EnrollmentResponse)
def enroll_in_learning_path(
    learning_path_id: uuid.UUID,
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(get_current_user),
):
    enrollment = service.enroll(learning_path_id=learning_path_id, user=current_user)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Trilha não encontrada.")
    return enrollment


@router.post("/{learning_path_id}/items/{item_id}/complete", status_code=204)
def complete_learning_path_item(
    learning_path_id: uuid.UUID,
    item_id: uuid.UUID,
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(get_current_user),
):
    try:
        service.mark_item_complete(
            learning_path_id=learning_path_id, item_id=item_id, user=current_user
        )
    except NotEnrolledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LearningPathItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{learning_path_id}/items/{item_id}/complete", status_code=204)
def uncomplete_learning_path_item(
    learning_path_id: uuid.UUID,
    item_id: uuid.UUID,
    service: LearningPathService = Depends(get_learning_path_service),
    current_user: User = Depends(get_current_user),
):
    service.unmark_item_complete(learning_path_id=learning_path_id, item_id=item_id, user=current_user)
