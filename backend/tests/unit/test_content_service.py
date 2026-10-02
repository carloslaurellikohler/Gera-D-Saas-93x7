from __future__ import annotations

from pathlib import Path

import pytest

from app.models.content import ContentKind
from app.models.learning_path import LearningPath, LearningPathItem
from app.models.user import User, UserRole, UserStatus
from app.repositories.content_repository import ContentRepository
from app.repositories.user_repository import UserRepository
from app.services.content_service import ContentService, ContentStillReferencedError
from app.storage.local_storage import LocalDiskStorage


@pytest.fixture()
def admin_user(db_session) -> User:
    return UserRepository(db_session).create(
        User(name="Admin", email="csa@example.com", password_hash="h", role=UserRole.ADMIN, status=UserStatus.ACTIVE)
    )


@pytest.fixture()
def service(db_session, tmp_path: Path) -> ContentService:
    return ContentService(
        repo=ContentRepository(db_session),
        storage=LocalDiskStorage(tmp_path / "storage"),
        max_upload_mb=10,
    )


def test_create_file_content_stores_bytes_and_persists(service, admin_user):
    content = service.create(
        title="Apostila de sondagem",
        description=None,
        criterion_key=None,
        kind=ContentKind.FILE,
        file_name="apostila.pdf",
        file_content=b"%PDF-1.4" + b"\x00" * 10,
        external_url=None,
        uploaded_by=admin_user,
    )

    assert content.kind == ContentKind.FILE
    assert content.file_path is not None
    assert service.storage.read(content.file_path).startswith(b"%PDF-")


def test_create_link_content_requires_no_file(service, admin_user):
    content = service.create(
        title="Vídeo-aula",
        description=None,
        criterion_key=None,
        kind=ContentKind.LINK,
        file_name=None,
        file_content=None,
        external_url="https://youtube.com/watch?v=abc",
        uploaded_by=admin_user,
    )

    assert content.kind == ContentKind.LINK
    assert content.file_path is None
    assert content.external_url == "https://youtube.com/watch?v=abc"


def test_create_file_without_upload_raises(service, admin_user):
    with pytest.raises(ValueError):
        service.create(
            title="Sem arquivo",
            description=None,
            criterion_key=None,
            kind=ContentKind.FILE,
            file_name=None,
            file_content=None,
            external_url=None,
            uploaded_by=admin_user,
        )


def test_create_link_without_url_raises(service, admin_user):
    with pytest.raises(ValueError):
        service.create(
            title="Sem link",
            description=None,
            criterion_key=None,
            kind=ContentKind.LINK,
            file_name=None,
            file_content=None,
            external_url=None,
            uploaded_by=admin_user,
        )


def test_update_returns_none_when_not_found(service):
    import uuid

    result = service.update(
        uuid.uuid4(),
        title="Qualquer",
        description=None,
        criterion_key=None,
        file_name=None,
        file_content=None,
        external_url=None,
    )

    assert result is None


def test_update_link_changes_external_url(service, admin_user):
    content = service.create(
        title="Vídeo-aula",
        description=None,
        criterion_key=None,
        kind=ContentKind.LINK,
        file_name=None,
        file_content=None,
        external_url="https://youtube.com/watch?v=abc",
        uploaded_by=admin_user,
    )

    updated = service.update(
        content.id,
        title="Vídeo-aula atualizada",
        description="Nova descrição",
        criterion_key=None,
        file_name=None,
        file_content=None,
        external_url="https://youtube.com/watch?v=xyz",
    )

    assert updated is not None
    assert updated.title == "Vídeo-aula atualizada"
    assert updated.external_url == "https://youtube.com/watch?v=xyz"


def test_update_link_without_external_url_raises(service, admin_user):
    content = service.create(
        title="Vídeo-aula",
        description=None,
        criterion_key=None,
        kind=ContentKind.LINK,
        file_name=None,
        file_content=None,
        external_url="https://youtube.com/watch?v=abc",
        uploaded_by=admin_user,
    )

    with pytest.raises(ValueError):
        service.update(
            content.id,
            title="Vídeo-aula",
            description=None,
            criterion_key=None,
            file_name=None,
            file_content=None,
            external_url=None,
        )


def test_update_file_without_new_upload_keeps_existing_file_path(service, admin_user):
    content = service.create(
        title="Apostila",
        description=None,
        criterion_key=None,
        kind=ContentKind.FILE,
        file_name="apostila.pdf",
        file_content=b"%PDF-1.4" + b"\x00" * 10,
        external_url=None,
        uploaded_by=admin_user,
    )
    original_path = content.file_path

    updated = service.update(
        content.id,
        title="Apostila atualizada",
        description=None,
        criterion_key=None,
        file_name=None,
        file_content=None,
        external_url=None,
    )

    assert updated is not None
    assert updated.title == "Apostila atualizada"
    assert updated.file_path == original_path
    assert service.storage.path(original_path).exists()


def test_update_file_with_new_upload_replaces_file_and_deletes_old(service, admin_user):
    content = service.create(
        title="Apostila",
        description=None,
        criterion_key=None,
        kind=ContentKind.FILE,
        file_name="apostila.pdf",
        file_content=b"%PDF-1.4" + b"\x00" * 10,
        external_url=None,
        uploaded_by=admin_user,
    )
    original_path = content.file_path

    updated = service.update(
        content.id,
        title="Apostila",
        description=None,
        criterion_key=None,
        file_name="apostila-v2.pdf",
        file_content=b"%PDF-1.4" + b"\x11" * 20,
        external_url=None,
    )

    assert updated is not None
    assert updated.file_path != original_path
    assert not service.storage.path(original_path).exists()
    assert service.storage.read(updated.file_path).startswith(b"%PDF-")


def test_delete_blocked_when_referenced_by_learning_path(service, admin_user, db_session):
    content = service.create(
        title="Material em uso",
        description=None,
        criterion_key=None,
        kind=ContentKind.LINK,
        file_name=None,
        file_content=None,
        external_url="https://example.com",
        uploaded_by=admin_user,
    )
    learning_path = LearningPath(title="Trilha", created_by_id=admin_user.id)
    db_session.add(learning_path)
    db_session.flush()
    db_session.add(
        LearningPathItem(learning_path_id=learning_path.id, content_id=content.id, order_index=0)
    )
    db_session.commit()

    with pytest.raises(ContentStillReferencedError):
        service.delete(content.id)

    assert service.repo.get(content.id) is not None


def test_delete_removes_file_from_storage(service, admin_user):
    content = service.create(
        title="Removível",
        description=None,
        criterion_key=None,
        kind=ContentKind.FILE,
        file_name="removivel.pdf",
        file_content=b"%PDF-1.4" + b"\x00" * 10,
        external_url=None,
        uploaded_by=admin_user,
    )
    file_path = content.file_path

    service.delete(content.id)

    assert service.repo.get(content.id) is None
    assert not service.storage.path(file_path).exists()
