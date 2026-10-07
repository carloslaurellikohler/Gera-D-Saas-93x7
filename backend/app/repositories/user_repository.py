from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, UserStatus


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_subordinates(self, manager_id: uuid.UUID) -> list[User]:
        stmt = select(User).where(User.manager_id == manager_id).order_by(User.name.asc())
        return list(self.db.execute(stmt).scalars().all())

    def list(
        self,
        *,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        search: str | None = None,
    ) -> list[User]:
        stmt = select(User).order_by(User.name.asc())
        if role is not None:
            stmt = stmt.where(User.role == role)
        if status is not None:
            stmt = stmt.where(User.status == status)
        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(func.lower(User.name).like(pattern), func.lower(User.email).like(pattern))
            )
        return list(self.db.execute(stmt).scalars().all())

    def update(self, user_id: uuid.UUID, **fields: Any) -> User:
        user = self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        for key, value in fields.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user
