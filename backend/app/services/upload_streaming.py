"""Buffer de upload em streaming: lê em chunks, escreve incrementalmente em disco e aborta
antecipadamente se exceder o limite — evita materializar uploads de até 1GB inteiros em
memória."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.services.validation import FileTooLargeError

_CHUNK_SIZE = 8 * 1024 * 1024  # 8MB por chunk de leitura/escrita
_HEADER_SIZE = 4096  # suficiente para todas as assinaturas binárias em validation.py


@dataclass
class StreamedUpload:
    path: Path
    size_bytes: int
    header: bytes


class BufferedUpload:
    """Context manager: grava `stream` num arquivo temporário e garante sua remoção ao
    saír do bloco `with`, tanto no caminho feliz (chamador deve mover/copiar o arquivo para
    o destino final antes de sair do bloco) quanto em caso de erro/abort."""

    def __init__(self, stream: BinaryIO, max_upload_mb: int, temp_dir: str | Path) -> None:
        self._stream = stream
        self._max_bytes = max_upload_mb * 1024 * 1024
        self._max_upload_mb = max_upload_mb
        self._temp_dir = temp_dir
        self._tmp_path: Path | None = None

    def __enter__(self) -> StreamedUpload:
        # Nota: se este método levantar, o protocolo de context manager NÃO chama
        # __exit__ (só é chamado depois de um __enter__ bem-sucedido) — por isso o
        # cleanup do arquivo temporário em caso de abort precisa estar aqui dentro.
        fd, name = tempfile.mkstemp(prefix="gerad-upload-", dir=str(self._temp_dir))
        self._tmp_path = Path(name)
        try:
            total = 0
            header = b""
            with os.fdopen(fd, "wb") as out:
                while chunk := self._stream.read(_CHUNK_SIZE):
                    if len(header) < _HEADER_SIZE:
                        header += chunk[: _HEADER_SIZE - len(header)]
                    total += len(chunk)
                    if total > self._max_bytes:
                        raise FileTooLargeError(total / (1024 * 1024), self._max_upload_mb)
                    out.write(chunk)
        except Exception:
            self._tmp_path.unlink(missing_ok=True)
            self._tmp_path = None
            raise
        return StreamedUpload(path=self._tmp_path, size_bytes=total, header=header)

    def __exit__(self, *exc_info: object) -> None:
        if self._tmp_path is not None:
            self._tmp_path.unlink(missing_ok=True)


def buffer_upload(stream: BinaryIO, max_upload_mb: int, temp_dir: str | Path) -> BufferedUpload:
    return BufferedUpload(stream, max_upload_mb, temp_dir)
