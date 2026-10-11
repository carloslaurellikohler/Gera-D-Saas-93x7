"""Rotas de gestão administrativa de usuários (criar, editar, inativar,
reativar). Todas as operações são restritas a ADMIN — não há autocadastro."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_user_service, require_role
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import AdminResetPasswordIn, UserCreateIn, UserResponse, UserUpdateIn
from app.services.user_service import (
    CannotDeactivateSelfError,
    EmailAlreadyExistsError,
    GestorComEquipeError,
    InvalidManagerAssignmentError,
    UserNotFoundError,
    UserService,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    role: UserRole | None = Query(None),
    status: UserStatus | None = Query(None),
    search: str | None = Query(None),
    manager_id: uuid.UUID | None = Query(None),
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return service.list_users(role=role, status=status, search=search, manager_id=manager_id)


@router.get("/me/team", response_model=list[UserResponse])
def list_my_team(
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.GESTOR)),
):
    return service.list_subordinates(current_user.id)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreateIn,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.create_user(**payload.model_dump())
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidManagerAssignmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateIn,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.update_user(user_id, **payload.model_dump())
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidManagerAssignmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GestorComEquipeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.set_status(user_id, new_status=UserStatus.ACTIVE, current_user=current_user)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.set_status(user_id, new_status=UserStatus.INACTIVE, current_user=current_user)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CannotDeactivateSelfError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GestorComEquipeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{user_id}/reset-password", response_model=UserResponse)
def reset_password(
    user_id: uuid.UUID,
    payload: AdminResetPasswordIn,
    service: UserService = Depends(get_user_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        return service.reset_password(user_id, new_password=payload.password)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
