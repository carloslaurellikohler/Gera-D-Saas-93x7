from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class AuthService:
    def __init__(self, repo: UserRepository, settings: Settings) -> None:
        self.repo = repo
        self.settings = settings

    def authenticate(self, *, email: str, password: str) -> tuple[User, str]:
        user = self.repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        if user.status != UserStatus.ACTIVE:
            raise InactiveUserError()

        user = self.repo.update(user.id, last_login_at=datetime.now(timezone.utc))
        token = create_access_token(user_id=str(user.id), role=user.role.value, settings=self.settings)
        return user, token

    def create_user(self, *, name: str, email: str, password: str, role: UserRole = UserRole.USER) -> User:
        existing = self.repo.get_by_email(email)
        if existing is not None:
            raise ValueError(f"User with email {email} already exists")
        user = User(name=name, email=email, password_hash=hash_password(password), role=role)
        return self.repo.create(user)
