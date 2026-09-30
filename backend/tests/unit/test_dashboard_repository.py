from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def users(db_session) -> tuple[User, User]:
    repo = UserRepository(db_session)
    user_a = repo.create(
        User(name="A", email="da@example.com", password_hash="h", role=UserRole.USER, status=UserStatus.ACTIVE)
    )
    user_b = repo.create(
        User(name="B", email="db@example.com", password_hash="h", role=UserRole.USER, status=UserStatus.ACTIVE)
    )
    return user_a, user_b


def _completed_analysis(
    db_session,
    *,
    interaction_id: str,
    user_id,
    participant_name: str,
    overall_score: float,
    band_label: str,
    completed_at: datetime,
    created_at: datetime | None = None,
) -> Analysis:
    repo = AnalysisRepository(db_session)
    analysis = repo.create(
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
    if created_at is not None:
        repo.update(analysis.id, created_at=created_at)
    return analysis


def test_count_by_status_respects_user_filter(db_session, users):
    user_a, user_b = users
    since = date.today() - timedelta(days=30)
    AnalysisRepository(db_session).create(
        Analysis(
            participant_name="X",
            objective="Onboarding",
            input_type="txt",
            interaction_id="i1",
            user_id=user_a.id,
            status=AnalysisStatus.CREATED,
        )
    )
    AnalysisRepository(db_session).create(
        Analysis(
            participant_name="Y",
            objective="Onboarding",
            input_type="txt",
            interaction_id="i2",
            user_id=user_b.id,
            status=AnalysisStatus.CREATED,
        )
    )

    repo = DashboardRepository(db_session)
    result_a = repo.count_by_status(user_id=user_a.id, since=since)
    result_all = repo.count_by_status(user_id=None, since=since)

    assert dict(result_a) == {AnalysisStatus.CREATED: 1}
    assert dict(result_all) == {AnalysisStatus.CREATED: 2}


def test_count_by_band_label_groups_correctly(db_session, users):
    user_a, _ = users
    now = datetime.now(timezone.utc)
    since = date.today() - timedelta(days=30)
    _completed_analysis(
        db_session,
        interaction_id="i3",
        user_id=user_a.id,
        participant_name="Ana",
        overall_score=9.0,
        band_label="Excelente desempenho",
        completed_at=now,
    )
    _completed_analysis(
        db_session,
        interaction_id="i4",
        user_id=user_a.id,
        participant_name="Bruno",
        overall_score=5.0,
        band_label="Desenvolvimento crítico",
        completed_at=now,
    )

    repo = DashboardRepository(db_session)
    result = dict(repo.count_by_band_label(user_id=user_a.id, since=since))

    assert result == {"Excelente desempenho": 1, "Desenvolvimento crítico": 1}


def test_trend_by_week_aggregates_count_and_avg_score(db_session, users):
    user_a, _ = users
    now = datetime.now(timezone.utc)
    since = date.today() - timedelta(days=30)
    _completed_analysis(
        db_session,
        interaction_id="i5",
        user_id=user_a.id,
        participant_name="Ana",
        overall_score=8.0,
        band_label="Excelente desempenho",
        completed_at=now,
    )
    _completed_analysis(
        db_session,
        interaction_id="i6",
        user_id=user_a.id,
        participant_name="Bruno",
        overall_score=6.0,
        band_label="Atenção",
        completed_at=now,
    )

    repo = DashboardRepository(db_session)
    result = repo.trend_by_week(user_id=user_a.id, since=since)

    assert len(result) == 1
    _, count, avg_score = result[0]
    assert count == 2
    assert avg_score == pytest.approx(7.0)


def test_since_filter_excludes_older_records(db_session, users):
    user_a, _ = users
    old = datetime.now(timezone.utc) - timedelta(days=200)
    _completed_analysis(
        db_session,
        interaction_id="i7",
        user_id=user_a.id,
        participant_name="Ana",
        overall_score=8.0,
        band_label="Excelente desempenho",
        completed_at=old,
    )

    repo = DashboardRepository(db_session)
    since = date.today() - timedelta(days=30)
    result = repo.count_by_band_label(user_id=user_a.id, since=since)

    assert result == []


def test_completed_rows_by_participant_ignores_user_scope(db_session, users):
    user_a, user_b = users
    now = datetime.now(timezone.utc)
    since = date.today() - timedelta(days=30)
    _completed_analysis(
        db_session,
        interaction_id="i8",
        user_id=user_a.id,
        participant_name="Ana",
        overall_score=8.0,
        band_label="Excelente desempenho",
        completed_at=now,
    )
    _completed_analysis(
        db_session,
        interaction_id="i9",
        user_id=user_b.id,
        participant_name="Bruno",
        overall_score=6.0,
        band_label="Atenção",
        completed_at=now,
    )

    repo = DashboardRepository(db_session)
    rows = repo.completed_rows_by_participant(since=since)

    names = {row.participant_name for row in rows}
    assert names == {"Ana", "Bruno"}
