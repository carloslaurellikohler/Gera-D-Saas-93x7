from __future__ import annotations

import uuid

import pytest

from app.core.constants import CriterionKey
from app.models.methodology import MethodologyStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.methodology_repository import MethodologyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.methodology import MethodologyDraftIn
from tests.methodology_factory import valid_draft_payload as _valid_draft_payload

from app.services.methodology_service import (
    MethodologyAnchorMismatchError,
    MethodologyBandCoverageError,
    MethodologyCalibratorMismatchError,
    MethodologyCategoryMismatchError,
    MethodologyNotDraftError,
    MethodologyService,
    MethodologyWeightSumError,
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


# --- Fase 9: as validações que impedem publicar uma régua quebrada -----------------


def _publish_draft(service, admin, payload):
    draft = service.create_draft(from_id=None, actor=admin)
    service.update_draft(draft.id, payload)
    return service.publish(draft.id)


def test_publish_accepts_a_complete_v21_draft(service, admin):
    published = _publish_draft(service, admin, _valid_draft_payload())

    assert published.status == MethodologyStatus.PUBLISHED
    assert len(published.anchors) == 40


def test_publish_rejects_criterion_with_incomplete_anchors(service, admin):
    payload = _valid_draft_payload()
    # tira a âncora de nível 10 de sondagem: a régua deixa de cobrir o topo da escala
    payload.anchors = [
        a for a in payload.anchors if not (a.scope_key == "sondagem" and a.level == 10)
    ]

    with pytest.raises(MethodologyAnchorMismatchError, match="sondagem"):
        _publish_draft(service, admin, payload)


def test_publish_rejects_pillar_without_anchors(service, admin):
    payload = _valid_draft_payload()
    payload.anchors = [a for a in payload.anchors if a.scope_key != "pilar_7"]

    with pytest.raises(MethodologyAnchorMismatchError, match="pilar_7"):
        _publish_draft(service, admin, payload)


def test_publish_rejects_weights_that_do_not_sum_to_one(service, admin):
    payload = _valid_draft_payload()
    payload.categories[0].weight = 0.50

    with pytest.raises(MethodologyWeightSumError, match="135"):
        _publish_draft(service, admin, payload)


def test_publish_rejects_bands_with_a_gap(service, admin):
    payload = _valid_draft_payload(calibration_version="com-buraco")
    # deixa 5,9 a 7,0 descoberto: uma nota 6,5 cairia no fallback silencioso da engine
    payload.calibrators[2].min = 6.5
    payload.calibrators[3].max = 5.9

    with pytest.raises(MethodologyBandCoverageError, match="buraco"):
        _publish_draft(service, admin, payload)


def test_publish_rejects_overlapping_bands(service, admin):
    payload = _valid_draft_payload(calibration_version="sobreposta")
    payload.calibrators[1].min = 6.5

    with pytest.raises(MethodologyBandCoverageError, match="sobrep"):
        _publish_draft(service, admin, payload)
