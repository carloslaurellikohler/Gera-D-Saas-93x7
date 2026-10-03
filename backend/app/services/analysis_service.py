"""Camada de orquestração: o único módulo que conhece tanto AnalysisRepository quanto
EngineAdapter/FileStorage ao mesmo tempo. Rotas HTTP nunca importam a engine diretamente."""

from __future__ import annotations

import logging
import tempfile
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from gera_d_engine.schemas.analysis import AnalysisResult
from gera_d_engine.schemas.transcript import Transcript

from app.core.config import Settings
from app.engine_integration.adapter import EngineAdapter
from app.engine_integration.mappers import build_input_metadata, slugify
from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User
from app.repositories.analysis_repository import AnalysisRepository
from app.services.validation import sanitize_filename, validate_upload
from app.storage.base import FileStorage

log = logging.getLogger(__name__)

# Mensagens seguras por etapa — nunca expor str(exc)/stack trace ao cliente (seção 22 do plano).
_SAFE_MESSAGES = {
    "transcription": "Falha ao transcrever/ingerir o arquivo enviado.",
    "analysis": "Falha ao gerar a análise da conversa.",
    "reports": "Falha ao gerar os relatórios.",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisService:
    def __init__(
        self,
        repo: AnalysisRepository,
        storage: FileStorage,
        engine: EngineAdapter,
        settings: Settings,
    ) -> None:
        self.repo = repo
        self.storage = storage
        self.engine = engine
        self.settings = settings

    def create_and_store(
        self,
        *,
        current_user: User,
        participant_name: str,
        objective: str,
        objective_complement: str | None,
        duration_minutes: int | None,
        interaction_date: date | None,
        file_name: str,
        file_content: bytes,
    ) -> Analysis:
        input_type = validate_upload(
            file_name=file_name,
            content=file_content,
            max_upload_mb=self.settings.MAX_UPLOAD_MB,
        )
        safe_name = sanitize_filename(file_name)
        analysis_id = uuid.uuid4()

        analysis = Analysis(
            id=analysis_id,
            participant_name=participant_name,
            objective=objective,
            objective_complement=objective_complement,
            duration_seconds=duration_minutes * 60 if duration_minutes is not None else None,
            interaction_date=interaction_date,
            input_type=input_type,
            file_name=safe_name,
            status=AnalysisStatus.CREATED,
            user_id=current_user.id,
            cs_id=str(current_user.id),
            cs_name=current_user.name,
            pb_id=slugify(participant_name),
            interaction_id=str(analysis_id),
        )
        analysis = self.repo.create(analysis)

        file_ref = self.storage.save_bytes(f"{analysis.id}/{safe_name}", file_content)
        return self.repo.update(analysis.id, file_path=file_ref, status=AnalysisStatus.UPLOADED)

    def run_analysis_job(self, analysis_id: uuid.UUID) -> None:
        analysis = self.repo.get(analysis_id)
        if analysis is None:
            raise ValueError(f"Analysis {analysis_id} not found")

        stage = "transcription"
        try:
            transcript = self._run_transcription(analysis)
            stage = "analysis"
            result = self._run_pipeline(analysis, transcript)
            stage = "reports"
            self._run_reports(analysis, result)
        except Exception:
            log.exception("analysis %s failed at stage=%s", analysis_id, stage)
            self.repo.update(
                analysis_id,
                status=AnalysisStatus.FAILED,
                error_message=_SAFE_MESSAGES[stage],
                completed_at=_utcnow(),
            )
            raise

    def _run_transcription(self, analysis: Analysis) -> Transcript:
        self.repo.update_status(analysis.id, AnalysisStatus.TRANSCRIBING, started_at=_utcnow())
        transcript = self.engine.load_transcript(self.storage.path(analysis.file_path))
        self.repo.update(
            analysis.id,
            transcription=transcript.model_dump(mode="json"),
            status=AnalysisStatus.TRANSCRIBED,
        )
        return transcript

    def _run_pipeline(self, analysis: Analysis, transcript: Transcript) -> AnalysisResult:
        self.repo.update_status(analysis.id, AnalysisStatus.ANALYZING)
        # Roda no worker Celery, sem acesso ao usuário autenticado (fronteira de
        # processo) — lê cs_id/cs_name já persistidos por create_and_store, em vez de
        # settings, para refletir o usuário que de fato criou a análise.
        metadata = build_input_metadata(analysis, cs_id=analysis.cs_id, cs_name=analysis.cs_name)
        result = self.engine.run_pipeline(transcript, metadata)
        self.repo.update(
            analysis.id,
            analysis_result=result.model_dump(mode="json"),
            methodology_version_id=self.engine.methodology_id,
        )
        return result

    def _run_reports(self, analysis: Analysis, result: AnalysisResult) -> None:
        self.repo.update_status(analysis.id, AnalysisStatus.GENERATING_REPORTS)
        with tempfile.TemporaryDirectory() as tmp_dir:
            exec_path, det_path = self.engine.export_reports(result, Path(tmp_dir))
            exec_ref = self.storage.save_file(exec_path, f"{analysis.id}/executivo.pdf")
            det_ref = self.storage.save_file(det_path, f"{analysis.id}/detalhado.pdf")
        self.repo.update(
            analysis.id,
            executive_report_path=exec_ref,
            detailed_report_path=det_ref,
            status=AnalysisStatus.COMPLETED,
            completed_at=_utcnow(),
        )
