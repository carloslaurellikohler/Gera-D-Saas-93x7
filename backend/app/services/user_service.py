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


class InvalidManagerAssignmentError(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "manager_id deve apontar para um usuário ativo com papel GESTOR, e só é "
            "válido para usuários COLABORADOR."
        )


class GestorComEquipeError(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "Este usuário ainda é Gestor de uma equipe. Reatribua os colaboradores a "
            "outro Gestor antes de trocar o papel ou inativar esta conta."
        )


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

    def list_subordinates(self, manager_id: uuid.UUID) -> list[User]:
        return self.repo.list_subordinates(manager_id)

    def create_user(
        self,
        *,
        name: str,
        email: str,
        password: str,
        role: UserRole = UserRole.COLABORADOR,
        manager_id: uuid.UUID | None = None,
    ) -> User:
        if self.repo.get_by_email(email) is not None:
            raise EmailAlreadyExistsError()
        self._validate_manager_assignment(role=role, manager_id=manager_id)
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            manager_id=manager_id,
        )
        return self.repo.create(user)

    def update_user(
        self,
        user_id: uuid.UUID,
        *,
        name: str,
        email: str,
        role: UserRole,
        manager_id: uuid.UUID | None = None,
    ) -> User:
        user = self.repo.get(user_id)
        if user is None:
            raise UserNotFoundError()
        existing = self.repo.get_by_email(email)
        if existing is not None and existing.id != user_id:
            raise EmailAlreadyExistsError()
        self._validate_manager_assignment(role=role, manager_id=manager_id)
        if user.role == UserRole.GESTOR and role != UserRole.GESTOR and self.repo.list_subordinates(user_id):
            raise GestorComEquipeError()
        return self.repo.update(user_id, name=name, email=email, role=role, manager_id=manager_id)

    def set_status(
        self, user_id: uuid.UUID, *, new_status: UserStatus, current_user: User
    ) -> User:
        if user_id == current_user.id and new_status == UserStatus.INACTIVE:
            raise CannotDeactivateSelfError()
        user = self.repo.get(user_id)
        if user is None:
            raise UserNotFoundError()
        if (
            new_status == UserStatus.INACTIVE
            and user.role == UserRole.GESTOR
            and self.repo.list_subordinates(user_id)
        ):
            raise GestorComEquipeError()
        return self.repo.update(user_id, status=new_status)

    def _validate_manager_assignment(
        self, *, role: UserRole, manager_id: uuid.UUID | None
    ) -> None:
        if manager_id is None:
            return
        if role != UserRole.COLABORADOR:
            raise InvalidManagerAssignmentError()
        manager = self.repo.get(manager_id)
        if manager is None or manager.role != UserRole.GESTOR or manager.status != UserStatus.ACTIVE:
            raise InvalidManagerAssignmentError()

    def reset_password(self, user_id: uuid.UUID, *, new_password: str) -> User:
        user = self.repo.get(user_id)
        if user is None:
            raise UserNotFoundError()
        return self.repo.update(user_id, password_hash=hash_password(new_password))
