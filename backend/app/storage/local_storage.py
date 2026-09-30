from __future__ import annotations

import shutil
from pathlib import Path


class LocalDiskStorage:
    """Implementação de FileStorage sobre um diretório local (volume Docker em produção)."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, ref: str) -> Path:
        resolved = (self.base_dir / ref).resolve()
        if self.base_dir.resolve() not in resolved.parents and resolved != self.base_dir.resolve():
            raise ValueError(f"Referência de storage inválida: {ref!r}")
        return resolved

    def save_bytes(self, key: str, content: bytes) -> str:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return key

    def save_file(self, source_path: Path, key: str) -> str:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target)
        return key

    def path(self, ref: str) -> Path:
        return self._resolve(ref)

    def read(self, ref: str) -> bytes:
        return self._resolve(ref).read_bytes()

    def delete(self, ref: str) -> None:
        target = self._resolve(ref)
        if target.exists():
            target.unlink()
