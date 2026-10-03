"""Metodologia/calibração versionada (Fase 7) — substitui calibration/v1.yaml como fonte
de dados. Nunca importa gera_d_engine (ver engine_integration/calibration_builder.py para
a ponte com o shape Calibration esperado pela engine).

Methodology guarda identidade + ciclo de vida (DRAFT/PUBLISHED/ARCHIVED) + a prosa global
do YAML original num JSONB `content` (objective, pillars, regras, etc. — nunca filtrados
em SQL, sempre injetados em bloco no prompt da engine). MethodologyCategory (6 por versão)
e Calibrator (4 por versão, as faixas de farol) são genuinamente relacionais."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MethodologyStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class FarolColor(str, enum.Enum):
    VERDE = "verde"
    AMARELO = "amarelo"
    LARANJA = "laranja"
    VERMELHO = "vermelho"


class Methodology(Base):
    __tablename__ = "methodologies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Valor exato que vira AnalysisResult.calibration_version (trava do contrato da
    # engine) — não duplicar dentro de `content`.
    calibration_version: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    methodology_name: Mapped[str] = mapped_column(String(64), nullable=False)
    project: Mapped[str] = mapped_column(String(128), nullable=False)

    status: Mapped[MethodologyStatus] = mapped_column(
        Enum(MethodologyStatus, name="methodology_status", native_enum=False, length=16),
        nullable=False,
        default=MethodologyStatus.DRAFT,
        index=True,
    )

    # Prosa/estrutura global não-relacional do YAML (objective, unit_of_analysis,
    # product_principle, contextual_analysis_principle, seniority_and_adaptation,
    # pillars, object_evaluated, score_format, final_score_rule, result_potential,
    # pb_commercial_potential, evidence_basis, evidence_structure,
    # development_taxonomy, suggested_questions_rule, suggested_questions_examples,
    # executive_recommendation_rule, training_notes_rule,
    # individual_development_not_ranking, forbidden_behaviors) — ver
    # engine_integration/calibration_builder.py para o shape exato esperado.
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    categories: Mapped[list["MethodologyCategory"]] = relationship(
        back_populates="methodology",
        cascade="all, delete-orphan",
        order_by="MethodologyCategory.order_index",
    )
    calibrators: Mapped[list["Calibrator"]] = relationship(
        back_populates="methodology",
        cascade="all, delete-orphan",
        order_by="Calibrator.order_index",
    )


class MethodologyCategory(Base):
    """Um registro por critério comportamental (6 por versão de metodologia)."""

    __tablename__ = "methodology_categories"
    __table_args__ = (UniqueConstraint("methodology_id", "key", name="uq_methodology_category_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("methodologies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Deve casar com app.core.constants.CriterionKey — validado em
    # MethodologyService.publish(), nunca tornado dinâmico (CriterionKey também é
    # usado como tipo de coluna em Content/LearningPath, fora do escopo desta fase).
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Campos opcionais e não-homogêneos por critério no YAML original
    # (good_performance, risks, calibration_note, critical_rule, cross_impact,
    # desired_structure) — guardados só quando presentes.
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    methodology: Mapped["Methodology"] = relationship(back_populates="categories")


class Calibrator(Base):
    """Uma faixa de farol (4 por versão de metodologia)."""

    __tablename__ = "calibrators"
    __table_args__ = (UniqueConstraint("methodology_id", "key", name="uq_calibrator_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("methodologies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    key: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[FarolColor] = mapped_column(
        Enum(
            FarolColor,
            name="calibrator_color",
            native_enum=False,
            length=16,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    min: Mapped[float] = mapped_column(Float, nullable=False)
    max: Mapped[float] = mapped_column(Float, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    methodology: Mapped["Methodology"] = relationship(back_populates="calibrators")
