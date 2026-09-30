from __future__ import annotations

from pathlib import Path

import pytest

from app.storage.local_storage import LocalDiskStorage


@pytest.fixture()
def storage(tmp_path: Path) -> LocalDiskStorage:
    return LocalDiskStorage(tmp_path)


def test_save_bytes_and_read(storage: LocalDiskStorage):
    ref = storage.save_bytes("analysis-1/original.txt", b"hello world")
    assert ref == "analysis-1/original.txt"
    assert storage.read(ref) == b"hello world"


def test_save_file_copies_content(storage: LocalDiskStorage, tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"conteudo do arquivo")

    ref = storage.save_file(source, "analysis-2/executivo.pdf")

    assert storage.read(ref) == b"conteudo do arquivo"


def test_path_resolves_within_base_dir(storage: LocalDiskStorage):
    storage.save_bytes("nested/file.txt", b"x")
    resolved = storage.path("nested/file.txt")
    assert resolved.exists()
    assert resolved.is_relative_to(storage.base_dir.resolve())


def test_path_rejects_traversal_outside_base_dir(storage: LocalDiskStorage):
    with pytest.raises(ValueError):
        storage.path("../../etc/passwd")


def test_delete_removes_file(storage: LocalDiskStorage):
    ref = storage.save_bytes("to-delete.txt", b"x")
    storage.delete(ref)
    assert not storage.path(ref).exists()


def test_delete_missing_file_is_noop(storage: LocalDiskStorage):
    storage.delete("never-existed.txt")
