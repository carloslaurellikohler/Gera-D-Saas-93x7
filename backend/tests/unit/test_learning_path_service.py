from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.constants import CriterionKey
from app.models.analysis import Analysis, AnalysisStatus
from app.models.content import Content, ContentKind
from app.models.learning_path import LearningPath
from app.models.user import User, UserRole, UserStatus
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.learning_path_enrollment_repository import LearningPathEnrollmentRepository
from app.repositories.learning_path_repository import LearningPathRepository
from app.repositories.metrics_repository import MetricsRepository
from app.repositories.user_repository import UserRepository
from app.schemas.learning_path import CreateLearningPathItem, CreateLearningPathRequest
from app.services.learning_path_service import (
    _CRITERION_VALUES,
    LearningPathItemNotFoundError,
    LearningPathService,
    NotEnrolledError,
)


@pytest.fixture()
def admin_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="Admin", email="lpsa@example.com", password_hash="h", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def regular_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="U", email="lpsu@example.com", password_hash="h", role=UserRole.USER, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def service(db_session) -> LearningPathService:
    return LearningPathService(
        repo=LearningPathRepository(db_session),
        content_repo=ContentRepository(db_session),
        metrics_repo=MetricsRepository(db_session),
        enrollment_repo=LearningPathEnrollmentRepository(db_session),
    )


def test_create_rejects_unknown_content_id(service, admin_user):
    import uuid

    request = CreateLearningPathRequest(
        title="Trilha inválida", items=[CreateLearningPathItem(content_id=uuid.uuid4(), order_index=0)]
    )

    with pytest.raises(ValueError):
        service.create(request=request, created_by=admin_user)


def test_create_and_get_detail_roundtrip(service, admin_user, db_session):
    content = ContentRepository(db_session).create(
        Content(title="Módulo único", kind=ContentKind.LINK, external_url="https://example.com")
    )
    request = CreateLearningPathRequest(
        title="Trilha completa",
        criterion_key=CriterionKey.SONDAGEM,
        items=[CreateLearningPathItem(content_id=content.id, order_index=0)],
    )

    detail = service.create(request=request, created_by=admin_user)

    assert detail.title == "Trilha completa"
    assert len(detail.items) == 1
    assert detail.items[0].content.title == "Módulo único"

    fetched = service.get_detail(detail.id)
    assert fetched is not None
    assert fetched.id == detail.id


def _completed_analysis(db_session, *, user_id, interaction_id: str, criterion_scores: dict[str, float]):
    analysis_result = {
        "overall_score": 7.0,
        "overall_band_label": "Atenção",
        "pilar_93_score": {"key": "pilar_93", "label": "Pilar 93", "score": 7.0},
        "pilar_7_score": {"key": "pilar_7", "label": "Pilar 7", "score": 7.0},
        "scores_by_criterion": [
            {"key": key, "label": key.title(), "score": score} for key, score in criterion_scores.items()
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
            completed_at=datetime.now(timezone.utc),
            analysis_result=analysis_result,
        )
    )


def test_recommended_returns_empty_without_completed_analyses(service, regular_user):
    result = service.get_recommended(current_user=regular_user)

    assert result == []


def test_recommended_matches_weakest_criterion_first(service, regular_user, admin_user, db_session):
    all_scores = {key: 9.0 for key in _CRITERION_VALUES}
    all_scores[CriterionKey.SONDAGEM.value] = 4.0
    all_scores[CriterionKey.CONEXAO.value] = 6.0
    _completed_analysis(db_session, user_id=regular_user.id, interaction_id="r1", criterion_scores=all_scores)

    LearningPathRepository(db_session).create(
        LearningPath(title="Trilha Sondagem", criterion_key=CriterionKey.SONDAGEM, created_by_id=admin_user.id),
        items=[],
    )
    LearningPathRepository(db_session).create(
        LearningPath(title="Trilha Conexao", criterion_key=CriterionKey.CONEXAO, created_by_id=admin_user.id),
        items=[],
    )
    LearningPathRepository(db_session).create(
        LearningPath(title="Trilha Posicionamento", criterion_key=CriterionKey.POSICIONAMENTO, created_by_id=admin_user.id),
        items=[],
    )

    result = service.get_recommended(current_user=regular_user)

    assert [r.title for r in result] == ["Trilha Sondagem", "Trilha Conexao"]


def test_recommended_is_scoped_to_own_analyses_even_for_admin(service, regular_user, admin_user, db_session):
    weak_for_regular = {key: 9.0 for key in _CRITERION_VALUES}
    weak_for_regular[CriterionKey.SONDAGEM.value] = 3.0
    _completed_analysis(db_session, user_id=regular_user.id, interaction_id="r2", criterion_scores=weak_for_regular)

    LearningPathRepository(db_session).create(
        LearningPath(title="Trilha Sondagem", criterion_key=CriterionKey.SONDAGEM, created_by_id=admin_user.id),
        items=[],
    )

    admin_result = service.get_recommended(current_user=admin_user)

    assert admin_result == []


def _create_path_with_items(service, admin_user, db_session, *, item_count: int):
    contents = [
        ContentRepository(db_session).create(
            Content(title=f"Material {i}", kind=ContentKind.LINK, external_url="https://example.com")
        )
        for i in range(item_count)
    ]
    request = CreateLearningPathRequest(
        title="Trilha com itens",
        items=[
            CreateLearningPathItem(content_id=content.id, order_index=i)
            for i, content in enumerate(contents)
        ],
    )
    return service.create(request=request, created_by=admin_user)


def test_enroll_returns_none_for_unknown_path(service, regular_user):
    import uuid

    assert service.enroll(learning_path_id=uuid.uuid4(), user=regular_user) is None


def test_enroll_then_list_enrolled_shows_zero_progress(service, admin_user, regular_user, db_session):
    path = _create_path_with_items(service, admin_user, db_session, item_count=2)

    service.enroll(learning_path_id=path.id, user=regular_user)
    enrolled = service.list_enrolled(user=regular_user)

    assert len(enrolled) == 1
    assert enrolled[0].id == path.id
    assert enrolled[0].completed_count == 0
    assert enrolled[0].progress_percent == 0.0
    assert enrolled[0].is_completed is False


def test_mark_item_complete_without_enrollment_raises_not_enrolled(
    service, admin_user, regular_user, db_session
):
    path = _create_path_with_items(service, admin_user, db_session, item_count=1)

    with pytest.raises(NotEnrolledError):
        service.mark_item_complete(learning_path_id=path.id, item_id=path.items[0].id, user=regular_user)


def test_mark_item_complete_unknown_item_raises_not_found(service, admin_user, regular_user, db_session):
    import uuid

    path = _create_path_with_items(service, admin_user, db_session, item_count=1)
    service.enroll(learning_path_id=path.id, user=regular_user)

    with pytest.raises(LearningPathItemNotFoundError):
        service.mark_item_complete(learning_path_id=path.id, item_id=uuid.uuid4(), user=regular_user)


def test_mark_all_items_complete_marks_path_as_completed(service, admin_user, regular_user, db_session):
    path = _create_path_with_items(service, admin_user, db_session, item_count=2)
    service.enroll(learning_path_id=path.id, user=regular_user)

    for item in path.items:
        service.mark_item_complete(learning_path_id=path.id, item_id=item.id, user=regular_user)

    enrolled = service.list_enrolled(user=regular_user)
    assert enrolled[0].progress_percent == 100.0
    assert enrolled[0].is_completed is True


def test_unmark_item_complete_reduces_progress(service, admin_user, regular_user, db_session):
    path = _create_path_with_items(service, admin_user, db_session, item_count=2)
    service.enroll(learning_path_id=path.id, user=regular_user)
    for item in path.items:
        service.mark_item_complete(learning_path_id=path.id, item_id=item.id, user=regular_user)

    service.unmark_item_complete(learning_path_id=path.id, item_id=path.items[0].id, user=regular_user)

    enrolled = service.list_enrolled(user=regular_user)
    assert enrolled[0].completed_count == 1
    assert enrolled[0].is_completed is False


def test_get_detail_marks_completed_items_for_current_user_only(
    service, admin_user, regular_user, db_session
):
    other_user = UserRepository(db_session).create(
        User(name="Outro", email="lpso@example.com", password_hash="h", role=UserRole.USER, status=UserStatus.ACTIVE)
    )
    path = _create_path_with_items(service, admin_user, db_session, item_count=1)
    service.enroll(learning_path_id=path.id, user=regular_user)
    service.mark_item_complete(learning_path_id=path.id, item_id=path.items[0].id, user=regular_user)

    detail_for_owner = service.get_detail(path.id, current_user=regular_user)
    detail_for_other = service.get_detail(path.id, current_user=other_user)
    detail_without_user = service.get_detail(path.id)

    assert detail_for_owner.items[0].completed is True
    assert detail_for_other.items[0].completed is False
    assert detail_without_user.items[0].completed is False
