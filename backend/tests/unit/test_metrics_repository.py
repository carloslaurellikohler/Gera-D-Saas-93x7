from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def users(db_session) -> tuple[User, User]:
    repo = UserRepository(db_session)
    user_a = repo.create(
        User(name="A", email="ma@example.com", password_hash="h", role=UserRole.COLABORADOR, status=UserStatus.ACTIVE)
    )
    user_b = repo.create(
        User(name="B", email="mb@example.com", password_hash="h", role=UserRole.COLABORADOR, status=UserStatus.ACTIVE)
    )
    return user_a, user_b


def _analysis_result(overall_score: float = 8.0) -> dict:
    return {
        "overall_score": overall_score,
        "overall_band_label": "Excelente desempenho",
        "pilar_93_score": {"key": "pilar_93", "label": "Pilar 93", "score": overall_score},
        "pilar_7_score": {"key": "pilar_7", "label": "Pilar 7", "score": overall_score},
        "scores_by_criterion": [
            {"key": "posicionamento", "label": "Posicionamento", "score": overall_score},
        ],
    }


def _analysis(
    db_session,
    *,
    interaction_id: str,
    owner_id,
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
    completed_at: datetime | None = None,
    analysis_result: dict | None = ...,
) -> Analysis:
    repo = AnalysisRepository(db_session)
    kwargs = dict(
        participant_name="Ana",
        objective="Onboarding",
        input_type="txt",
        interaction_id=interaction_id,
        owner_id=owner_id,
        status=status,
        completed_at=completed_at,
    )
    if analysis_result is not ...:
        kwargs["analysis_result"] = analysis_result
    elif status == AnalysisStatus.COMPLETED:
        kwargs["analysis_result"] = _analysis_result()
    return repo.create(Analysis(**kwargs))


def test_completed_rows_respects_user_filter(db_session, users):
    user_a, user_b = users
    now = datetime.now(timezone.utc)
    since = date.today() - timedelta(days=30)
    _analysis(db_session, interaction_id="m1", owner_id=user_a.id, completed_at=now)
    _analysis(db_session, interaction_id="m2", owner_id=user_b.id, completed_at=now)

    repo = MetricsRepository(db_session)
    rows_a = repo.completed_rows(owner_ids=[user_a.id], since=since)
    rows_all = repo.completed_rows(owner_ids=None, since=since)

    assert len(rows_a) == 1
    assert len(rows_all) == 2


def test_completed_rows_excludes_non_completed_status(db_session, users):
    user_a, _ = users
    since = date.today() - timedelta(days=30)
    _analysis(
        db_session,
        interaction_id="m3",
        owner_id=user_a.id,
        status=AnalysisStatus.CREATED,
        analysis_result=None,
    )

    repo = MetricsRepository(db_session)
    rows = repo.completed_rows(owner_ids=[user_a.id], since=since)

    assert rows == []


def test_completed_rows_excludes_older_than_since(db_session, users):
    user_a, _ = users
    old = datetime.now(timezone.utc) - timedelta(days=200)
    since = date.today() - timedelta(days=30)
    _analysis(db_session, interaction_id="m4", owner_id=user_a.id, completed_at=old)

    repo = MetricsRepository(db_session)
    rows = repo.completed_rows(owner_ids=[user_a.id], since=since)

    assert rows == []


def test_completed_rows_excludes_null_analysis_result(db_session, users):
    """Simula analysis_result nunca populado (SQL NULL real) — passar `None`
    explicitamente no construtor gravaria JSON 'null' dentro do JSONB, não SQL NULL,
    então o campo precisa ficar de fora do construtor para reproduzir o caso real."""
    user_a, _ = users
    now = datetime.now(timezone.utc)
    since = date.today() - timedelta(days=30)
    AnalysisRepository(db_session).create(
        Analysis(
            participant_name="Ana",
            objective="Onboarding",
            input_type="txt",
            interaction_id="m5",
            owner_id=user_a.id,
            status=AnalysisStatus.COMPLETED,
            completed_at=now,
        )
    )

    repo = MetricsRepository(db_session)
    rows = repo.completed_rows(owner_ids=[user_a.id], since=since)

    assert rows == []
