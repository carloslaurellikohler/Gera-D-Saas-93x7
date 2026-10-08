"""Contabilização e custeio de consumo de IA (FinAI). Nunca importa gera_d_engine — a
captura dos tokens acontece em app/ai_cost/, por callback do LangChain, justamente para não
precisar tocar na engine.

Quatro tabelas:

- AiUsageEvent — uma linha por chamada à OpenAI, com o custo já calculado e **congelado**
  no momento da gravação (snapshot). Congelar em vez de recalcular por join na leitura é o
  que mantém o histórico imutável quando a OpenAI muda de preço: mês fechado não é
  reescrito. `price_id` fica como trilha de auditoria de qual vigência gerou o número.
- AiModelPrice — preço por modelo/operação, versionado por `valid_from`. O preço de um
  evento é a linha com maior `valid_from <= data do evento`.
- AiCostBudget — meta de gasto por mês. Versionada por mês, pelo mesmo motivo que o preço é
  versionado por vigência: "estourei a meta de setembro?" exige a meta *de setembro*, e uma
  linha única reescreveria o julgamento de meses já fechados a cada ajuste.
- AiCostSettings — linha única (UUID fixo semeado pela migration) com o limiar de alerta e a
  taxa USD→BRL de exibição.

Valores monetários são Numeric, nunca Float, e com escala 10. Escala menor não serve: 10
tokens de embedding a US$ 0,02/milhão custam US$ 0,0000002 — com escala 6 isso arredonda
para zero e o custo de embedding desapareceria da soma. `SUM()` sobre numeric no Postgres é
exato; sobre float, desvia.

O orçamento **nunca bloqueia nada** — serve para a barra de consumo e o alerta visual. Os
freios efetivos continuam sendo os volumétricos já existentes
(DAILY_ANALYSIS_LIMIT_PER_OWNER e ASSISTANT_DAILY_MESSAGE_LIMIT).
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Importes só para registrar em Base.metadata as tabelas referenciadas pelas FKs abaixo
# (analyses, users). Sem isso, qualquer consumidor que importe só este módulo — como
# scripts/ingest_methodology.py, que não conhece análise nem usuário — quebra no flush com
# NoReferencedTableError, porque o SQLAlchemy não consegue resolver o alvo da FK. Um modelo
# que declara FK não é utilizável sem o alvo registrado, então a dependência é explícita aqui.
from app.models import analysis as _analysis_models  # noqa: F401
from app.models import user as _user_models  # noqa: F401

# Linha única de AiCostSettings. UUID literal fixo semeado pela migration, mesma técnica da
# migration 5b77efb26e8d (que semeia a metodologia inicial): o repositório sempre lê/escreve
# este ID, o que elimina get_or_create e a corrida que ele traria.
AI_COST_SETTINGS_ID = uuid.UUID("9f2c1b7e-4d3a-4e58-9c81-0a6b5d2f7c40")


class AiUsageFeature(str, enum.Enum):
    """Qual parte do produto originou a chamada."""

    ANALYSIS = "ANALYSIS"
    ASSISTANT = "ASSISTANT"
    INGESTION = "INGESTION"


class AiUsageOperation(str, enum.Enum):
    """Qual tipo de API foi consumida — define também como o custo é calculado:
    CHAT/EMBEDDING por token, TRANSCRIPTION por minuto de áudio."""

    CHAT = "CHAT"
    TRANSCRIPTION = "TRANSCRIPTION"
    EMBEDDING = "EMBEDDING"


class AiUsageCostStatus(str, enum.Enum):
    """Por que o custo de um evento é o que é. Distinguir "custou zero" de "não foi possível
    custear" é o que impede a tela de exibir um total subestimado como se fosse completo."""

    PRICED = "PRICED"  # vigência encontrada e aplicada
    NO_PRICE = "NO_PRICE"  # nenhuma vigência cadastrada para (modelo, operação, data)
    NO_UNITS = "NO_UNITS"  # unidades não medidas (ffprobe falhou, usage_metadata ausente)


class AiUsageEvent(Base):
    __tablename__ = "ai_usage_events"
    __table_args__ = (
        # Predicado de praticamente toda agregação da tela (janela de período + corte por
        # origem), por isso composto em vez de dois índices separados.
        Index("ix_ai_usage_events_occurred_at_feature", "occurred_at", "feature"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    feature: Mapped[AiUsageFeature] = mapped_column(
        Enum(AiUsageFeature, name="ai_usage_feature", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    operation: Mapped[AiUsageOperation] = mapped_column(
        Enum(AiUsageOperation, name="ai_usage_operation", native_enum=False, length=16),
        nullable=False,
    )

    # Etapa de origem, derivada do nome da classe pydantic passada a
    # with_structured_output pelo nó da engine (ver app/ai_cost/stages.py) — determinístico
    # por chamada. Nullable porque um esquema desconhecido é possível se a engine mudar.
    stage: Mapped[str | None] = mapped_column(String(48))

    # Modelo real reportado pela API (response_metadata["model_name"]); cai no modelo
    # configurado só quando a resposta não informa.
    model: Mapped[str] = mapped_column(String(64), nullable=False)

    # SET NULL: o histórico de custo não pode desaparecer junto com o usuário — o gasto
    # aconteceu de fato e precisa continuar somando no total do período. A atribuição
    # degrada para "sem atribuição", o total nunca muda.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # SET NULL e NÃO cascade: existe DELETE /analyses/{id}; com cascade, apagar uma análise
    # apagaria dinheiro já gasto e o total do mês mudaria retroativamente. O preço dessa
    # escolha é que o ranking de análises mais caras só cobre análises existentes.
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="SET NULL"), index=True
    )

    # Agrupa as chamadas de UMA tentativa de job (ou de uma mensagem do assistente), o que
    # permite distinguir as tentativas de uma mesma análise.
    job_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)

    # Tentativa do Celery (0 = primeira execução). É o que torna visível o custo de retry:
    # uma falha transitória tardia reexecuta o pipeline inteiro e reemite todas as chamadas.
    attempt: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )

    # Quantas chamadas à API esta linha representa. >1 só no Whisper chunkado, onde medimos
    # a duração total do arquivo numa linha só (fiel ao faturamento, que é por minuto).
    calls: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default=text("1")
    )

    input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    # Subconjunto de input_tokens (cache hit), faturado mais barato. O input faturado cheio
    # é input_tokens - cached_input_tokens.
    cached_input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    # Subconjunto de output_tokens — breakdown informativo apenas. NUNCA somado ao custo:
    # usage_metadata["output_tokens"] já os inclui, somar seria cobrar em dobro.
    reasoning_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    audio_seconds: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))

    # True = contagem local por tiktoken (embeddings), não reportada pela API.
    tokens_estimated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(18, 10), nullable=False, default=Decimal("0"), server_default=text("0")
    )
    cost_status: Mapped[AiUsageCostStatus] = mapped_column(
        Enum(AiUsageCostStatus, name="ai_usage_cost_status", native_enum=False, length=16),
        nullable=False,
        default=AiUsageCostStatus.NO_UNITS,
    )
    # SET NULL: o custo já está congelado na linha, então perder o ponteiro de auditoria é
    # degradação aceitável. Não há endpoint de DELETE de preço (corrigir = nova vigência).
    price_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_model_prices.id", ondelete="SET NULL"), index=True
    )

    latency_ms: Mapped[int | None] = mapped_column(Integer)
    # Classe da exceção quando a chamada falhou; NULL em sucesso. Uma chamada que falhou é
    # justamente o que explica "gastei e não saiu análise".
    error_type: Mapped[str | None] = mapped_column(String(120))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AiModelPrice(Base):
    """Preço de um modelo para uma operação, válido a partir de `valid_from`.

    Preços de token são expressos **por 1 milhão de tokens**, que é como a OpenAI publica —
    assim o ADMIN digita o número direto da página de preços, sem converter. Transcrição usa
    `usd_per_minute`. As colunas são nullable porque cada operação usa um subconjunto delas
    (chat usa as três de token; embedding só a de input; transcrição só a de minuto).

    Só `valid_from`, sem `valid_to`: com os dois campos existiria a possibilidade de buracos
    e sobreposições inconsistentes. Com um só, a vigência é sempre total e inequívoca, e a
    resolução é `valid_from <= data ORDER BY valid_from DESC LIMIT 1`.
    """

    __tablename__ = "ai_model_prices"
    __table_args__ = (
        UniqueConstraint("model", "operation", "valid_from", name="uq_ai_model_price_vigencia"),
        Index("ix_ai_model_prices_model_operation_valid_from", "model", "operation", "valid_from"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    model: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[AiUsageOperation] = mapped_column(
        Enum(AiUsageOperation, name="ai_usage_operation", native_enum=False, length=16),
        nullable=False,
    )
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)

    input_usd_per_mtok: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    cached_input_usd_per_mtok: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    output_usd_per_mtok: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    usd_per_minute: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))

    # True = valor semeado sem referência pública confiável (os modelos de chat vêm do
    # ambiente e variam por deploy). A tela avisa enquanto houver placeholder vigente, e
    # qualquer edição do ADMIN zera o flag — é a confirmação humana do preço.
    is_placeholder: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    notes: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class AiCostBudget(Base):
    """Meta de gasto de um mês, em USD. `month` é sempre o dia 1 (normalizado no service)."""

    __tablename__ = "ai_cost_budgets"
    __table_args__ = (UniqueConstraint("month", name="uq_ai_cost_budget_month"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    month: Mapped[date] = mapped_column(Date, nullable=False)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class AiCostSettings(Base):
    """Configuração financeira global — sempre uma única linha, de id AI_COST_SETTINGS_ID.

    `usd_to_brl_rate` é taxa manual, usada só para exibir o equivalente aproximado em reais
    ao lado do valor em dólar. **Nenhum valor em BRL é persistido**: a taxa muda, e um valor
    em reais gravado hoje seria mentira amanhã. A conversão acontece na borda de
    apresentação, no frontend.
    """

    __tablename__ = "ai_cost_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    warn_threshold_pct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=80, server_default=text("80")
    )
    usd_to_brl_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    usd_to_brl_rate_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
