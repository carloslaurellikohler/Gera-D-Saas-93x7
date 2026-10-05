"""Histórico de chat por usuário (Assistente de IA, Fase 6). `conversation_id` separa o
botão "Nova Conversa" do resto do log — não é um cadastro de threads nomeadas, só um
marcador para agrupar mensagens da mesma conversa (NULL = mensagens de antes da feature,
tratadas como uma conversa única contínua). user_id é NOT NULL + CASCADE (como
LearningPathEnrollment): uma mensagem de chat não faz sentido sem o usuário dono dela."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatMessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_user_conversation_created", "user_id", "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[ChatMessageRole] = mapped_column(
        Enum(ChatMessageRole, name="chat_message_role", native_enum=False, length=16), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # NULL = mensagem de antes da feature "Nova Conversa" (sem backfill artificial, mesmo
    # racional de analyses.methodology_version_id) — continua valendo como o histórico
    # único de sempre até o usuário iniciar a primeira conversa nova explicitamente.
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
