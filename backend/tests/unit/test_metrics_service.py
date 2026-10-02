from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.user_repository import UserRepository
from app.services.metrics_service import _CRITERION_ORDER, MetricsService


@pytest.fixture()
def service(db_session) -> MetricsService:
    return MetricsService(repo=MetricsRepository(db_session))


@pytest.fixture()
def regular_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="U", email="mu@example.com", password_hash="h", role=UserRole.USER, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def admin_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="Admin", email="madm@example.com", password_hash="h", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    )


def _completed(
    db_session,
    *,
    user_id,
    interaction_id: str,
    completed_at: datetime,
    overall_score: float = 8.0,
    pilar_93: float = 8.0,
    pilar_7: float = 8.0,
    criterion_scores: dict[str, float] | None = None,
):
    criterion_scores = criterion_scores or {key: overall_score for key in _CRITERION_ORDER}
    analysis_result = {
        "overall_score": overall_score,
        "overall_band_label": "Excelente desempenho",
        "pilar_93_score": {"key": "pilar_93", "label": "Pilar 93", "score": pilar_93},
        "pilar_7_score": {"key": "pilar_7", "label": "Pilar 7", "score": pilar_7},
        "scores_by_criterion": [
            {"key": key, "label": key.replace("_", " ").title(), "score": score}
            for key, score in criterion_scores.items()
        ],
    }
    return AnalysisRepository(db_session).create(
        Analysis(
            participant_name="Ana",
            objective="Onboarding",
            input_type="txt",
            interaction_id=interaction_id,
            user_id=user_id,
            status=AnalysisStatus.COMPLETED,
            completed_at=completed_at,
            analysis_result=analysis_result,
        )
    )


def test_radar_averages_current_period_scores_per_criterion(db_session, service, regular_user):
    now = datetime.now(timezone.utc)
    _completed(
        db_session,
        user_id=regular_user.id,
        interaction_id="s1",
        completed_at=now,
        criterion_scores={"posicionamento": 6.0, **{k: 8.0 for k in _CRITERION_ORDER if k != "posicionamento"}},
    )
    _completed(
        db_session,
        user_id=regular_user.id,
        interaction_id="s2",
        completed_at=now,
        criterion_scores={"posicionamento": 8.0, **{k: 8.0 for k in _CRITERION_ORDER if k != "posicionamento"}},
    )

    result = service.get_evolution(current_user=regular_user, period="30d")

    posicionamento = next(p for p in result.radar if p.key == "posicionamento")
    assert posicionamento.score == pytest.approx(7.0)
    assert posicionamento.sample_size == 2
    assert posicionamento.label == "Posicionamento"
    assert len(result.radar) == 6


def test_radar_includes_previous_period_comparison(db_session, service, regular_user):
    now = datetime.now(timezone.utc)
    previous = now - timedelta(days=45)
    _completed(
        db_session,
        user_id=regular_user.id,
        interaction_id="s3",
        completed_at=now,
        criterion_scores={k: 9.0 for k in _CRITERION_ORDER},
    )
    _completed(
        db_session,
        user_id=regular_user.id,
        interaction_id="s4",
        completed_at=previous,
        criterion_scores={k: 6.0 for k in _CRITERION_ORDER},
    )

    result = service.get_evolution(current_user=regular_user, period="30d")

    point = result.radar[0]
    assert point.score == pytest.approx(9.0)
    assert point.previous_score == pytest.approx(6.0)


def test_radar_reports_six_points_with_none_when_no_completed_analyses(db_session, service, regular_user):
    result = service.get_evolution(current_user=regular_user, period="30d")

    assert len(result.radar) == 6
    assert all(p.score is None and p.previous_score is None and p.sample_size == 0 for p in result.radar)
    assert result.trend == []


def test_trend_aggregates_weekly_buckets_for_overall_and_both_pillars(db_session, service, regular_user):
    now = datetime.now(timezone.utc)
    _completed(
        db_session,
        user_id=regular_user.id,
        interaction_id="s5",
        completed_at=now,
        overall_score=8.0,
        pilar_93=9.0,
        pilar_7=7.0,
    )
    _completed(
        db_session,
        user_id=regular_user.id,
        interaction_id="s6",
        completed_at=now,
        overall_score=6.0,
        pilar_93=7.0,
        pilar_7=5.0,
    )

    result = service.get_evolution(current_user=regular_user, period="30d")

    assert len(result.trend) == 1
    point = result.trend[0]
    assert point.count == 2
    assert point.avg_overall_score == pytest.approx(7.0)
    assert point.avg_pilar_93 == pytest.approx(8.0)
    assert point.avg_pilar_7 == pytest.approx(6.0)


def test_admin_sees_all_users_regular_user_sees_only_own(db_session, service, regular_user, admin_user):
    now = datetime.now(timezone.utc)
    _completed(db_session, user_id=regular_user.id, interaction_id="s7", completed_at=now)
    _completed(db_session, user_id=admin_user.id, interaction_id="s8", completed_at=now)

    user_result = service.get_evolution(current_user=regular_user, period="30d")
    admin_result = service.get_evolution(current_user=admin_user, period="30d")

    assert user_result.trend[0].count == 1
    assert admin_result.trend[0].count == 2


def test_period_limits_query_window(db_session, service, regular_user):
    old = datetime.now(timezone.utc) - timedelta(days=200)
    _completed(db_session, user_id=regular_user.id, interaction_id="s9", completed_at=old)

    result = service.get_evolution(current_user=regular_user, period="30d")

    assert result.trend == []
    assert all(p.score is None for p in result.radar)
