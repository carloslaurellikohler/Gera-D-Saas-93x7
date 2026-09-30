from __future__ import annotations

from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository


def _new_user(**overrides) -> User:
    defaults = dict(
        name="Ana Souza",
        email="ana@example.com",
        password_hash="hashed-value",
    )
    defaults.update(overrides)
    return User(**defaults)


def test_create_and_get(db_session):
    repo = UserRepository(db_session)
    created = repo.create(_new_user())

    fetched = repo.get(created.id)

    assert fetched is not None
    assert fetched.email == "ana@example.com"
    assert fetched.role == UserRole.USER
    assert fetched.status == UserStatus.ACTIVE
    assert fetched.created_at is not None


def test_get_by_email(db_session):
    repo = UserRepository(db_session)
    repo.create(_new_user(email="bruno@example.com"))

    found = repo.get_by_email("bruno@example.com")
    missing = repo.get_by_email("nao-existe@example.com")

    assert found is not None
    assert found.email == "bruno@example.com"
    assert missing is None


def test_update(db_session):
    repo = UserRepository(db_session)
    created = repo.create(_new_user(email="carla@example.com"))

    updated = repo.update(created.id, status=UserStatus.INACTIVE)

    assert updated.status == UserStatus.INACTIVE
