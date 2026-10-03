"""Camada de acesso a dados do histórico de chat do Assistente de IA (Fase 6). Sem
relationship() do SQLAlchemy, mesmo estilo dos demais repositórios."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage, ChatMessageRole


class ChatMessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, message: ChatMessage) -> ChatMessage:
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_all(self, *, user_id: uuid.UUID) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_recent(self, *, user_id: uuid.UUID, limit: int) -> list[ChatMessage]:
        """Últimas `limit` mensagens do usuário, em ordem cronológica — janela
        deslizante de histórico usada para montar o prompt."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        rows = list(self.db.execute(stmt).scalars().all())
        return list(reversed(rows))

    def count_today(self, *, user_id: uuid.UUID, since: datetime) -> int:
        """Conta só mensagens do usuário (role=USER) — não penaliza pelas respostas do
        assistente. Base do rate limit diário."""
        stmt = (
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.role == ChatMessageRole.USER,
                ChatMessage.created_at >= since,
            )
        )
        return self.db.execute(stmt).scalar_one()
