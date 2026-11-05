from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from gera_d_engine.schemas.transcript import Transcript, TranscriptTurn

from app.core.config import Settings
from app.models.analysis import AnalysisStatus
from app.models.methodology import Calibrator, FarolColor, Methodology, MethodologyStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.user_repository import UserRepository
from app.services.analysis_service import AnalysisService, DailyAnalysisLimitError
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


class FakeUsageSink:
    """Sink de contabilização de custo em memória. Injetado explicitamente para que teste
    nunca escreva em ai_usage_events do banco de desenvolvimento (o sink padrão usa
    SessionLocal, que aponta para o banco real, não para gerad_test)."""

    def __init__(self) -> None:
        self.events: list = []

    def flush(self, events: list) -> None:
        self.events.extend(events)


class ExplodingUsageSink:
    def flush(self, events: list) -> None:  # noqa: ARG002
        raise RuntimeError("banco de custo indisponivel")


@pytest.fixture()
def usage_sink() -> FakeUsageSink:
    return FakeUsageSink()


@pytest.fixture()
def service(db_session, storage, settings, usage_sink) -> AnalysisService:
    repo = AnalysisRepository(db_session)
    engine = MagicMock()
    # Sem pesos, a ponderação é no-op e devolve o par holístico vazio — ver
    # engine_integration/score_resolver.apply_weighted_overall.
    engine.apply_weighted_overall.return_value = (None, None)
    engine.methodology_id = _seed_methodology(db_session).id
    return AnalysisService(
        repo=repo, storage=storage, engine=engine, settings=settings, usage_sink=usage_sink
    )


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
    service: AnalysisService,
    storage: LocalDiskStorage,
    current_user: User,
    tmp_path: Path,
    *,
    file_name: str = "transcricao.txt",
    content: bytes | None = None,
):
    # Default é entrada de texto. Os testes de custo de transcrição passam um .mp3 com
    # cabeçalho ID3 real, porque validate_upload_streamed checa a assinatura do arquivo.
    if content is None:
        content = b"ID3\x04\x00\x00\x00\x00\x00\x23" + b"\x00" * 100 if file_name.endswith(".mp3") else b"CS: Oi\nPB: Oi"
    analysis = service.create_and_store(
        current_user=current_user,
        participant_name="João Silva",
        objective="Onboarding",
        objective_complement=None,
        duration_minutes=45,
        interaction_date=None,
        file_name=file_name,
        temp_file_path=_write_temp_upload(tmp_path, file_name, content),
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
    # Sem pesos, a ponderação é no-op e devolve o par holístico vazio — ver
    # engine_integration/score_resolver.apply_weighted_overall.
    engine.apply_weighted_overall.return_value = (None, None)
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


def _service_with_limit(db_session, storage, limit: int) -> AnalysisService:
    settings = Settings(
        DEFAULT_CS_ID="cs-1", DEFAULT_CS_NAME="Consultor Teste", MAX_UPLOAD_MB=100,
        DAILY_ANALYSIS_LIMIT_PER_OWNER=limit,
    )
    repo = AnalysisRepository(db_session)
    engine = MagicMock()
    # Sem pesos, a ponderação é no-op e devolve o par holístico vazio — ver
    # engine_integration/score_resolver.apply_weighted_overall.
    engine.apply_weighted_overall.return_value = (None, None)
    engine.methodology_id = _seed_methodology(db_session).id
    return AnalysisService(repo=repo, storage=storage, engine=engine, settings=settings)


def test_create_and_store_raises_when_daily_quota_reached(storage, db_session, tmp_path, current_user):
    service = _service_with_limit(db_session, storage, limit=2)

    _create_uploaded_analysis(service, storage, current_user, tmp_path)
    _create_uploaded_analysis(service, storage, current_user, tmp_path)

    with pytest.raises(DailyAnalysisLimitError):
        _create_uploaded_analysis(service, storage, current_user, tmp_path)


def test_create_and_store_counts_failed_analyses_against_quota(storage, db_session, tmp_path, current_user):
    service = _service_with_limit(db_session, storage, limit=1)

    analysis = _create_uploaded_analysis(service, storage, current_user, tmp_path)
    service.repo.update_status(analysis.id, AnalysisStatus.FAILED)

    with pytest.raises(DailyAnalysisLimitError):
        _create_uploaded_analysis(service, storage, current_user, tmp_path)


def test_create_and_store_quota_is_scoped_to_owner(storage, db_session, tmp_path):
    service = _service_with_limit(db_session, storage, limit=1)
    user_repo = UserRepository(db_session)
    gestor = user_repo.create(
        User(
            name="Gestora Quota",
            email="gestora-quota-scope@example.com",
            password_hash="hash",
            role=UserRole.GESTOR,
            status=UserStatus.ACTIVE,
        )
    )
    colaborador_a = user_repo.create(
        User(
            name="Colaborador A",
            email="col-a-quota-scope@example.com",
            password_hash="hash",
            role=UserRole.COLABORADOR,
            status=UserStatus.ACTIVE,
        )
    )
    colaborador_b = user_repo.create(
        User(
            name="Colaborador B",
            email="col-b-quota-scope@example.com",
            password_hash="hash",
            role=UserRole.COLABORADOR,
            status=UserStatus.ACTIVE,
        )
    )
    content = b"CS: Oi\nPB: Oi"

    def _upload(owner: User, suffix: str):
        return service.create_and_store(
            current_user=gestor,
            owner=owner,
            participant_name="Participante",
            objective="Onboarding",
            objective_complement=None,
            duration_minutes=None,
            interaction_date=None,
            file_name=suffix,
            temp_file_path=_write_temp_upload(tmp_path, suffix, content),
            file_size_bytes=len(content),
            file_header=content[:4096],
        )

    _upload(colaborador_a, "a1.txt")
    with pytest.raises(DailyAnalysisLimitError):
        _upload(colaborador_a, "a2.txt")

    # colaborador_b tem cota independente de colaborador_a.
    analysis_b = _upload(colaborador_b, "b1.txt")
    assert analysis_b.owner_id == colaborador_b.id


def test_admin_exempt_from_quota_when_owner_is_self(storage, db_session, tmp_path):
    service = _service_with_limit(db_session, storage, limit=1)
    admin = UserRepository(db_session).create(
        User(
            name="Admin Quota",
            email="admin-quota@example.com",
            password_hash="hash",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
    )
    content = b"CS: Oi\nPB: Oi"

    analysis = None
    for i in range(3):
        suffix = f"admin-{i}.txt"
        analysis = service.create_and_store(
            current_user=admin,
            participant_name="Admin",
            objective="Onboarding",
            objective_complement=None,
            duration_minutes=None,
            interaction_date=None,
            file_name=suffix,
            temp_file_path=_write_temp_upload(tmp_path, suffix, content),
            file_size_bytes=len(content),
            file_header=content[:4096],
        )

    assert analysis is not None
    assert analysis.owner_id == admin.id


def test_gestor_not_exempt_from_quota_when_owner_is_self(storage, db_session, tmp_path):
    service = _service_with_limit(db_session, storage, limit=1)
    gestor = UserRepository(db_session).create(
        User(
            name="Gestora Self",
            email="gestora-self-quota@example.com",
            password_hash="hash",
            role=UserRole.GESTOR,
            status=UserStatus.ACTIVE,
        )
    )
    content = b"CS: Oi\nPB: Oi"

    def _upload(suffix: str):
        return service.create_and_store(
            current_user=gestor,
            participant_name="Gestora",
            objective="Onboarding",
            objective_complement=None,
            duration_minutes=None,
            interaction_date=None,
            file_name=suffix,
            temp_file_path=_write_temp_upload(tmp_path, suffix, content),
            file_size_bytes=len(content),
            file_header=content[:4096],
        )

    _upload("g1.txt")
    with pytest.raises(DailyAnalysisLimitError):
        _upload("g2.txt")


def test_quota_check_happens_before_file_validation(storage, db_session, tmp_path, current_user):
    service = _service_with_limit(db_session, storage, limit=1)
    _create_uploaded_analysis(service, storage, current_user, tmp_path)

    invalid_content = b"not a real file"
    with pytest.raises(DailyAnalysisLimitError):
        service.create_and_store(
            current_user=current_user,
            participant_name="João",
            objective="Onboarding",
            objective_complement=None,
            duration_minutes=None,
            interaction_date=None,
            file_name="invalido.xyz",
            temp_file_path=_write_temp_upload(tmp_path, "invalido.xyz", invalid_content),
            file_size_bytes=len(invalid_content),
            file_header=invalid_content[:4096],
        )


def test_list_analyses_includes_owner_name_duration_and_farol_only_when_completed(
    service: AnalysisService, storage, tmp_path, current_user, db_session
):
    db_session.add(
        Calibrator(
            key="excelente",
            label="Excelente desempenho",
            color=FarolColor.VERDE,
            min=8.0,
            max=10.0,
            order_index=0,
            methodology_id=service.engine.methodology_id,
        )
    )
    db_session.commit()

    in_progress = _create_uploaded_analysis(service, storage, current_user, tmp_path, file_name="a.txt")
    completed = _create_uploaded_analysis(service, storage, current_user, tmp_path, file_name="b.txt")
    service.repo.update(
        completed.id,
        status=AnalysisStatus.COMPLETED,
        analysis_result={"overall_score": 8.5, "overall_band_label": "Excelente desempenho"},
    )

    items, total = service.list_analyses(status=None, owner_ids=[current_user.id], offset=0, limit=20)
    by_id = {item.id: item for item in items}

    assert total == 2
    assert by_id[in_progress.id].owner_name == current_user.name
    assert by_id[in_progress.id].duration_seconds == 45 * 60
    assert by_id[in_progress.id].overall_score is None
    assert by_id[in_progress.id].overall_farol_level is None
    assert by_id[completed.id].overall_score == 8.5
    assert by_id[completed.id].overall_farol_level == "excelente"


def test_list_analyses_applies_participant_and_date_filters(
    service: AnalysisService, storage, tmp_path, current_user
):
    from datetime import date, datetime, timezone

    content = b"CS: Oi\nPB: Oi"

    def _upload(participant_name: str, file_name: str):
        return service.create_and_store(
            current_user=current_user,
            participant_name=participant_name,
            objective="Onboarding",
            objective_complement=None,
            duration_minutes=None,
            interaction_date=None,
            file_name=file_name,
            temp_file_path=_write_temp_upload(tmp_path, file_name, content),
            file_size_bytes=len(content),
            file_header=content[:4096],
        )

    kept = _upload("Ana Souza", "kept.txt")
    service.repo.update(kept.id, created_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc))
    _upload("Bruno Lima", "other.txt")

    items, total = service.list_analyses(
        status=None,
        owner_ids=[current_user.id],
        offset=0,
        limit=20,
        participant_name="ana",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )

    assert total == 1
    assert items[0].id == kept.id


def test_list_analyses_total_ignores_limit(service: AnalysisService, storage, tmp_path, current_user):
    for i in range(3):
        _create_uploaded_analysis(service, storage, current_user, tmp_path, file_name=f"q{i}.txt")

    items, total = service.list_analyses(status=None, owner_ids=[current_user.id], offset=0, limit=1)

    assert len(items) == 1
    assert total == 3


def test_get_daily_quota_reflects_used_and_remaining(service: AnalysisService, storage, tmp_path, current_user):
    _create_uploaded_analysis(service, storage, current_user, tmp_path)

    quota = service.get_daily_quota(target_owner=current_user, current_user=current_user)

    assert quota.used == 1
    assert quota.limit == service.settings.DAILY_ANALYSIS_LIMIT_PER_OWNER
    assert quota.remaining == quota.limit - 1
    assert quota.exempt is False


# --- FinAI: contabilização de custo de IA ---


def test_entrada_de_texto_nao_gera_evento_de_transcricao(
    service: AnalysisService, storage, tmp_path, current_user, usage_sink
):
    """`.docx`/`.txt` são lidos localmente pelo docx_loader: não chamam Whisper e não custam
    nada. Registrar um evento aqui inflaria a fatura."""
    analysis = _create_uploaded_analysis(service, storage, current_user, tmp_path)
    result, export_reports_fn = _fake_result(tmp_path)
    service.engine.load_transcript.return_value = _fake_transcript()
    service.engine.run_pipeline.return_value = result
    service.engine.export_reports.side_effect = export_reports_fn

    service.run_analysis_job(analysis.id)

    assert usage_sink.events == []


def test_entrada_de_audio_gera_evento_de_transcricao_com_duracao(
    service: AnalysisService, storage, tmp_path, current_user, usage_sink, monkeypatch
):
    import subprocess
    from decimal import Decimal

    from app.models.ai_cost import AiUsageFeature, AiUsageOperation

    monkeypatch.setattr(
        subprocess, "run", MagicMock(return_value=MagicMock(stdout=b"600.000000\n"))
    )
    analysis = _create_uploaded_analysis(
        service, storage, current_user, tmp_path, file_name="chamada.mp3"
    )
    result, export_reports_fn = _fake_result(tmp_path)
    service.engine.load_transcript.return_value = _fake_transcript()
    service.engine.run_pipeline.return_value = result
    service.engine.export_reports.side_effect = export_reports_fn

    service.run_analysis_job(analysis.id)

    eventos = [e for e in usage_sink.events if e.operation is AiUsageOperation.TRANSCRIPTION]
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento.model == "whisper-1"
    assert evento.audio_seconds == Decimal("600.000000")
    assert evento.feature is AiUsageFeature.ANALYSIS
    assert evento.analysis_id == analysis.id
    assert evento.user_id == current_user.id
    assert evento.calls == 1


def test_ffprobe_indisponivel_nao_impede_a_analise(
    service: AnalysisService, storage, tmp_path, current_user, usage_sink, monkeypatch
):
    """Sem duração medida o evento fica sem unidades (cost_status=NO_UNITS no sink real),
    mas a análise conclui normalmente."""
    import subprocess

    monkeypatch.setattr(subprocess, "run", MagicMock(side_effect=FileNotFoundError("ffprobe")))
    analysis = _create_uploaded_analysis(
        service, storage, current_user, tmp_path, file_name="chamada.mp3"
    )
    result, export_reports_fn = _fake_result(tmp_path)
    service.engine.load_transcript.return_value = _fake_transcript()
    service.engine.run_pipeline.return_value = result
    service.engine.export_reports.side_effect = export_reports_fn

    service.run_analysis_job(analysis.id)

    assert service.repo.get(analysis.id).status == AnalysisStatus.COMPLETED
    assert usage_sink.events[0].audio_seconds is None


def test_attempt_do_celery_e_propagado_para_os_eventos(
    service: AnalysisService, storage, tmp_path, current_user, usage_sink, monkeypatch
):
    """É o que torna visível o custo de retentativa."""
    import subprocess

    monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(stdout=b"60.0\n")))
    analysis = _create_uploaded_analysis(
        service, storage, current_user, tmp_path, file_name="chamada.mp3"
    )
    result, export_reports_fn = _fake_result(tmp_path)
    service.engine.load_transcript.return_value = _fake_transcript()
    service.engine.run_pipeline.return_value = result
    service.engine.export_reports.side_effect = export_reports_fn

    service.run_analysis_job(analysis.id, attempt=2)

    assert usage_sink.events[0].attempt == 2


def test_falha_ao_contabilizar_custo_nao_reprova_a_analise(
    db_session, storage, settings, tmp_path, current_user, monkeypatch
):
    """INVARIANTE da feature: contabilizar custo NUNCA falha uma análise."""
    import subprocess

    monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(stdout=b"60.0\n")))
    engine = MagicMock()
    # Sem pesos, a ponderação é no-op e devolve o par holístico vazio — ver
    # engine_integration/score_resolver.apply_weighted_overall.
    engine.apply_weighted_overall.return_value = (None, None)
    engine.methodology_id = _seed_methodology(db_session).id
    service = AnalysisService(
        repo=AnalysisRepository(db_session),
        storage=storage,
        engine=engine,
        settings=settings,
        usage_sink=ExplodingUsageSink(),
    )
    analysis = _create_uploaded_analysis(
        service, storage, current_user, tmp_path, file_name="chamada.mp3"
    )
    result, export_reports_fn = _fake_result(tmp_path)
    engine.load_transcript.return_value = _fake_transcript()
    engine.run_pipeline.return_value = result
    engine.export_reports.side_effect = export_reports_fn

    service.run_analysis_job(analysis.id)

    assert service.repo.get(analysis.id).status == AnalysisStatus.COMPLETED


def test_pipeline_que_falha_ainda_contabiliza_o_que_ja_queimou(
    service: AnalysisService, storage, tmp_path, current_user, usage_sink, monkeypatch
):
    """O flush acontece no finally: tokens já gastos numa análise que falhou são justamente
    o número que o dono da ferramenta precisa ver."""
    import subprocess

    from app.models.ai_cost import AiUsageOperation

    monkeypatch.setattr(subprocess, "run", MagicMock(return_value=MagicMock(stdout=b"300.0\n")))
    analysis = _create_uploaded_analysis(
        service, storage, current_user, tmp_path, file_name="chamada.mp3"
    )
    service.engine.load_transcript.return_value = _fake_transcript()
    service.engine.run_pipeline.side_effect = RuntimeError("estourou o contexto do modelo")

    with pytest.raises(RuntimeError):
        service.run_analysis_job(analysis.id)

    assert service.repo.get(analysis.id).status == AnalysisStatus.FAILED
    assert [e.operation for e in usage_sink.events] == [AiUsageOperation.TRANSCRIPTION]
