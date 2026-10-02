"""Rotas da biblioteca de materiais de apoio (Content, Fase 5). Escrita restrita a
ADMIN (biblioteca curada); leitura liberada a qualquer usuário autenticado."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.api.deps import get_content_service, get_current_user, require_role
from app.core.constants import CriterionKey
from app.models.content import ContentKind
from app.models.user import User, UserRole
from app.schemas.content import ContentResponse
from app.services.content_service import ContentService, ContentStillReferencedError
from app.services.content_validation import (
    ContentFileTooLargeError,
    CorruptedContentFileError,
    UnsupportedContentFileTypeError,
)

router = APIRouter(prefix="/content", tags=["content"])


@router.post("", response_model=ContentResponse, status_code=201)
def create_content(
    title: str = Form(...),
    description: str | None = Form(None),
    criterion_key: CriterionKey | None = Form(None),
    kind: ContentKind = Form(...),
    file: UploadFile | None = File(None),
    external_url: str | None = Form(None),
    service: ContentService = Depends(get_content_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        content = service.create(
            title=title,
            description=description,
            criterion_key=criterion_key,
            kind=kind,
            file_name=file.filename if file else None,
            file_content=file.file.read() if file else None,
            external_url=external_url,
            uploaded_by=current_user,
        )
    except (
        UnsupportedContentFileTypeError,
        ContentFileTooLargeError,
        CorruptedContentFileError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return content


@router.get("", response_model=list[ContentResponse])
def list_content(
    criterion_key: CriterionKey | None = Query(None),
    service: ContentService = Depends(get_content_service),
    current_user: User = Depends(get_current_user),
):
    return service.list_all(criterion_key=criterion_key)


@router.get("/{content_id}", response_model=ContentResponse)
def get_content(
    content_id: uuid.UUID,
    service: ContentService = Depends(get_content_service),
    current_user: User = Depends(get_current_user),
):
    content = service.get(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Material não encontrado.")
    return content


@router.delete("/{content_id}", status_code=204)
def delete_content(
    content_id: uuid.UUID,
    service: ContentService = Depends(get_content_service),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        service.delete(content_id)
    except ContentStillReferencedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
