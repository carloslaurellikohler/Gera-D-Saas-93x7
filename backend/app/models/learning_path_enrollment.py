"""Modelos de inscrição e conclusão de trilha de treinamento. Progresso da trilha é
CALCULADO em runtime (concluídos/total), nunca persistido como coluna — ver
LearningPathService.list_enrolled. Sem relationship() do SQLAlchemy, mesmo estilo de
learning_path.py."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LearningPathEnrollment(Base):
    """Inscrição de um usuário em uma trilha. user_id é NOT NULL + CASCADE (diferente
    do padrão SET NULL de Content/LearningPath): uma inscrição não tem sentido sem o
    usuário dono dela, então remover o usuário remove a inscrição e, em cascata, as
    conclusões associadas."""

    __tablename__ = "learning_path_enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "learning_path_id", name="uq_enrollment_user_path"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learning_path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )

    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LearningPathItemCompletion(Base):
    """Sinalização binária de que um item (material) de uma trilha foi concluído por
    quem está inscrito. Ligada ao LearningPathItem (não ao Content): o mesmo material
    pode estar em trilhas diferentes, e a conclusão é por-item-de-trilha, não global."""

    __tablename__ = "learning_path_item_completions"
    __table_args__ = (
        UniqueConstraint(
            "enrollment_id", "learning_path_item_id", name="uq_completion_enrollment_item"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_path_enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    learning_path_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_path_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
