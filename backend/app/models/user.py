"""Modelo de usuário da SaaS. Nada relacionado à engine é armazenado aqui —
o vínculo entre usuários autenticados e Analysis é feito em fase futura."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    GESTOR = "GESTOR"
    COLABORADOR = "COLABORADOR"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=32),
        nullable=False,
        default=UserRole.COLABORADOR,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", native_enum=False, length=32),
        nullable=False,
        default=UserStatus.ACTIVE,
    )

    # Gestor responsável — só relevante quando role == COLABORADOR (validado em
    # UserService, não via CHECK de banco). Hierarquia de um nível só: sem
    # relationship() ORM, igual ao resto do modelo — resolvido via query explícita em
    # UserRepository.list_subordinates.
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Conversa atual do Assistente de IA (Fase 6) — NULL até o usuário clicar em "Nova
    # Conversa" pela primeira vez, ver app/models/chat_message.py::ChatMessage.conversation_id.
    current_assistant_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
