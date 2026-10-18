from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.analysis import Analysis, AnalysisStatus
from app.models.methodology import Calibrator, FarolColor, Methodology, MethodologyStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.methodology_repository import MethodologyRepository
from app.repositories.user_repository import UserRepository
from app.services.dashboard_service import DashboardService


def _seed_calibrators(db_session) -> None:
    """Farol da metodologia seedada, usada por get_farol_level via
    MethodologyRepository.get_label_color_map() — espelha os labels/cores reais de
    calibration/v1.yaml para que os testes de normalização de farol continuem válidos."""
    methodology = Methodology(
        calibration_version="Calibração de teste v1",
        methodology_name="93x7®",
        project="Projeto Teste",
        status=MethodologyStatus.PUBLISHED,
        content={},
        calibrators=[
            Calibrator(key="excelente", label="Excelente desempenho", color=FarolColor.VERDE, min=8.0, max=10.0, order_index=0),
            Calibrator(key="atencao", label="Atenção", color=FarolColor.AMARELO, min=7.0, max=7.9, order_index=1),
            Calibrator(key="desenvolvimento_prioritario", label="Desenvolvimento prioritário", color=FarolColor.LARANJA, min=6.0, max=6.9, order_index=2),
            Calibrator(key="desenvolvimento_critico", label="Desenvolvimento crítico", color=FarolColor.VERMELHO, min=-999, max=5.9, order_index=3),
        ],
    )
    db_session.add(methodology)
    db_session.commit()


@pytest.fixture()
def service(db_session) -> DashboardService:
    _seed_calibrators(db_session)
    return DashboardService(
        repo=DashboardRepository(db_session),
        methodology_repo=MethodologyRepository(db_session),
        user_repo=UserRepository(db_session),
    )


@pytest.fixture()
def regular_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(
            name="U",
            email="u@example.com",
            password_hash="h",
            role=UserRole.COLABORADOR,
            status=UserStatus.ACTIVE,
        )
    )


@pytest.fixture()
def admin_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="Admin", email="adm@example.com", password_hash="h", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    )


def _completed(db_session, *, owner_id, interaction_id, participant_name, overall_score, band_label, completed_at):
    return AnalysisRepository(db_session).create(
        Analysis(
            participant_name=participant_name,
            objective="Onboarding",
            input_type="txt",
            interaction_id=interaction_id,
            owner_id=owner_id,
            pb_id=participant_name.lower().replace(" ", "-"),
            status=AnalysisStatus.COMPLETED,
            completed_at=completed_at,
            analysis_result={"overall_score": overall_score, "overall_band_label": band_label},
        )
    )


def test_normalizes_band_label_to_known_level(db_session, service, regular_user):
    now = datetime.now(timezone.utc)
    _completed(
        db_session,
        owner_id=regular_user.id,
        interaction_id="i1",
        participant_name="Ana",
        overall_score=9.0,
        band_label="Excelente desempenho",
        completed_at=now,
    )

    stats = service.get_stats(current_user=regular_user, period="30d")

    assert stats.farol_distribution[0].level == "excelente"


def test_unknown_band_label_falls_back_gracefully(db_session, service, regular_user):
    now = datetime.now(timezone.utc)
    _completed(
        db_session,
        owner_id=regular_user.id,
        interaction_id="i2",
        participant_name="Ana",
        overall_score=9.0,
        band_label="Texto novo que não existe na calibração antiga",
        completed_at=now,
    )

    stats = service.get_stats(current_user=regular_user, period="30d")

    assert stats.farol_distribution[0].level == "outro"


def test_admin_scope_includes_team_board_regular_user_scope_does_not(
    db_session, service, regular_user, admin_user
):
    now = datetime.now(timezone.utc)
    _completed(
        db_session,
        owner_id=regular_user.id,
        interaction_id="i3",
        participant_name="Ana",
        overall_score=8.0,
        band_label="Excelente desempenho",
        completed_at=now,
    )

    user_stats = service.get_stats(current_user=regular_user, period="30d")
    admin_stats = service.get_stats(current_user=admin_user, period="30d")

    assert user_stats.team_board is None
    assert admin_stats.team_board is not None
    assert len(admin_stats.team_board) == 1
    assert admin_stats.team_board[0].name == regular_user.name


def test_regular_user_only_sees_own_farol_distribution(db_session, service, regular_user, admin_user):
    now = datetime.now(timezone.utc)
    _completed(
        db_session,
        owner_id=regular_user.id,
        interaction_id="i4",
        participant_name="Ana",
        overall_score=8.0,
        band_label="Excelente desempenho",
        completed_at=now,
    )
    _completed(
        db_session,
        owner_id=admin_user.id,
        interaction_id="i5",
        participant_name="Bruno",
        overall_score=5.0,
        band_label="Desenvolvimento crítico",
        completed_at=now,
    )

    stats = service.get_stats(current_user=regular_user, period="30d")

    assert len(stats.farol_distribution) == 1
    assert stats.farol_distribution[0].label == "Excelente desempenho"


def test_period_limits_query_window(db_session, service, regular_user):
    old = datetime.now(timezone.utc) - timedelta(days=200)
    _completed(
        db_session,
        owner_id=regular_user.id,
        interaction_id="i6",
        participant_name="Ana",
        overall_score=8.0,
        band_label="Excelente desempenho",
        completed_at=old,
    )

    stats = service.get_stats(current_user=regular_user, period="30d")

    assert stats.farol_distribution == []


def test_gestor_scope_includes_team_board_with_colaborador_scores(db_session, service):
    user_repo = UserRepository(db_session)
    gestor = user_repo.create(
        User(name="Gestor", email="gestor@example.com", password_hash="h", role=UserRole.GESTOR)
    )
    colaborador = user_repo.create(
        User(
            name="Colaborador",
            email="colab@example.com",
            password_hash="h",
            role=UserRole.COLABORADOR,
            manager_id=gestor.id,
        )
    )
    outsider = user_repo.create(
        User(name="Fora da equipe", email="fora@example.com", password_hash="h", role=UserRole.COLABORADOR)
    )
    now = datetime.now(timezone.utc)
    _completed(
        db_session,
        owner_id=colaborador.id,
        interaction_id="i7",
        participant_name="Ana",
        overall_score=8.0,
        band_label="Excelente desempenho",
        completed_at=now,
    )
    _completed(
        db_session,
        owner_id=outsider.id,
        interaction_id="i8",
        participant_name="Bruno",
        overall_score=5.0,
        band_label="Desenvolvimento crítico",
        completed_at=now,
    )

    stats = service.get_stats(current_user=gestor, period="30d")

    assert stats.team_board is not None
    assert len(stats.team_board) == 1
    assert stats.team_board[0].user_id == str(colaborador.id)
    assert stats.team_board[0].name == "Colaborador"
    assert len(stats.farol_distribution) == 1
    assert stats.farol_distribution[0].label == "Excelente desempenho"
