from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.user_repository import UserRepository
from app.services.dashboard_service import DashboardService


@pytest.fixture()
def service(db_session) -> DashboardService:
    return DashboardService(repo=DashboardRepository(db_session))


@pytest.fixture()
def regular_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="U", email="u@example.com", password_hash="h", role=UserRole.USER, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def admin_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="Admin", email="adm@example.com", password_hash="h", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    )


def _completed(db_session, *, user_id, interaction_id, participant_name, overall_score, band_label, completed_at):
    return AnalysisRepository(db_session).create(
        Analysis(
            participant_name=participant_name,
            objective="Onboarding",
            input_type="txt",
            interaction_id=interaction_id,
            user_id=user_id,
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
        user_id=regular_user.id,
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
        user_id=regular_user.id,
        interaction_id="i2",
        participant_name="Ana",
        overall_score=9.0,
        band_label="Texto novo que não existe na calibração antiga",
        completed_at=now,
    )

    stats = service.get_stats(current_user=regular_user, period="30d")

    assert stats.farol_distribution[0].level == "outro"


def test_admin_scope_includes_board_regular_user_scope_does_not(
    db_session, service, regular_user, admin_user
):
    now = datetime.now(timezone.utc)
    _completed(
        db_session,
        user_id=regular_user.id,
        interaction_id="i3",
        participant_name="Ana",
        overall_score=8.0,
        band_label="Excelente desempenho",
        completed_at=now,
    )

    user_stats = service.get_stats(current_user=regular_user, period="30d")
    admin_stats = service.get_stats(current_user=admin_user, period="30d")

    assert user_stats.board is None
    assert admin_stats.board is not None
    assert len(admin_stats.board) == 1
    assert admin_stats.board[0].name == "Ana"


def test_regular_user_only_sees_own_farol_distribution(db_session, service, regular_user, admin_user):
    now = datetime.now(timezone.utc)
    _completed(
        db_session,
        user_id=regular_user.id,
        interaction_id="i4",
        participant_name="Ana",
        overall_score=8.0,
        band_label="Excelente desempenho",
        completed_at=now,
    )
    _completed(
        db_session,
        user_id=admin_user.id,
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
        user_id=regular_user.id,
        interaction_id="i6",
        participant_name="Ana",
        overall_score=8.0,
        band_label="Excelente desempenho",
        completed_at=old,
    )

    stats = service.get_stats(current_user=regular_user, period="30d")

    assert stats.farol_distribution == []
