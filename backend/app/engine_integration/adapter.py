"""Wrapper fino sobre gera_d_engine. Sem lógica de negócio e sem transições de status —
isso é responsabilidade de AnalysisService. Mantém a engine substituível/testável isoladamente
(ver tests/contract/test_engine_contract.py).

A calibração (Fase 7) vem do Postgres, nunca mais de calibration/v1.yaml — ver
calibration_builder.build_calibration. Nunca reintroduzir
`gera_d_engine.calibration.load_calibration()` no caminho do backend: isso reverteria a
migração silenciosamente para o YAML estático com cache (`lru_cache`) potencialmente
desatualizado.

O **modelo e a temperatura da análise** também vêm do Postgres (tabela runtime_settings,
editável em /configuracoes) — ver engine_settings_builder.build_engine_settings. Pela mesma
razão, nunca deixar o caminho de produção cair no `get_settings()` da engine: ele lê
`os.getenv("OPENAI_MODEL")` e reverteria a configuração para o ambiente do processo em
silêncio. O parâmetro `settings=None` existe só para teste isolado da engine. A
`OPENAI_API_KEY` continua vindo do ambiente: é segredo, não configuração de admin."""

from __future__ import annotations

import uuid
from pathlib import Path

from gera_d_engine.calibration import Calibration
from gera_d_engine.config import Settings as EngineSettings
from gera_d_engine.config import get_settings
from gera_d_engine.ingestion import load_transcript
from gera_d_engine.pipeline import run_pipeline
from gera_d_engine.rendering import export_both
from gera_d_engine.schemas.analysis import AnalysisResult
from gera_d_engine.schemas.transcript import InputMetadata, Transcript
from sqlalchemy.orm import Session

from app.engine_integration.audio_chunking import load_transcript_chunked, needs_chunking
from app.engine_integration.calibration_builder import build_calibration
from app.engine_integration.engine_settings_builder import build_engine_settings
from app.engine_integration.score_resolver import apply_weighted_overall


class NoPublishedMethodologyError(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "Nenhuma metodologia publicada encontrada. Isso só pode acontecer por "
            "intervenção manual indevida no banco — o ciclo de vida normal de "
            "MethodologyService nunca deixa o sistema sem uma versão PUBLISHED."
        )


class EngineAdapter:
    def __init__(
        self,
        calibration: Calibration,
        methodology_id: uuid.UUID,
        settings: EngineSettings | None = None,
    ) -> None:
        # `settings=None` cai no get_settings() da engine (os.getenv). O caminho de produção
        # sempre injeta — ver from_published e a docstring do módulo.
        self._settings = settings or get_settings()
        self._calibration = calibration
        self._methodology_id = methodology_id

    @classmethod
    def from_published(cls, db: Session) -> "EngineAdapter":
        # Imports locais para evitar import circular (os repositories não precisam conhecer
        # engine_integration).
        from app.core.config import get_settings as get_app_settings
        from app.repositories.methodology_repository import MethodologyRepository
        from app.repositories.runtime_settings_repository import RuntimeSettingsRepository

        methodology = MethodologyRepository(db).get_published()
        if methodology is None:
            raise NoPublishedMethodologyError()
        return cls(
            calibration=build_calibration(methodology),
            methodology_id=methodology.id,
            settings=build_engine_settings(
                RuntimeSettingsRepository(db).get(), get_app_settings()
            ),
        )

    def load_transcript(self, file_path: Path) -> Transcript:
        if needs_chunking(file_path):
            return load_transcript_chunked(file_path, self._settings)
        return load_transcript(file_path, self._settings)

    def run_pipeline(self, transcript: Transcript, metadata: InputMetadata) -> AnalysisResult:
        return run_pipeline(
            transcript, metadata, settings=self._settings, calibration=self._calibration
        )

    def apply_weighted_overall(self, result: AnalysisResult) -> tuple[float | None, str | None]:
        """Aplica os pesos da metodologia publicada à nota geral, devolvendo o par
        holístico original. Chamado entre run_pipeline e export_reports, para que os PDFs
        já saiam com a nota oficial — ver score_resolver."""
        return apply_weighted_overall(result, self._calibration)

    def export_reports(self, result: AnalysisResult, out_dir: Path) -> tuple[Path, Path]:
        return export_both(result, self._calibration, out_dir)

    @property
    def calibration_version(self) -> str:
        return self._calibration.calibration_version

    @property
    def methodology_id(self) -> uuid.UUID:
        return self._methodology_id
