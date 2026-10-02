"""Orquestração de materiais de apoio da biblioteca (Content, Fase 5)."""

from __future__ import annotations

import uuid

from app.core.constants import CriterionKey
from app.models.content import Content, ContentKind
from app.models.user import User
from app.repositories.content_repository import ContentRepository
from app.services.content_validation import validate_content_upload
from app.services.validation import sanitize_filename
from app.storage.base import FileStorage


class ContentStillReferencedError(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "Este material ainda está vinculado a uma ou mais trilhas de treinamento; "
            "remova-o das trilhas antes de excluí-lo."
        )


class ContentService:
    def __init__(self, repo: ContentRepository, storage: FileStorage, max_upload_mb: int) -> None:
        self.repo = repo
        self.storage = storage
        self.max_upload_mb = max_upload_mb

    def create(
        self,
        *,
        title: str,
        description: str | None,
        criterion_key: CriterionKey | None,
        kind: ContentKind,
        file_name: str | None,
        file_content: bytes | None,
        external_url: str | None,
        uploaded_by: User,
    ) -> Content:
        content_id = uuid.uuid4()
        resolved_file_path: str | None = None
        resolved_url: str | None = None

        if kind == ContentKind.FILE:
            if not file_name or file_content is None:
                raise ValueError("Upload de arquivo é obrigatório para materiais do tipo FILE.")
            validate_content_upload(
                file_name=file_name, content=file_content, max_upload_mb=self.max_upload_mb
            )
            safe_name = sanitize_filename(file_name)
            resolved_file_path = self.storage.save_bytes(f"content/{content_id}/{safe_name}", file_content)
        else:
            if not external_url:
                raise ValueError("URL externa é obrigatória para materiais do tipo LINK.")
            resolved_url = external_url

        content = Content(
            id=content_id,
            title=title,
            description=description,
            criterion_key=criterion_key,
            kind=kind,
            file_path=resolved_file_path,
            external_url=resolved_url,
            uploaded_by_id=uploaded_by.id,
        )
        return self.repo.create(content)

    def list_all(self, *, criterion_key: CriterionKey | None = None) -> list[Content]:
        return self.repo.list(criterion_key=criterion_key)

    def get(self, content_id: uuid.UUID) -> Content | None:
        return self.repo.get(content_id)

    def delete(self, content_id: uuid.UUID) -> None:
        content = self.repo.get(content_id)
        if content is None:
            return
        if self.repo.is_referenced_by_learning_path(content_id):
            raise ContentStillReferencedError()
        if content.kind == ContentKind.FILE and content.file_path:
            self.storage.delete(content.file_path)
        self.repo.delete(content_id)
