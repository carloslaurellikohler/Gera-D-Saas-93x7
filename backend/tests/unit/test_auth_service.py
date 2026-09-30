from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.security import hash_password
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService, InactiveUserError, InvalidCredentialsError


@pytest.fixture()
def settings() -> Settings:
    return Settings(JWT_SECRET_KEY="test-secret")


@pytest.fixture()
def auth_service(db_session, settings) -> AuthService:
    return AuthService(repo=UserRepository(db_session), settings=settings)


def _create_user(db_session, **overrides) -> User:
    defaults = dict(
        name="Ana Souza",
        email="ana@example.com",
        password_hash=hash_password("correct-password"),
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    defaults.update(overrides)
    return UserRepository(db_session).create(User(**defaults))


def test_authenticate_success(db_session, auth_service):
    _create_user(db_session)

    user, token = auth_service.authenticate(email="ana@example.com", password="correct-password")

    assert user.email == "ana@example.com"
    assert user.last_login_at is not None
    assert isinstance(token, str) and token


def test_authenticate_wrong_password(db_session, auth_service):
    _create_user(db_session)

    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate(email="ana@example.com", password="wrong-password")


def test_authenticate_unknown_email(auth_service):
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate(email="nao-existe@example.com", password="whatever")


def test_authenticate_inactive_user(db_session, auth_service):
    _create_user(db_session, email="inativo@example.com", status=UserStatus.INACTIVE)

    with pytest.raises(InactiveUserError):
        auth_service.authenticate(email="inativo@example.com", password="correct-password")


def test_create_user_duplicate_email_raises(db_session, auth_service):
    _create_user(db_session, email="duplicado@example.com")

    with pytest.raises(ValueError):
        auth_service.create_user(name="Outro", email="duplicado@example.com", password="x")
