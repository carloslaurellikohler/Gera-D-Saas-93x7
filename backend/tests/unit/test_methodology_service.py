from __future__ import annotations

import uuid

import pytest

from app.core.constants import CriterionKey
from app.models.methodology import FarolColor, MethodologyStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.methodology_repository import MethodologyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.methodology import CalibratorIn, MethodologyCategoryIn, MethodologyDraftIn
from app.services.methodology_service import (
    MethodologyCalibratorMismatchError,
    MethodologyCategoryMismatchError,
    MethodologyNotDraftError,
    MethodologyService,
)

_ALL_CRITERION_KEYS = list(CriterionKey)


@pytest.fixture()
def admin(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="Admin", email="admin@example.com", password_hash="h", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def service(db_session) -> MethodologyService:
    return MethodologyService(MethodologyRepository(db_session))


def _valid_draft_payload(*, calibration_version: str = "v2") -> MethodologyDraftIn:
    return MethodologyDraftIn(
        calibration_version=calibration_version,
        methodology_name="93x7®",
        project="Projeto Teste",
        content={"objective": "Avaliar."},
        categories=[
            MethodologyCategoryIn(key=key, label=key.value.title(), description="d", order_index=i, extra={})
            for i, key in enumerate(_ALL_CRITERION_KEYS)
        ],
        calibrators=[
            CalibratorIn(key="excelente", label="Excelente", color=FarolColor.VERDE, min=8.0, max=10.0, order_index=0),
            CalibratorIn(key="atencao", label="Atenção", color=FarolColor.AMARELO, min=7.0, max=7.9, order_index=1),
            CalibratorIn(key="prioritario", label="Prioritário", color=FarolColor.LARANJA, min=6.0, max=6.9, order_index=2),
            CalibratorIn(key="critico", label="Crítico", color=FarolColor.VERMELHO, min=0.0, max=5.9, order_index=3),
        ],
    )


def test_create_draft_without_source_starts_empty(service, admin):
    draft = service.create_draft(from_id=None, actor=admin)

    assert draft.status == MethodologyStatus.DRAFT
    assert draft.categories == []
    assert draft.calibrators == []


def test_create_draft_from_source_clones_categories_and_calibrators(service, admin):
    source = service.create_draft(from_id=None, actor=admin)
    service.update_draft(source.id, _valid_draft_payload(calibration_version="origem"))
    service.publish(source.id)

    clone = service.create_draft(from_id=source.id, actor=admin)

    assert clone.id != source.id
    assert clone.status == MethodologyStatus.DRAFT
    assert len(clone.categories) == 6
    assert len(clone.calibrators) == 4


def test_update_draft_rejects_non_draft(service, admin):
    draft = service.create_draft(from_id=None, actor=admin)
    service.update_draft(draft.id, _valid_draft_payload())
    service.publish(draft.id)

    with pytest.raises(MethodologyNotDraftError):
        service.update_draft(draft.id, _valid_draft_payload(calibration_version="outra"))


def test_publish_rejects_missing_categories(service, admin):
    draft = service.create_draft(from_id=None, actor=admin)
    payload = _valid_draft_payload()
    payload.categories = payload.categories[:-1]  # falta um critério
    service.update_draft(draft.id, payload)

    with pytest.raises(MethodologyCategoryMismatchError):
        service.publish(draft.id)


def test_publish_rejects_wrong_calibrator_count(service, admin):
    draft = service.create_draft(from_id=None, actor=admin)
    payload = _valid_draft_payload()
    payload.calibrators = payload.calibrators[:-1]  # só 3 faixas
    service.update_draft(draft.id, payload)

    with pytest.raises(MethodologyCalibratorMismatchError):
        service.publish(draft.id)


def test_publish_archives_previous_published_version(service, admin):
    v1 = service.create_draft(from_id=None, actor=admin)
    service.update_draft(v1.id, _valid_draft_payload(calibration_version="v1"))
    service.publish(v1.id)

    v2 = service.create_draft(from_id=None, actor=admin)
    service.update_draft(v2.id, _valid_draft_payload(calibration_version="v2"))
    service.publish(v2.id)

    assert service.get(v1.id).status == MethodologyStatus.ARCHIVED
    assert service.get_published().id == v2.id


def test_delete_draft_rejects_non_draft(service, admin):
    draft = service.create_draft(from_id=None, actor=admin)
    service.update_draft(draft.id, _valid_draft_payload())
    service.publish(draft.id)

    with pytest.raises(MethodologyNotDraftError):
        service.delete_draft(draft.id)


def test_delete_draft_removes_unreferenced_draft(service, admin):
    # Um DRAFT nunca é referenciado por análise de verdade (methodology_version_id só
    # é setado para a versão PUBLISHED no momento da análise, e uma vez PUBLISHED uma
    # versão nunca volta a DRAFT) — a checagem is_referenced_by_analysis em
    # delete_draft é defensiva. A cobertura de is_referenced_by_analysis em si vive em
    # test_methodology_repository.py.
    draft = service.create_draft(from_id=None, actor=admin)

    service.delete_draft(draft.id)

    assert service.get(draft.id) is None


def test_delete_nonexistent_draft_is_noop(service):
    service.delete_draft(uuid.uuid4())
