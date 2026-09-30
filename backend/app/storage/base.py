"""Abstração de armazenamento de arquivos. Implementação local hoje (Docker volume),
trocável por S3/object storage depois sem tocar a regra de negócio (services/pipelines)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class FileStorage(Protocol):
    def save_bytes(self, key: str, content: bytes) -> str:
        """Persiste o conteúdo sob `key` e retorna a referência de storage (== key hoje)."""
        ...

    def save_file(self, source_path: Path, key: str) -> str:
        """Copia um arquivo já existente em disco para `key` e retorna a referência."""
        ...

    def path(self, ref: str) -> Path:
        """Resolve uma referência de storage para um Path local legível."""
        ...

    def read(self, ref: str) -> bytes:
        ...

    def delete(self, ref: str) -> None:
        ...
