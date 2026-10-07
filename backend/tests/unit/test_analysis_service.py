from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from gera_d_engine.schemas.transcript import Transcript, TranscriptTurn

from app.core.config import Settings
from app.models.analysis import AnalysisStatus
from app.models.methodology import Methodology, MethodologyStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.user_repository import UserRepository
from app.services.analysis_service import AnalysisService
from app.storage.local_storage import LocalDiskStorage


@pytest.fixture()
def settings() -> Settings:
    return Settings(DEFAULT_CS_ID="cs-1", DEFAULT_CS_NAME="Consultor Teste", MAX_UPLOAD_MB=100)


@pytest.fixture()
def storage(tmp_path: Path) -> LocalDiskStorage:
    return LocalDiskStorage(tmp_path / "storage")


def _seed_methodology(db_session) -> Methodology:
    """analyses.methodology_version_id tem FK para methodologies — mesmo com um
    engine mockado, o id gravado precisa existir de verdade na tabela."""
    methodology = Methodology(
        calibration_version=f"Calibração de teste {uuid.uuid4()}",
        methodology_name="93x7®",
        project="Projeto Teste",
        status=MethodologyStatus.PUBLISHED,
        content={},
    )
    db_session.add(methodology)
    db_session.commit()
    return methodology


@pytest.fixture()
def service(db_session, storage, settings) -> AnalysisService:
    repo = AnalysisRepository(db_session)
    engine = MagicMock()
    engine.methodology_id = _seed_methodology(db_session).id
    return AnalysisService(repo=repo, storage=storage, engine=engine, settings=settings)


@pytest.fixture()
def current_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(
            name="Consultora Teste",
            email="consultora@example.com",
            password_hash="hash",
            role=UserRole.COLABORADOR,
            status=UserStatus.ACTIVE,
        )
    )


def _write_temp_upload(tmp_path: Path, name: str, content: bytes) -> Path:
    temp_path = tmp_path / name
    temp_path.write_bytes(content)
    return temp_path


def _create_uploaded_analysis(
    service: AnalysisService, storage: LocalDiskStorage, current_user: User, tmp_path: Path
):
    content = b"CS: Oi\nPB: Oi"
    analysis = service.create_and_store(
        current_user=current_user,
        participant_name="João Silva",
        objective="Onboarding",
        objective_complement=None,
        duration_minutes=45,
        interaction_date=None,
        file_name="transcricao.txt",
        temp_file_path=_write_temp_upload(tmp_path, "transcricao.txt", content),
        file_size_bytes=len(content),
        file_header=content[:4096],
    )
    return analysis


def _fake_transcript() -> Transcript:
    return Transcript(
        turns=[TranscriptTurn(speaker="CS", text="Oi"), TranscriptTurn(speaker="PB", text="Oi")],
        is_diarized=True,
        source_kind="texto_transcrito",
    )


def _fake_result(tmp_path: Path):
    result = MagicMock()
    result.model_dump.return_value = {"overall_score": 8.5, "pb_name": "João Silva"}

    def export_reports(_result, out_dir: Path):
        exec_path = Path(out_dir) / "executivo.pdf"
        det_path = Path(out_dir) / "detalhado.pdf"
        exec_path.write_bytes(b"%PDF-1.4 executivo")
        det_path.write_bytes(b"%PDF-1.4 detalhado")
        return exec_path, det_path

    return result, export_reports


def test_create_and_store_uploads_file_and_sets_status(
    service: AnalysisService, storage, tmp_path: Path, current_user
):
    analysis = _create_uploaded_analysis(service, storage, current_user, tmp_path)

    assert analysis.status == AnalysisStatus.UPLOADED
    assert analysis.input_type == "txt"
    assert analysis.file_path is not None
    assert storage.read(analysis.file_path) == b"CS: Oi\nPB: Oi"
    assert analysis.cs_id == str(current_user.id)
    assert analysis.cs_name == current_user.name
    assert analysis.duration_seconds == 45 * 60


def test_create_and_store_accepts_real_mp3_signature(
    service: AnalysisService, storage, tmp_path: Path, current_user
):
    # Cabeçalho ID3v2 real (gerado com ffmpeg) — prova que validate_upload aceita áudio de
    # verdade, não só a extensão declarada (ver services/validation.py).
    mp3_content = b"ID3\x04\x00\x00\x00\x00\x00\x23" + b"\x00" * 100
    analysis = service.create_and_store(
        current_user=current_user,
        participant_name="Carlos",
        objective="Reunião comercial",
        objective_complement=None,
        duration_minutes=None,
        interaction_date=None,
        file_name="chamada.mp3",
        temp_file_path=_write_temp_upload(tmp_path, "chamada.mp3", mp3_content),
        file_size_bytes=len(mp3_content),
        file_header=mp3_content[:4096],
    )

    assert analysis.status == AnalysisStatus.UPLOADED
    assert analysis.input_type == "mp3"
    assert storage.read(analysis.file_path) == mp3_content


def test_run_analysis_job_happy_path_reaches_completed(service: AnalysisService, storage, tmp_path, current_user):
    analysis = _create_uploaded_analysis(service, storage, current_user, tmp_path)

    transcript = _fake_transcript()
    result, export_reports_fn = _fake_result(tmp_path)
    service.engine.load_transcript.return_value = transcript
    service.engine.run_pipeline.return_value = result
    service.engine.export_reports.side_effect = export_reports_fn

    service.run_analysis_job(analysis.id)

    final = service.repo.get(analysis.id)
    assert final.status == AnalysisStatus.COMPLETED
    assert final.transcription is not None
    assert final.analysis_result == {"overall_score": 8.5, "pb_name": "João Silva"}
    assert final.executive_report_path is not None
    assert final.detailed_report_path is not None
    assert storage.read(final.executive_report_path) == b"%PDF-1.4 executivo"
    assert final.completed_at is not None
    assert final.error_message is None

    service.engine.run_pipeline.assert_called_once()
    called_metadata = service.engine.run_pipeline.call_args.args[1]
    assert called_metadata.cs_id == str(current_user.id)
    assert called_metadata.pb_name == "João Silva"


def test_run_analysis_job_records_status_sequence(service: AnalysisService, storage, tmp_path, current_user):
    analysis = _create_uploaded_analysis(service, storage, current_user, tmp_path)
    observed_statuses: list[AnalysisStatus] = []

    original_update_status = service.repo.update_status

    def tracking_update_status(analysis_id, status, **extra):
        observed_statuses.append(status)
        return original_update_status(analysis_id, status, **extra)

    service.repo.update_status = tracking_update_status  # type: ignore[method-assign]

    transcript = _fake_transcript()
    result, export_reports_fn = _fake_result(tmp_path)
    service.engine.load_transcript.return_value = transcript
    service.engine.run_pipeline.return_value = result
    service.engine.export_reports.side_effect = export_reports_fn

    service.run_analysis_job(analysis.id)

    assert observed_statuses == [
        AnalysisStatus.TRANSCRIBING,
        AnalysisStatus.ANALYZING,
        AnalysisStatus.GENERATING_REPORTS,
    ]


def test_run_analysis_job_transcription_failure_sets_failed_with_safe_message(
    service: AnalysisService, storage, tmp_path: Path, current_user
):
    analysis = _create_uploaded_analysis(service, storage, current_user, tmp_path)
    service.engine.load_transcript.side_effect = RuntimeError(
        "segredo interno: chave de API invalida xyz123"
    )

    with pytest.raises(RuntimeError):
        service.run_analysis_job(analysis.id)

    final = service.repo.get(analysis.id)
    assert final.status == AnalysisStatus.FAILED
    assert final.error_message == "Falha ao transcrever/ingerir o arquivo enviado."
    assert "xyz123" not in final.error_message
    assert final.completed_at is not None


def test_run_analysis_job_pipeline_failure_sets_failed_with_safe_message(
    service: AnalysisService, storage, tmp_path: Path, current_user
):
    analysis = _create_uploaded_analysis(service, storage, current_user, tmp_path)
    service.engine.load_transcript.return_value = _fake_transcript()
    service.engine.run_pipeline.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        service.run_analysis_job(analysis.id)

    final = service.repo.get(analysis.id)
    assert final.status == AnalysisStatus.FAILED
    assert final.error_message == "Falha ao gerar a análise da conversa."
    # transcrição já persistida antes da falha do pipeline
    assert final.transcription is not None


def test_run_analysis_job_reports_failure_sets_failed_with_safe_message(
    service: AnalysisService, storage, tmp_path: Path, current_user
):
    analysis = _create_uploaded_analysis(service, storage, current_user, tmp_path)
    service.engine.load_transcript.return_value = _fake_transcript()
    result = MagicMock()
    result.model_dump.return_value = {"overall_score": 5.0}
    service.engine.run_pipeline.return_value = result
    service.engine.export_reports.side_effect = RuntimeError("weasyprint explodiu")

    with pytest.raises(RuntimeError):
        service.run_analysis_job(analysis.id)

    final = service.repo.get(analysis.id)
    assert final.status == AnalysisStatus.FAILED
    assert final.error_message == "Falha ao gerar os relatórios."
    assert final.analysis_result is not None


def test_create_and_store_uses_current_user_as_cs_identity(
    service: AnalysisService, storage, tmp_path: Path, current_user
):
    analysis = _create_uploaded_analysis(service, storage, current_user, tmp_path)

    assert analysis.owner_id == current_user.id
    assert analysis.cs_id == str(current_user.id)
    assert analysis.cs_name == current_user.name


def test_run_pipeline_does_not_depend_on_settings_defaults(
    db_session, storage, tmp_path, current_user
):
    # Settings com DEFAULT_CS_ID/DEFAULT_CS_NAME propositalmente diferentes do usuário —
    # confirma que _run_pipeline lê analysis.cs_id/cs_name (persistidos a partir do
    # usuário autenticado), nunca settings, ao montar o metadata para a engine.
    settings = Settings(
        DEFAULT_CS_ID="settings-default-id", DEFAULT_CS_NAME="Settings Default Name", MAX_UPLOAD_MB=100
    )
    repo = AnalysisRepository(db_session)
    engine = MagicMock()
    engine.methodology_id = _seed_methodology(db_session).id
    service = AnalysisService(repo=repo, storage=storage, engine=engine, settings=settings)

    analysis = _create_uploaded_analysis(service, storage, current_user, tmp_path)

    transcript = _fake_transcript()
    result, export_reports_fn = _fake_result(tmp_path)
    service.engine.load_transcript.return_value = transcript
    service.engine.run_pipeline.return_value = result
    service.engine.export_reports.side_effect = export_reports_fn

    service.run_analysis_job(analysis.id)

    called_metadata = service.engine.run_pipeline.call_args.args[1]
    assert called_metadata.cs_id == str(current_user.id)
    assert called_metadata.cs_name == current_user.name


def test_create_and_store_with_explicit_owner_sets_owner_and_created_by(
    service: AnalysisService, storage, tmp_path: Path, current_user, db_session
):
    gestor = UserRepository(db_session).create(
        User(
            name="Gestora Teste",
            email="gestora@example.com",
            password_hash="hash",
            role=UserRole.GESTOR,
            status=UserStatus.ACTIVE,
        )
    )
    content = b"CS: Oi\nPB: Oi"
    analysis = service.create_and_store(
        current_user=gestor,
        owner=current_user,
        participant_name="João Silva",
        objective="Onboarding",
        objective_complement=None,
        duration_minutes=45,
        interaction_date=None,
        file_name="transcricao.txt",
        temp_file_path=_write_temp_upload(tmp_path, "transcricao2.txt", content),
        file_size_bytes=len(content),
        file_header=content[:4096],
    )

    assert analysis.owner_id == current_user.id
    assert analysis.created_by_id == gestor.id
    assert analysis.cs_id == str(current_user.id)
    assert analysis.cs_name == current_user.name
