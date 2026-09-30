"""Wrapper fino sobre gera_d_engine. Sem lógica de negócio e sem transições de status —
isso é responsabilidade de AnalysisService. Mantém a engine substituível/testável isoladamente
(ver tests/contract/test_engine_contract.py)."""

from __future__ import annotations

from pathlib import Path

from gera_d_engine.calibration import load_calibration
from gera_d_engine.config import get_settings
from gera_d_engine.ingestion import load_transcript
from gera_d_engine.pipeline import run_pipeline
from gera_d_engine.rendering import export_both
from gera_d_engine.schemas.analysis import AnalysisResult
from gera_d_engine.schemas.transcript import InputMetadata, Transcript


class EngineAdapter:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._calibration = load_calibration()

    def load_transcript(self, file_path: Path) -> Transcript:
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
