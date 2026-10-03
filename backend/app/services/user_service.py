"""Orquestração da gestão administrativa de usuários (criar, editar, inativar,
reativar). Distinto de AuthService, que cobre login/logout/sessão."""

from __future__ import annotations

import uuid

from app.core.security import hash_password
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository


class UserNotFoundError(ValueError):
    def __init__(self) -> None:
        super().__init__("Usuário não encontrado.")


class EmailAlreadyExistsError(ValueError):
    def __init__(self) -> None:
        super().__init__("Já existe um usuário com este e-mail.")


class CannotDeactivateSelfError(ValueError):
    def __init__(self) -> None:
        super().__init__("Você não pode inativar sua própria conta.")


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    def list_users(
        self,
        *,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        search: str | None = None,
    ) -> list[User]:
        return self.repo.list(role=role, status=status, search=search)

    def create_user(
        self, *, name: str, email: str, password: str, role: UserRole = UserRole.USER
    ) -> User:
        if self.repo.get_by_email(email) is not None:
            raise EmailAlreadyExistsError()
        user = User(name=name, email=email, password_hash=hash_password(password), role=role)
        return self.repo.create(user)

    def update_user(self, user_id: uuid.UUID, *, name: str, email: str, role: UserRole) -> User:
        user = self.repo.get(user_id)
        if user is None:
            raise UserNotFoundError()
        existing = self.repo.get_by_email(email)
        if existing is not None and existing.id != user_id:
            raise EmailAlreadyExistsError()
        return self.repo.update(user_id, name=name, email=email, role=role)

    def set_status(
        self, user_id: uuid.UUID, *, new_status: UserStatus, current_user: User
    ) -> User:
        if user_id == current_user.id and new_status == UserStatus.INACTIVE:
            raise CannotDeactivateSelfError()
        user = self.repo.get(user_id)
        if user is None:
            raise UserNotFoundError()
        return self.repo.update(user_id, status=new_status)
