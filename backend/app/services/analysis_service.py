"""Camada de orquestração: o único módulo que conhece tanto AnalysisRepository quanto
EngineAdapter/FileStorage ao mesmo tempo. Rotas HTTP nunca importam a engine diretamente."""

from __future__ import annotations

import logging
import tempfile
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from gera_d_engine.schemas.analysis import AnalysisResult
from gera_d_engine.schemas.transcript import Transcript

from app.ai_cost import PendingUsage, WHISPER_MODEL_NAME, probe_duration_seconds, track_ai_usage
from app.ai_cost.callback import UsageCollector
from app.ai_cost.constants import TRANSCRIBED_INPUT_TYPES
from app.ai_cost.recorder import UsageSink
from app.ai_cost.stages import STAGE_TRANSCRIPTION
from app.core.config import Settings
from app.engine_integration.adapter import EngineAdapter
from app.engine_integration.audio_chunking import whisper_call_count
from app.engine_integration.mappers import build_input_metadata, slugify
from app.models.ai_cost import AiUsageFeature, AiUsageOperation
from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User, UserRole
from app.repositories.analysis_repository import AnalysisRepository
from app.services.validation import sanitize_filename, validate_upload_streamed
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


def _safe_whisper_call_count(file_path: Path, duration: Decimal | None) -> int:
    try:
        return whisper_call_count(file_path, duration)
    except Exception:  # noqa: BLE001 — número de diagnóstico nunca derruba uma análise
        return 1


class DailyAnalysisLimitError(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "O limite de análises de hoje para este colaborador foi atingido. Volte amanhã."
        )


@dataclass(frozen=True)
class DailyQuota:
    used: int
    limit: int
    exempt: bool

    @property
    def remaining(self) -> int:
        return self.limit if self.exempt else max(0, self.limit - self.used)


class AnalysisService:
    def __init__(
        self,
        repo: AnalysisRepository,
        storage: FileStorage,
        engine: EngineAdapter,
        settings: Settings,
        usage_sink: UsageSink | None = None,
    ) -> None:
        self.repo = repo
        self.storage = storage
        self.engine = engine
        self.settings = settings
        # None faz track_ai_usage resolver o sink padrão (respeitando o kill switch
        # AI_COST_TRACKING_ENABLED). Injetável para teste.
        self.usage_sink = usage_sink

    def get_daily_quota(self, *, target_owner: User, current_user: User) -> DailyQuota:
        # ADMIN é isento só quando sobe para si mesmo — GESTOR nunca é isento (o limite é
        # do colaborador avaliado, não de quem faz upload).
        exempt = target_owner.id == current_user.id and current_user.role == UserRole.ADMIN
        start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        used = self.repo.count_today(owner_id=target_owner.id, since=start_of_day)
        return DailyQuota(used=used, limit=self.settings.DAILY_ANALYSIS_LIMIT_PER_OWNER, exempt=exempt)

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
        temp_file_path: Path,
        file_size_bytes: int,
        file_header: bytes,
        owner: User | None = None,
    ) -> Analysis:
        # owner é quem avalia/conta nas métricas (o colaborador); current_user é quem
        # de fato fez o upload. Para um COLABORADOR subindo a própria análise, os dois
        # são a mesma pessoa. Para um GESTOR subindo em nome de alguém da equipe,
        # owner é validado contra a equipe na rota antes de chegar aqui.
        target_owner = owner or current_user
        quota = self.get_daily_quota(target_owner=target_owner, current_user=current_user)
        if not quota.exempt and quota.used >= quota.limit:
            raise DailyAnalysisLimitError()
        input_type = validate_upload_streamed(
            file_name=file_name,
            size_bytes=file_size_bytes,
            header=file_header,
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
            owner_id=target_owner.id,
            created_by_id=current_user.id,
            cs_id=str(target_owner.id),
            cs_name=target_owner.name,
            pb_id=slugify(participant_name),
            interaction_id=str(analysis_id),
        )
        analysis = self.repo.create(analysis)

        file_ref = self.storage.save_file(temp_file_path, f"{analysis.id}/{safe_name}")
        return self.repo.update(analysis.id, file_path=file_ref, status=AnalysisStatus.UPLOADED)

    def run_analysis_job(self, analysis_id: uuid.UUID, *, attempt: int = 0) -> None:
        analysis = self.repo.get(analysis_id)
        if analysis is None:
            raise ValueError(f"Analysis {analysis_id} not found")

        stage = "transcription"
        # Um único escopo de contabilização para o job inteiro: as 6-7 chamadas de chat que
        # acontecem lá dentro da engine são capturadas pelo hook de ContextVar (ver
        # app/ai_cost/callback.py), e tudo é gravado numa única vez no fim — inclusive
        # quando o pipeline falha no meio, porque os tokens já queimados são justamente o
        # que o dono da ferramenta precisa ver. `attempt` vem do Celery e torna visível o
        # custo de retentativa, que hoje reexecuta o pipeline inteiro sem deixar rastro.
        with track_ai_usage(
            feature=AiUsageFeature.ANALYSIS,
            user_id=analysis.owner_id,
            analysis_id=analysis.id,
            job_run_id=uuid.uuid4(),
            attempt=attempt,
            sink=self.usage_sink,
        ) as usage:
            try:
                transcript = self._run_transcription(analysis, usage)
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

    def _run_transcription(self, analysis: Analysis, usage: UsageCollector) -> Transcript:
        self.repo.update_status(analysis.id, AnalysisStatus.TRANSCRIBING, started_at=_utcnow())
        file_path = self.storage.path(analysis.file_path)
        transcript = self.engine.load_transcript(file_path)
        self._record_transcription_usage(analysis, file_path, usage)
        self.repo.update(
            analysis.id,
            transcription=transcript.model_dump(mode="json"),
            status=AnalysisStatus.TRANSCRIBED,
        )
        return transcript

    def _record_transcription_usage(
        self, analysis: Analysis, file_path: Path, usage: UsageCollector
    ) -> None:
        """Whisper é faturado por minuto de áudio e não passa pelo LangChain (a engine usa o
        SDK bruto), então medimos o arquivo com ffprobe e registramos o evento à mão.

        `.docx`/`.txt` não geram evento: são lidos localmente e não custam nada.

        Registrado só no caminho de sucesso. Uma falha no meio da transcrição pode
        subcontar, mas o contrário — registrar sempre — superestimaria quando o ffmpeg do
        chunking falha antes de qualquer chamada ao Whisper.
        """
        if analysis.input_type not in TRANSCRIBED_INPUT_TYPES:
            return

        duration = probe_duration_seconds(
            file_path, timeout_seconds=self.settings.AI_COST_FFPROBE_TIMEOUT_SECONDS
        )
        usage.add(
            PendingUsage(
                feature=AiUsageFeature.ANALYSIS,
                operation=AiUsageOperation.TRANSCRIPTION,
                model=WHISPER_MODEL_NAME,
                stage=STAGE_TRANSCRIPTION,
                audio_seconds=duration,
                # Uma linha só, com a duração total do arquivo: os chunks de
                # audio_chunking particionam o áudio, então a soma das durações é a
                # duração original e o número de chamadas HTTP não altera a fatura.
                # `calls` guarda quantas chamadas foram, para fins de diagnóstico.
                calls=_safe_whisper_call_count(file_path, duration),
            )
        )

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
