"""Metodologia/calibração versionada (Fase 7) — substitui calibration/v1.yaml como fonte
de dados. Nunca importa gera_d_engine (ver engine_integration/calibration_builder.py para
a ponte com o shape Calibration esperado pela engine).

Methodology guarda identidade + ciclo de vida (DRAFT/PUBLISHED/ARCHIVED) + a prosa global
do YAML original num JSONB `content` (objective, pillars, regras, etc. — nunca filtrados
em SQL, sempre injetados em bloco no prompt da engine). MethodologyCategory (6 por versão)
e Calibrator (4 por versão, as faixas de farol) são genuinamente relacionais.

Fase 9 (metodologia V2.1): o racional que a IA aplica para chegar à nota deixou de ser
prosa solta e virou dado estruturado — MethodologyAnchor (a régua observável 0–10 por
critério e por pilar), MethodologyAnchorExample (few-shot: fala literal → nota),
MethodologySubdimension (rubrica 0–4 de auditoria) e MethodologyEligibilityRule (tetos de
faixa: "sem priorização → não elegível para 8+"). Nada disso chega à engine como tabela:
calibration_builder.py COMPILA essas linhas nos slots de texto que a engine já lê, por
isso o pacote engine/ permanece intocado."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
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


class AnchorScope(str, enum.Enum):
    """Uma âncora descreve um nível observável de 0 a 10 — ou de um dos 6 critérios, ou de
    um dos 2 pilares conceituais (93/7), que não são critérios e não recebem peso."""

    CRITERION = "CRITERION"
    PILLAR = "PILLAR"


class EligibilityEffect(str, enum.Enum):
    """CAP impede a nota do critério de passar de `max_score` quando a condição ocorre
    (o Manual V2.1 eliminou pisos automáticos: boa evidência não "protege" nota diante de
    falha crítica). NOTE é regra qualitativa sem teto numérico."""

    CAP = "CAP"
    NOTE = "NOTE"


class Methodology(Base):
    __tablename__ = "methodologies"
    __table_args__ = (
        # Invariante "no máximo 1 PUBLISHED". Nasceu só na migration f49241d88702; está
        # declarada aqui para que Base.metadata.create_all() dos testes também a crie.
        Index(
            "uq_methodology_single_published",
            "status",
            unique=True,
            postgresql_where=text("status = 'PUBLISHED'"),
        ),
    )

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
    # individual_development_not_ranking, forbidden_behaviors) — desde a Fase 9 o shape
    # é validado por schemas.methodology.MethodologyContentIn, não mais dict livre.
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
    anchors: Mapped[list["MethodologyAnchor"]] = relationship(
        back_populates="methodology",
        cascade="all, delete-orphan",
        order_by="MethodologyAnchor.order_index",
    )
    anchor_examples: Mapped[list["MethodologyAnchorExample"]] = relationship(
        back_populates="methodology",
        cascade="all, delete-orphan",
        order_by="MethodologyAnchorExample.order_index",
    )
    subdimensions: Mapped[list["MethodologySubdimension"]] = relationship(
        back_populates="methodology",
        cascade="all, delete-orphan",
        order_by="MethodologySubdimension.order_index",
    )
    eligibility_rules: Mapped[list["MethodologyEligibilityRule"]] = relationship(
        back_populates="methodology",
        cascade="all, delete-orphan",
        order_by="MethodologyEligibilityRule.order_index",
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
    # "O que o critério avalia" — vira criteria[key].description no prompt.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Definição refinada (Fase 9, Manual V2.1 seção 4). Nullable porque uma versão
    # anterior à V2.1 não tem esses blocos; o compilador omite o que for None.
    central_question: Mapped[str | None] = mapped_column(Text)
    what_it_is_not: Mapped[str | None] = mapped_column(Text)
    positive_evidence: Mapped[str | None] = mapped_column(Text)
    negative_evidence: Mapped[str | None] = mapped_column(Text)
    cross_impact_text: Mapped[str | None] = mapped_column(Text)

    # Peso na nota geral ponderada (Fase 9). A soma dos 6 pesos é validada == 1 em
    # MethodologyService.publish(). Numeric, não Float: a soma precisa fechar exata.
    weight: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, server_default=text("0"))

    # Campos opcionais e não-homogêneos por critério no YAML original
    # (good_performance, risks, calibration_note, critical_rule, cross_impact,
    # desired_structure). Legado da V1: desde a Fase 9 o calibration_builder COMPILA
    # esses slots a partir das colunas e tabelas acima, e `extra` só sobrevive como
    # fallback para versões antigas que ainda não têm dado estruturado.
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


class MethodologyAnchor(Base):
    """Âncora comportamental: o descritor observável de um nível da escala 0–10, para um
    critério ou para um pilar. É a régua que impede a IA de atribuir nota livremente
    (Manual V2.1, seções 3 e 8) — 5 por escopo, nos níveis 2/4/6/8/10."""

    __tablename__ = "methodology_anchors"
    __table_args__ = (
        UniqueConstraint("methodology_id", "scope", "scope_key", "level", name="uq_methodology_anchor_level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("methodologies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    scope: Mapped[AnchorScope] = mapped_column(
        Enum(
            AnchorScope,
            name="anchor_scope",
            native_enum=False,
            length=16,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # CriterionKey.value quando scope=CRITERION; "pilar_93"/"pilar_7" quando scope=PILLAR.
    scope_key: Mapped[str] = mapped_column(String(32), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    descriptor: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    methodology: Mapped["Methodology"] = relationship(back_populates="anchors")


class MethodologyAnchorExample(Base):
    """Exemplo ancorado: a fala concreta que caracteriza um nível (Manual V2.1, seção 8).
    É o material few-shot do prompt — o que permite à IA inferir a valoração em vez de
    arbitrá-la. `quote` é nullable porque alguns níveis do Manual trazem só o descritor."""

    __tablename__ = "methodology_anchor_examples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("methodologies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    criterion_key: Mapped[str] = mapped_column(String(32), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario: Mapped[str | None] = mapped_column(Text)
    quote: Mapped[str | None] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    methodology: Mapped["Methodology"] = relationship(back_populates="anchor_examples")


class MethodologySubdimension(Base):
    """Rubrica de auditoria 0–4 (Manual V2.1, seção 7). Instrumento de refinamento dentro
    da âncora, nunca substituto dela. Os 5 níveis ficam em JSONB na própria linha: são 35
    subdimensões por versão, e uma tabela filha viraria 175 linhas sem ganhar validação
    que o pydantic não dê (ver MethodologySubdimensionIn)."""

    __tablename__ = "methodology_subdimensions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("methodologies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    criterion_key: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # Lista de exatamente 5 descritores, índice == nível (0..4).
    levels: Mapped[list] = mapped_column(JSONB, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    methodology: Mapped["Methodology"] = relationship(back_populates="subdimensions")


class MethodologyEligibilityRule(Base):
    """Regra de elegibilidade de faixa (Manual V2.1, seção 9): a condição observável que
    impede um critério de alcançar determinada nota. `scope_key` é um CriterionKey.value
    ou "TRANSVERSAL" para a regra que vale para todos."""

    __tablename__ = "methodology_eligibility_rules"

    TRANSVERSAL_SCOPE_KEY = "TRANSVERSAL"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("methodologies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    scope_key: Mapped[str] = mapped_column(String(32), nullable=False)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    effect: Mapped[EligibilityEffect] = mapped_column(
        Enum(
            EligibilityEffect,
            name="eligibility_effect",
            native_enum=False,
            length=16,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Obrigatório quando effect=CAP, sempre None quando effect=NOTE (validado no schema).
    max_score: Mapped[float | None] = mapped_column(Float)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    methodology: Mapped["Methodology"] = relationship(back_populates="eligibility_rules")
