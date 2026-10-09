from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.user_repository import UserRepository


def _new_analysis(**overrides) -> Analysis:
    defaults = dict(
        participant_name="João Silva",
        objective="Onboarding",
        input_type="txt",
        interaction_id="interaction-1",
    )
    defaults.update(overrides)
    return Analysis(**defaults)


def test_create_and_get(db_session):
    repo = AnalysisRepository(db_session)
    created = repo.create(_new_analysis())

    fetched = repo.get(created.id)

    assert fetched is not None
    assert fetched.participant_name == "João Silva"
    assert fetched.status == AnalysisStatus.CREATED
    assert fetched.created_at is not None


def test_update_status_transitions(db_session):
    repo = AnalysisRepository(db_session)
    created = repo.create(_new_analysis(interaction_id="interaction-2"))

    updated = repo.update_status(created.id, AnalysisStatus.TRANSCRIBING)
    assert updated.status == AnalysisStatus.TRANSCRIBING

    updated = repo.update_status(created.id, AnalysisStatus.COMPLETED)
    assert updated.status == AnalysisStatus.COMPLETED


def test_update_unknown_id_raises(db_session):
    import uuid

    repo = AnalysisRepository(db_session)
    with pytest.raises(ValueError):
        repo.update(uuid.uuid4(), status=AnalysisStatus.FAILED)


def test_list_filters_by_status(db_session):
    repo = AnalysisRepository(db_session)
    a = repo.create(_new_analysis(interaction_id="interaction-3"))
    b = repo.create(_new_analysis(interaction_id="interaction-4"))
    repo.update_status(b.id, AnalysisStatus.COMPLETED)

    completed = repo.list(status=AnalysisStatus.COMPLETED)
    created_only = repo.list(status=AnalysisStatus.CREATED)

    assert [x.id for x in completed] == [b.id]
    assert [x.id for x in created_only] == [a.id]


def test_delete(db_session):
    repo = AnalysisRepository(db_session)
    created = repo.create(_new_analysis(interaction_id="interaction-5"))

    repo.delete(created.id)

    assert repo.get(created.id) is None


def test_create_with_null_user_id_allowed(db_session):
    repo = AnalysisRepository(db_session)
    created = repo.create(_new_analysis(interaction_id="interaction-6"))

    assert created.owner_id is None
    assert repo.get(created.id).owner_id is None


def test_list_filters_by_user_id(db_session):
    from app.models.user import User, UserRole, UserStatus
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(db_session)
    user_a = user_repo.create(
        User(
            name="Usuária A",
            email="a@example.com",
            password_hash="hash",
            role=UserRole.COLABORADOR,
            status=UserStatus.ACTIVE,
        )
    )
    user_b = user_repo.create(
        User(
            name="Usuária B",
            email="b@example.com",
            password_hash="hash",
            role=UserRole.COLABORADOR,
            status=UserStatus.ACTIVE,
        )
    )

    repo = AnalysisRepository(db_session)
    owned_by_a = repo.create(
        _new_analysis(interaction_id="interaction-7", owner_id=user_a.id)
    )
    repo.create(_new_analysis(interaction_id="interaction-8", owner_id=user_b.id))
    repo.create(_new_analysis(interaction_id="interaction-9"))

    result = repo.list(owner_ids=[user_a.id])

    assert [x.id for x in result] == [owned_by_a.id]


def test_list_without_user_id_returns_all(db_session):
    from app.models.user import User, UserRole, UserStatus
    from app.repositories.user_repository import UserRepository

    user = UserRepository(db_session).create(
        User(
            name="Usuária C",
            email="c@example.com",
            password_hash="hash",
            role=UserRole.COLABORADOR,
            status=UserStatus.ACTIVE,
        )
    )

    repo = AnalysisRepository(db_session)
    a = repo.create(_new_analysis(interaction_id="interaction-10"))
    b = repo.create(_new_analysis(interaction_id="interaction-11", owner_id=user.id))

    result = repo.list()

    assert {x.id for x in result} == {a.id, b.id}


def _create_user(db_session, email: str) -> User:
    return UserRepository(db_session).create(
        User(
            name="Colaboradora Teste",
            email=email,
            password_hash="hash",
            role=UserRole.COLABORADOR,
            status=UserStatus.ACTIVE,
        )
    )


def test_count_today_counts_all_statuses_including_failed(db_session):
    owner = _create_user(db_session, "owner-count@example.com")
    repo = AnalysisRepository(db_session)
    created = repo.create(_new_analysis(interaction_id="interaction-count-1", owner_id=owner.id))
    failed = repo.create(_new_analysis(interaction_id="interaction-count-2", owner_id=owner.id))
    repo.update_status(failed.id, AnalysisStatus.FAILED)

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = repo.count_today(owner_id=owner.id, since=since)

    assert count == 2
    assert created.status == AnalysisStatus.CREATED


def test_count_today_respects_since_boundary(db_session):
    owner = _create_user(db_session, "owner-boundary@example.com")
    repo = AnalysisRepository(db_session)
    repo.create(_new_analysis(interaction_id="interaction-count-3", owner_id=owner.id))

    since_in_future = datetime.now(timezone.utc) + timedelta(hours=1)
    count = repo.count_today(owner_id=owner.id, since=since_in_future)

    assert count == 0


def test_list_with_owner_includes_owner_name_via_left_join(db_session):
    owner = _create_user(db_session, "owner-list-with-owner@example.com")
    repo = AnalysisRepository(db_session)
    repo.create(_new_analysis(interaction_id="interaction-lwo-1", owner_id=owner.id))

    [row] = repo.list_with_owner(owner_ids=[owner.id])

    assert row.owner_id == owner.id
    assert row.owner_name == owner.name


def test_list_with_owner_keeps_orphan_analysis_with_null_owner_name(db_session):
    repo = AnalysisRepository(db_session)
    repo.create(_new_analysis(interaction_id="interaction-lwo-2"))

    rows = repo.list_with_owner(owner_ids=None)

    assert len(rows) == 1
    assert rows[0].owner_id is None
    assert rows[0].owner_name is None


def test_list_with_owner_extracts_score_and_band_only_when_completed(db_session):
    repo = AnalysisRepository(db_session)
    in_progress = repo.create(_new_analysis(interaction_id="interaction-lwo-3"))
    completed = repo.create(_new_analysis(interaction_id="interaction-lwo-4"))
    repo.update(
        completed.id,
        status=AnalysisStatus.COMPLETED,
        analysis_result={"overall_score": 7.2, "overall_band_label": "Atenção"},
    )

    rows = {row.id: row for row in repo.list_with_owner()}

    assert rows[in_progress.id].overall_score is None
    assert rows[in_progress.id].band_label is None
    assert rows[completed.id].overall_score == 7.2
    assert rows[completed.id].band_label == "Atenção"


def test_count_matches_filters_regardless_of_limit(db_session):
    owner = _create_user(db_session, "owner-count-filters@example.com")
    repo = AnalysisRepository(db_session)
    repo.create(_new_analysis(interaction_id="interaction-count-filters-1", owner_id=owner.id))
    repo.create(_new_analysis(interaction_id="interaction-count-filters-2", owner_id=owner.id))
    repo.create(_new_analysis(interaction_id="interaction-count-filters-3"))

    assert repo.count(owner_ids=[owner.id]) == 2
    assert repo.count() == 3
    assert len(repo.list_with_owner(owner_ids=[owner.id], limit=1)) == 1


def test_count_today_is_scoped_to_owner(db_session):
    owner_a = _create_user(db_session, "owner-a-scope@example.com")
    owner_b = _create_user(db_session, "owner-b-scope@example.com")
    repo = AnalysisRepository(db_session)
    repo.create(_new_analysis(interaction_id="interaction-count-4", owner_id=owner_b.id))

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = repo.count_today(owner_id=owner_a.id, since=since)

    assert count == 0
