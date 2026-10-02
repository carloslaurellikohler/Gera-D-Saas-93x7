from __future__ import annotations

import pytest

from app.core.constants import CriterionKey
from app.models.content import Content, ContentKind
from app.models.learning_path import LearningPath
from app.models.user import User, UserRole, UserStatus
from app.repositories.content_repository import ContentRepository
from app.repositories.learning_path_repository import LearningPathRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def admin_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="Admin", email="lpa@example.com", password_hash="h", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def contents(db_session) -> list[Content]:
    repo = ContentRepository(db_session)
    return [
        repo.create(Content(title="Módulo 1", kind=ContentKind.LINK, external_url="https://a.example")),
        repo.create(Content(title="Módulo 2", kind=ContentKind.LINK, external_url="https://b.example")),
    ]


def test_create_persists_learning_path_with_ordered_items(db_session, admin_user, contents):
    repo = LearningPathRepository(db_session)
    learning_path = LearningPath(
        title="Sondagem consultiva", criterion_key=CriterionKey.SONDAGEM, created_by_id=admin_user.id
    )

    created = repo.create(
        learning_path, items=[(contents[1].id, 1), (contents[0].id, 0)]
    )

    rows = repo.list_items(created.id)
    assert [content.title for _, content in rows] == ["Módulo 1", "Módulo 2"]
    assert repo.count_items(created.id) == 2


def test_list_by_criterion_keys_filters_correctly(db_session, admin_user):
    repo = LearningPathRepository(db_session)
    sondagem = repo.create(
        LearningPath(title="A", criterion_key=CriterionKey.SONDAGEM, created_by_id=admin_user.id), items=[]
    )
    repo.create(
        LearningPath(title="B", criterion_key=CriterionKey.CONEXAO, created_by_id=admin_user.id), items=[]
    )

    result = repo.list_by_criterion_keys([CriterionKey.SONDAGEM])

    assert [lp.id for lp in result] == [sondagem.id]


def test_update_replaces_items_and_metadata(db_session, admin_user, contents):
    repo = LearningPathRepository(db_session)
    learning_path = repo.create(
        LearningPath(title="Original", created_by_id=admin_user.id),
        items=[(contents[0].id, 0)],
    )

    updated = repo.update(
        learning_path.id,
        title="Atualizada",
        description="Nova descrição",
        criterion_key=CriterionKey.SONDAGEM,
        estimated_duration_minutes=30,
        items=[(contents[1].id, 0)],
    )

    assert updated is not None
    assert updated.title == "Atualizada"
    assert updated.description == "Nova descrição"
    assert updated.criterion_key == CriterionKey.SONDAGEM
    assert updated.estimated_duration_minutes == 30
    rows = repo.list_items(learning_path.id)
    assert [content.title for _, content in rows] == ["Módulo 2"]


def test_update_returns_none_when_not_found(db_session):
    import uuid

    repo = LearningPathRepository(db_session)

    result = repo.update(
        uuid.uuid4(),
        title="Qualquer",
        description=None,
        criterion_key=None,
        estimated_duration_minutes=None,
        items=[],
    )

    assert result is None


def test_delete_cascades_to_items(db_session, admin_user, contents):
    repo = LearningPathRepository(db_session)
    learning_path = repo.create(
        LearningPath(title="Trilha", created_by_id=admin_user.id),
        items=[(contents[0].id, 0)],
    )

    repo.delete(learning_path.id)

    assert repo.get(learning_path.id) is None
    assert repo.list_items(learning_path.id) == []
