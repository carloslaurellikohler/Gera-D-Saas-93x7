from __future__ import annotations

import pytest

from app.models.content import Content, ContentKind
from app.models.learning_path import LearningPath, LearningPathItem
from app.models.user import User, UserRole, UserStatus
from app.repositories.content_repository import ContentRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def admin_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="Admin", email="cra@example.com", password_hash="h", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    )


def _content(db_session, *, title: str, criterion_key=None, uploaded_by_id=None) -> Content:
    return ContentRepository(db_session).create(
        Content(
            title=title,
            kind=ContentKind.LINK,
            external_url="https://example.com/video",
            criterion_key=criterion_key,
            uploaded_by_id=uploaded_by_id,
        )
    )


def test_create_and_get_content(db_session, admin_user):
    content = _content(db_session, title="Sondagem consultiva", uploaded_by_id=admin_user.id)

    fetched = ContentRepository(db_session).get(content.id)

    assert fetched is not None
    assert fetched.title == "Sondagem consultiva"
    assert fetched.uploaded_by_id == admin_user.id


def test_list_filters_by_criterion_key(db_session, admin_user):
    from app.core.constants import CriterionKey

    _content(db_session, title="A", criterion_key=CriterionKey.SONDAGEM)
    _content(db_session, title="B", criterion_key=CriterionKey.CONEXAO)

    repo = ContentRepository(db_session)
    sondagem_only = repo.list(criterion_key=CriterionKey.SONDAGEM)
    all_content = repo.list()

    assert [c.title for c in sondagem_only] == ["A"]
    assert len(all_content) == 2


def test_is_referenced_by_learning_path(db_session, admin_user):
    content = _content(db_session, title="Referenciado")
    learning_path = LearningPath(title="Trilha", created_by_id=admin_user.id)
    db_session.add(learning_path)
    db_session.flush()
    db_session.add(LearningPathItem(learning_path_id=learning_path.id, content_id=content.id, order_index=0))
    db_session.commit()

    repo = ContentRepository(db_session)
    assert repo.is_referenced_by_learning_path(content.id) is True

    other_content = _content(db_session, title="Livre")
    assert repo.is_referenced_by_learning_path(other_content.id) is False


def test_update_persists_metadata_changes(db_session, admin_user):
    from app.core.constants import CriterionKey

    content = _content(db_session, title="Original")
    repo = ContentRepository(db_session)

    updated = repo.update(
        content.id,
        title="Atualizado",
        description="Nova descrição",
        criterion_key=CriterionKey.CONEXAO,
        file_path=None,
        external_url="https://example.com/novo",
    )

    assert updated is not None
    assert updated.title == "Atualizado"
    assert updated.description == "Nova descrição"
    assert updated.criterion_key == CriterionKey.CONEXAO
    assert updated.external_url == "https://example.com/novo"


def test_update_returns_none_when_not_found(db_session):
    import uuid

    repo = ContentRepository(db_session)

    result = repo.update(
        uuid.uuid4(),
        title="Qualquer",
        description=None,
        criterion_key=None,
        file_path=None,
        external_url=None,
    )

    assert result is None


def test_delete_removes_content(db_session):
    content = _content(db_session, title="Para apagar")
    repo = ContentRepository(db_session)

    repo.delete(content.id)

    assert repo.get(content.id) is None
