"""Validação de upload: extensão + assinatura binária real do conteúdo (não confiamos só
na extensão declarada pelo cliente) + sanitização de nome de arquivo."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from app.core.constants import ALLOWED_EXTENSIONS


class UnsupportedFileTypeError(ValueError):
    def __init__(self, extension: str) -> None:
        self.extension = extension
        super().__init__(
            f"Tipo de arquivo não suportado: {extension!r}. "
            f"Formatos aceitos: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )


class FileTooLargeError(ValueError):
    def __init__(self, size_mb: float, max_mb: int) -> None:
        self.size_mb = size_mb
        self.max_mb = max_mb
        super().__init__(f"Arquivo de {size_mb:.1f}MB excede o limite de {max_mb}MB.")


class CorruptedFileError(ValueError):
    def __init__(self, extension: str) -> None:
        super().__init__(
            f"O conteúdo do arquivo não corresponde a um {extension} válido "
            "(assinatura binária não reconhecida)."
        )


def sanitize_filename(file_name: str) -> str:
    name = PurePosixPath(file_name.replace("\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "arquivo"
    return name[:200]


def _looks_like_docx(content: bytes) -> bool:
    return content[:4] == b"PK\x03\x04"  # .docx é um ZIP (Office Open XML)


def _looks_like_txt(content: bytes) -> bool:
    sample = content[:4096]
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        try:
            sample.decode("latin-1")
        except UnicodeDecodeError:
            return False
    return True


def _looks_like_mp3(content: bytes) -> bool:
    if content[:3] == b"ID3":
        return True
    return len(content) >= 2 and content[0] == 0xFF and (content[1] & 0xE0) == 0xE0


def _looks_like_mp4(content: bytes) -> bool:
    return content[4:8] == b"ftyp"


_SIGNATURE_CHECKS = {
    "docx": _looks_like_docx,
    "txt": _looks_like_txt,
    "mp3": _looks_like_mp3,
    "mp4": _looks_like_mp4,
}


def _validate(*, file_name: str, size_bytes: int, header: bytes, max_upload_mb: int) -> str:
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > max_upload_mb:
        raise FileTooLargeError(size_mb, max_upload_mb)

    extension = PurePosixPath(file_name.lower()).suffix
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(extension)

    input_type = ALLOWED_EXTENSIONS[extension]
    if not _SIGNATURE_CHECKS[input_type](header):
        raise CorruptedFileError(extension)

    return input_type


def validate_upload(*, file_name: str, content: bytes, max_upload_mb: int) -> str:
    """Retorna o input_type (ex.: "txt") se válido; levanta um erro de validação caso contrário.

    Para uploads lidos em streaming (ver upload_streaming.py), use validate_upload_streamed."""
    return _validate(
        file_name=file_name,
        size_bytes=len(content),
        header=content[:4096],
        max_upload_mb=max_upload_mb,
    )


def validate_upload_streamed(
    *, file_name: str, size_bytes: int, header: bytes, max_upload_mb: int
) -> str:
    """Mesma validação de validate_upload, mas para quando o tamanho e os primeiros bytes já
    foram apurados incrementalmente (streaming), sem o arquivo inteiro em memória."""
    return _validate(
        file_name=file_name, size_bytes=size_bytes, header=header, max_upload_mb=max_upload_mb
    )
