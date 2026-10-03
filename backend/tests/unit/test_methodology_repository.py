from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.models.analysis import Analysis, AnalysisStatus
from app.models.methodology import Calibrator, FarolColor, Methodology, MethodologyCategory, MethodologyStatus
from app.repositories.methodology_repository import MethodologyRepository


def _methodology(*, calibration_version: str, status: MethodologyStatus = MethodologyStatus.DRAFT) -> Methodology:
    return Methodology(
        calibration_version=calibration_version,
        methodology_name="93x7®",
        project="Projeto Teste",
        status=status,
        content={"objective": "Avaliar."},
    )


def test_create_and_get(db_session):
    repo = MethodologyRepository(db_session)
    methodology = repo.create(_methodology(calibration_version="v1"))

    fetched = repo.get(methodology.id)

    assert fetched is not None
    assert fetched.calibration_version == "v1"
    assert fetched.status == MethodologyStatus.DRAFT


def test_get_published_returns_none_when_none_published(db_session):
    repo = MethodologyRepository(db_session)
    repo.create(_methodology(calibration_version="v1"))

    assert repo.get_published() is None


def test_publish_sets_status_and_timestamps(db_session):
    repo = MethodologyRepository(db_session)
    draft = repo.create(_methodology(calibration_version="v1"))

    published = repo.publish(draft.id, published_at=datetime.now(timezone.utc))

    assert published.status == MethodologyStatus.PUBLISHED
    assert published.published_at is not None
    assert repo.get_published().id == draft.id


def test_publish_archives_previous_published_version(db_session):
    repo = MethodologyRepository(db_session)
    v1 = repo.create(_methodology(calibration_version="v1"))
    repo.publish(v1.id, published_at=datetime.now(timezone.utc))

    v2 = repo.create(_methodology(calibration_version="v2"))
    repo.publish(v2.id, published_at=datetime.now(timezone.utc))

    refreshed_v1 = repo.get(v1.id)
    assert refreshed_v1.status == MethodologyStatus.ARCHIVED
    assert refreshed_v1.archived_at is not None
    assert repo.get_published().id == v2.id


def test_is_referenced_by_analysis(db_session):
    repo = MethodologyRepository(db_session)
    methodology = repo.create(_methodology(calibration_version="v1", status=MethodologyStatus.PUBLISHED))

    assert repo.is_referenced_by_analysis(methodology.id) is False

    analysis = Analysis(
        participant_name="Ana",
        objective="Onboarding",
        input_type="txt",
        interaction_id=f"i-{uuid.uuid4()}",
        status=AnalysisStatus.COMPLETED,
        methodology_version_id=methodology.id,
    )
    db_session.add(analysis)
    db_session.commit()

    assert repo.is_referenced_by_analysis(methodology.id) is True


def test_delete_draft_removes_row(db_session):
    repo = MethodologyRepository(db_session)
    draft = repo.create(_methodology(calibration_version="v1"))

    repo.delete_draft(draft.id)

    assert repo.get(draft.id) is None


def test_get_label_color_map_includes_all_versions_regardless_of_status(db_session):
    repo = MethodologyRepository(db_session)
    archived = _methodology(calibration_version="v1", status=MethodologyStatus.ARCHIVED)
    archived.calibrators = [
        Calibrator(key="excelente", label="Excelente desempenho", color=FarolColor.VERDE, min=8.0, max=10.0, order_index=0),
    ]
    repo.create(archived)

    draft = _methodology(calibration_version="v2")
    draft.calibrators = [
        Calibrator(key="novo", label="Novo label", color=FarolColor.AMARELO, min=5.0, max=7.9, order_index=0),
    ]
    repo.create(draft)

    color_map = repo.get_label_color_map()

    assert color_map == {"Excelente desempenho": "verde", "Novo label": "amarelo"}


def test_update_draft_replaces_categories_and_calibrators(db_session):
    repo = MethodologyRepository(db_session)
    draft = _methodology(calibration_version="v1")
    draft.categories = [
        MethodologyCategory(key="posicionamento", label="Posicionamento", description="d", order_index=0, extra={}),
    ]
    draft = repo.create(draft)

    updated = repo.update_draft(
        draft.id,
        calibration_version="v1.1",
        methodology_name="93x7®",
        project="Projeto Teste",
        content={"objective": "Nova redação."},
        categories=[
            {"key": "sondagem", "label": "Sondagem", "description": "d2", "order_index": 0, "extra": {}},
        ],
        calibrators=[],
    )

    assert updated.calibration_version == "v1.1"
    assert [c.key for c in updated.categories] == ["sondagem"]
