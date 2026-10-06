"""Wrapper fino sobre gera_d_engine. Sem lógica de negócio e sem transições de status —
isso é responsabilidade de AnalysisService. Mantém a engine substituível/testável isoladamente
(ver tests/contract/test_engine_contract.py).

A calibração (Fase 7) vem do Postgres, nunca mais de calibration/v1.yaml — ver
calibration_builder.build_calibration. Nunca reintroduzir
`gera_d_engine.calibration.load_calibration()` no caminho do backend: isso reverteria a
migração silenciosamente para o YAML estático com cache (`lru_cache`) potencialmente
desatualizado."""

from __future__ import annotations

import uuid
from pathlib import Path

from gera_d_engine.calibration import Calibration
from gera_d_engine.config import get_settings
from gera_d_engine.ingestion import load_transcript
from gera_d_engine.pipeline import run_pipeline
from gera_d_engine.rendering import export_both
from gera_d_engine.schemas.analysis import AnalysisResult
from gera_d_engine.schemas.transcript import InputMetadata, Transcript
from sqlalchemy.orm import Session

from app.engine_integration.audio_chunking import load_transcript_chunked, needs_chunking
from app.engine_integration.calibration_builder import build_calibration


class NoPublishedMethodologyError(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "Nenhuma metodologia publicada encontrada. Isso só pode acontecer por "
            "intervenção manual indevida no banco — o ciclo de vida normal de "
            "MethodologyService nunca deixa o sistema sem uma versão PUBLISHED."
        )


class EngineAdapter:
    def __init__(self, calibration: Calibration, methodology_id: uuid.UUID) -> None:
        self._settings = get_settings()
        self._calibration = calibration
        self._methodology_id = methodology_id

    @classmethod
    def from_published(cls, db: Session) -> "EngineAdapter":
        # Import local para evitar import circular (methodology_repository não precisa
        # conhecer engine_integration).
        from app.repositories.methodology_repository import MethodologyRepository

        methodology = MethodologyRepository(db).get_published()
        if methodology is None:
            raise NoPublishedMethodologyError()
        return cls(calibration=build_calibration(methodology), methodology_id=methodology.id)

    def load_transcript(self, file_path: Path) -> Transcript:
        if needs_chunking(file_path):
            return load_transcript_chunked(file_path, self._settings)
        return load_transcript(file_path, self._settings)

    def run_pipeline(self, transcript: Transcript, metadata: InputMetadata) -> AnalysisResult:
        return run_pipeline(
            transcript, metadata, settings=self._settings, calibration=self._calibration
        )

    def export_reports(self, result: AnalysisResult, out_dir: Path) -> tuple[Path, Path]:
        return export_both(result, self._calibration, out_dir)

    @property
    def calibration_version(self) -> str:
        return self._calibration.calibration_version

    @property
    def methodology_id(self) -> uuid.UUID:
        return self._methodology_id
