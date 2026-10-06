from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.services.upload_streaming import buffer_upload
from app.services.validation import FileTooLargeError


def test_buffer_upload_writes_full_content_within_limit(tmp_path: Path):
    content = b"conteudo pequeno de teste"
    with buffer_upload(io.BytesIO(content), max_upload_mb=10, temp_dir=tmp_path) as streamed:
        assert streamed.path.read_bytes() == content
        assert streamed.size_bytes == len(content)
        assert streamed.header == content

    # arquivo temporário é removido ao saír do bloco `with`
    assert not streamed.path.exists()


def test_buffer_upload_captures_header_across_small_chunks(tmp_path: Path):
    content = b"x" * 5000

    class TinyChunkStream:
        def __init__(self, data: bytes) -> None:
            self._data = data
            self._pos = 0

        def read(self, _size: int) -> bytes:
            chunk = self._data[self._pos : self._pos + 10]
            self._pos += 10
            return chunk

    with buffer_upload(TinyChunkStream(content), max_upload_mb=10, temp_dir=tmp_path) as streamed:
        assert streamed.header == content[:4096]
        assert streamed.size_bytes == len(content)


def test_buffer_upload_aborts_and_cleans_up_when_exceeding_limit(tmp_path: Path):
    content = b"x" * (2 * 1024 * 1024)

    with pytest.raises(FileTooLargeError):
        with buffer_upload(io.BytesIO(content), max_upload_mb=1, temp_dir=tmp_path):
            pass

    # nenhum arquivo temporário deve sobrar no diretório após o abort
    assert list(tmp_path.iterdir()) == []
