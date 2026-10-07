from __future__ import annotations

import pytest

from app.models.content import Content, ContentKind
from app.models.learning_path import LearningPath
from app.models.user import User, UserRole, UserStatus
from app.repositories.content_repository import ContentRepository
from app.repositories.learning_path_enrollment_repository import LearningPathEnrollmentRepository
from app.repositories.learning_path_repository import LearningPathRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def admin_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="Admin", email="lpea@example.com", password_hash="h", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def regular_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="U1", email="lpeu1@example.com", password_hash="h", role=UserRole.COLABORADOR, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def other_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="U2", email="lpeu2@example.com", password_hash="h", role=UserRole.COLABORADOR, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def path_with_item(db_session, admin_user):
    content = ContentRepository(db_session).create(
        Content(title="Módulo", kind=ContentKind.LINK, external_url="https://example.com")
    )
    return LearningPathRepository(db_session).create(
        LearningPath(title="Trilha", created_by_id=admin_user.id), items=[(content.id, 0)]
    )


def test_enroll_is_idempotent(db_session, regular_user, path_with_item):
    repo = LearningPathEnrollmentRepository(db_session)

    first = repo.enroll(user_id=regular_user.id, learning_path_id=path_with_item.id)
    second = repo.enroll(user_id=regular_user.id, learning_path_id=path_with_item.id)

    assert first.id == second.id


def test_mark_item_complete_is_idempotent(db_session, regular_user, path_with_item):
    repo = LearningPathEnrollmentRepository(db_session)
    enrollment = repo.enroll(user_id=regular_user.id, learning_path_id=path_with_item.id)
    item_id = LearningPathRepository(db_session).list_items(path_with_item.id)[0][0].id

    repo.mark_item_complete(enrollment_id=enrollment.id, learning_path_item_id=item_id)
    repo.mark_item_complete(enrollment_id=enrollment.id, learning_path_item_id=item_id)

    assert repo.count_completed(enrollment.id) == 1


def test_unmark_item_complete_when_not_completed_is_noop(db_session, regular_user, path_with_item):
    repo = LearningPathEnrollmentRepository(db_session)
    enrollment = repo.enroll(user_id=regular_user.id, learning_path_id=path_with_item.id)
    item_id = LearningPathRepository(db_session).list_items(path_with_item.id)[0][0].id

    repo.unmark_item_complete(enrollment_id=enrollment.id, learning_path_item_id=item_id)

    assert repo.count_completed(enrollment.id) == 0


def test_list_enrolled_with_paths_scoped_to_user(db_session, regular_user, other_user, path_with_item):
    repo = LearningPathEnrollmentRepository(db_session)
    repo.enroll(user_id=regular_user.id, learning_path_id=path_with_item.id)

    regular_rows = repo.list_enrolled_with_paths(regular_user.id)
    other_rows = repo.list_enrolled_with_paths(other_user.id)

    assert len(regular_rows) == 1
    assert other_rows == []
