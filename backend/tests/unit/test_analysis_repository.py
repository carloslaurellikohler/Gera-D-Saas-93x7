from __future__ import annotations

import pytest

from app.models.analysis import Analysis, AnalysisStatus
from app.repositories.analysis_repository import AnalysisRepository


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
