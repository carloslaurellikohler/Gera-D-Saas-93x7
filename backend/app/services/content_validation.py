"""Validação de upload de materiais de apoio da biblioteca (Content, Fase 5) — lista de
extensões e assinatura binária próprias, distintas dos uploads de análise
(app/services/validation.py, hardcoded para os 4 formatos de transcrição/mídia de
interação). v1 restrito a PDF; vídeo-aula entra como link externo, não upload."""

from __future__ import annotations

from pathlib import PurePosixPath

from app.core.constants import ALLOWED_CONTENT_EXTENSIONS


class UnsupportedContentFileTypeError(ValueError):
    def __init__(self, extension: str) -> None:
        self.extension = extension
        super().__init__(
            f"Tipo de arquivo não suportado: {extension!r}. "
            f"Formatos aceitos: {', '.join(sorted(ALLOWED_CONTENT_EXTENSIONS))}."
        )


class ContentFileTooLargeError(ValueError):
    def __init__(self, size_mb: float, max_mb: int) -> None:
        self.size_mb = size_mb
        self.max_mb = max_mb
        super().__init__(f"Arquivo de {size_mb:.1f}MB excede o limite de {max_mb}MB.")


class CorruptedContentFileError(ValueError):
    def __init__(self, extension: str) -> None:
        super().__init__(
            f"O conteúdo do arquivo não corresponde a um {extension} válido "
            "(assinatura binária não reconhecida)."
        )


def _looks_like_pdf(content: bytes) -> bool:
    return content[:5] == b"%PDF-"


_SIGNATURE_CHECKS = {"pdf": _looks_like_pdf}


def validate_content_upload(*, file_name: str, content: bytes, max_upload_mb: int) -> None:
    """Levanta um erro de validação se o upload não for aceitável; não retorna nada."""
    size_mb = len(content) / (1024 * 1024)
    if size_mb > max_upload_mb:
        raise ContentFileTooLargeError(size_mb, max_upload_mb)

    extension = PurePosixPath(file_name.lower()).suffix
    if extension not in ALLOWED_CONTENT_EXTENSIONS:
        raise UnsupportedContentFileTypeError(extension)

    input_type = ALLOWED_CONTENT_EXTENSIONS[extension]
    if not _SIGNATURE_CHECKS[input_type](content):
        raise CorruptedContentFileError(extension)
