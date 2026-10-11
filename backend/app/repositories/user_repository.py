from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Row, func, or_, select
from sqlalchemy.orm import Session, aliased

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
        manager_id: uuid.UUID | None = None,
    ) -> list[Row]:
        """Lista usuários trazendo o nome do gestor (self-join) e, para quem é
        GESTOR, o tamanho da equipe (subquery agregada) — ambos em uma única
        query, sem N+1."""
        manager = aliased(User)
        team_sizes = (
            select(User.manager_id.label("manager_id"), func.count().label("team_size"))
            .where(User.manager_id.isnot(None))
            .group_by(User.manager_id)
            .subquery()
        )
        stmt = (
            select(
                User,
                manager.name.label("manager_name"),
                func.coalesce(team_sizes.c.team_size, 0).label("team_size"),
            )
            .outerjoin(manager, manager.id == User.manager_id)
            .outerjoin(team_sizes, team_sizes.c.manager_id == User.id)
            .order_by(User.name.asc())
        )
        if role is not None:
            stmt = stmt.where(User.role == role)
        if status is not None:
            stmt = stmt.where(User.status == status)
        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(func.lower(User.name).like(pattern), func.lower(User.email).like(pattern))
            )
        if manager_id is not None:
            stmt = stmt.where(User.manager_id == manager_id)
        return list(self.db.execute(stmt).all())

    def update(self, user_id: uuid.UUID, **fields: Any) -> User:
        user = self.get(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        for key, value in fields.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user
