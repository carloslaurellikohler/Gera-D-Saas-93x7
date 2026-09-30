"""Persistência do AnalysisResult (seção 20). Interface simples para que um backend real possa
trocar a implementação (Postgres, etc.) sem tocar no motor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from gera_d_engine.schemas.analysis import AnalysisResult


class ReportRepository(Protocol):
    def save(self, result: AnalysisResult) -> str:
        """Persiste o resultado e retorna um identificador de localização (ex.: caminho, chave)."""
        ...

    def load(self, interaction_id: str) -> AnalysisResult:
        ...


class JsonFileReportRepository:
    """Implementação padrão do motor isolado: um arquivo JSON por interação."""

    def __init__(self, base_dir: str | Path = "output/interactions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, interaction_id: str) -> Path:
        return self.base_dir / f"{interaction_id}.json"

    def save(self, result: AnalysisResult) -> str:
        path = self._path_for(result.interaction_id)
        payload = json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False)
        path.write_text(payload, encoding="utf-8")
        return str(path)

    def load(self, interaction_id: str) -> AnalysisResult:
        path = self._path_for(interaction_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        return AnalysisResult.model_validate(data)
