from __future__ import annotations

import uuid

import pytest

from app.core.security import verify_password
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository
from app.services.user_service import (
    CannotDeactivateSelfError,
    EmailAlreadyExistsError,
    UserNotFoundError,
    UserService,
)


@pytest.fixture()
def service(db_session) -> UserService:
    return UserService(repo=UserRepository(db_session))


def test_create_user_hashes_password_and_defaults_role(service):
    user = service.create_user(name="Ana Souza", email="ana@example.com", password="correct-password")

    assert user.role == UserRole.USER
    assert user.status == UserStatus.ACTIVE
    assert verify_password("correct-password", user.password_hash)


def test_create_user_rejects_duplicate_email(service):
    service.create_user(name="Ana Souza", email="ana@example.com", password="correct-password")

    with pytest.raises(EmailAlreadyExistsError):
        service.create_user(name="Outra Ana", email="ana@example.com", password="correct-password")


def test_update_user_changes_fields(service):
    user = service.create_user(name="Ana Souza", email="ana@example.com", password="correct-password")

    updated = service.update_user(
        user.id, name="Ana Souza Lima", email="ana.lima@example.com", role=UserRole.ADMIN
    )

    assert updated.name == "Ana Souza Lima"
    assert updated.email == "ana.lima@example.com"
    assert updated.role == UserRole.ADMIN


def test_update_user_not_found_raises(service):
    with pytest.raises(UserNotFoundError):
        service.update_user(uuid.uuid4(), name="X", email="x@example.com", role=UserRole.USER)


def test_update_user_rejects_email_colliding_with_another_user(service):
    service.create_user(name="Ana Souza", email="ana@example.com", password="correct-password")
    bruno = service.create_user(name="Bruno Lima", email="bruno@example.com", password="correct-password")

    with pytest.raises(EmailAlreadyExistsError):
        service.update_user(bruno.id, name="Bruno Lima", email="ana@example.com", role=UserRole.USER)


def test_update_user_keeps_own_email(service):
    user = service.create_user(name="Ana Souza", email="ana@example.com", password="correct-password")

    updated = service.update_user(user.id, name="Ana Souza", email="ana@example.com", role=UserRole.USER)

    assert updated.email == "ana@example.com"


def test_set_status_deactivates_other_user(service):
    admin = service.create_user(
        name="Admin", email="admin@example.com", password="correct-password", role=UserRole.ADMIN
    )
    target = service.create_user(name="Ana Souza", email="ana@example.com", password="correct-password")

    deactivated = service.set_status(target.id, new_status=UserStatus.INACTIVE, current_user=admin)

    assert deactivated.status == UserStatus.INACTIVE


def test_set_status_reactivates_user(service):
    admin = service.create_user(
        name="Admin", email="admin@example.com", password="correct-password", role=UserRole.ADMIN
    )
    target = service.create_user(
        name="Ana Souza",
        email="ana@example.com",
        password="correct-password",
    )
    service.set_status(target.id, new_status=UserStatus.INACTIVE, current_user=admin)

    reactivated = service.set_status(target.id, new_status=UserStatus.ACTIVE, current_user=admin)

    assert reactivated.status == UserStatus.ACTIVE


def test_set_status_blocks_self_deactivation(service):
    admin = service.create_user(
        name="Admin", email="admin@example.com", password="correct-password", role=UserRole.ADMIN
    )

    with pytest.raises(CannotDeactivateSelfError):
        service.set_status(admin.id, new_status=UserStatus.INACTIVE, current_user=admin)


def test_set_status_not_found_raises(service):
    admin = User(id=uuid.uuid4(), name="Admin", email="admin2@example.com", password_hash="hash")

    with pytest.raises(UserNotFoundError):
        service.set_status(uuid.uuid4(), new_status=UserStatus.INACTIVE, current_user=admin)
