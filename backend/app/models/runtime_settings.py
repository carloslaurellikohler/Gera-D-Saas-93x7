"""Configuração operacional editável em runtime pelo ADMIN (tela /configuracoes).

Terceira aplicação do mesmo movimento das Fases 7 e 8: tirar do `.env` o que é decisão
operacional e não de infraestrutura. A Fase 7 fez isso com a calibração (YAML → Postgres,
tela /calibracao) e a Fase 8 com preço/orçamento/câmbio (env → Postgres, tela /custos-ia).
Aqui são seis valores: os dois limites diários de uso e o modelo+temperatura da análise e
do assistente.

**O banco sempre vence.** As variáveis de ambiente correspondentes passam a ser apenas
bootstrap: a migration de seed copia o ambiente para esta linha e, a partir dali, só a tela
manda — mudar a env var num deploy já migrado não tem efeito. Os campos de `app/core/config.py`
permanecem como fallback para o caso de a linha não existir (banco novo, testes com
`create_all`). A sobreposição acontece num único ponto:
`app/services/runtime_settings_service.py::build_effective_settings`.

O que **não** vive aqui: `OPENAI_API_KEY` é segredo de ambiente, não configuração de admin.

Auditoria é só do último editor (`updated_at` + `updated_by_id`), sem tabela de histórico —
mesma escolha de `AiCostSettings`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models import user as _user_models  # noqa: F401 — registra users como alvo da FK abaixo

# Linha única de RuntimeSettings. UUID literal fixo semeado pela migration, mesma técnica de
# AI_COST_SETTINGS_ID (app/models/ai_cost.py): o repositório sempre lê/escreve este ID, o que
# elimina get_or_create e a corrida que ele traria.
RUNTIME_SETTINGS_ID = uuid.UUID("9978481d-2674-4baa-baed-3b4d5e495f07")


class RuntimeSettings(Base):
    """Configuração operacional global — sempre uma única linha, de id RUNTIME_SETTINGS_ID.

    As temperaturas são `Numeric(3, 2)` e não `Float` de propósito: a tela devolve o número
    num `<input type="number">`, e um `0.30000000000000004` vindo de binário flutuante é bug
    de percepção numa tela de administração. O cast para `float` acontece na borda, em
    `build_effective_settings` (o ChatOpenAI e o schema de resposta não aceitam Decimal).
    """

    __tablename__ = "runtime_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    # Limite diário de análises por colaborador (owner_id) — ADMIN é isento quando sobe para
    # si mesmo; GESTOR nunca é isento. Reset à meia-noite UTC. Ver AnalysisService.get_daily_quota.
    daily_analysis_limit_per_owner: Mapped[int] = mapped_column(
        Integer, nullable=False, default=4, server_default=text("4")
    )
    # Mensagens do usuário por dia no assistente (respostas do assistente não contam).
    # Ver AssistantService._check_rate_limit.
    assistant_daily_message_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default=text("30")
    )

    # Modelo do pipeline pesado de análise — chega à engine por engine_settings_builder,
    # nunca mais por os.getenv("OPENAI_MODEL") no caminho do backend.
    analysis_model: Mapped[str] = mapped_column(String(120), nullable=False)
    analysis_temperature: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)

    # Modelo do chat do assistente — distinto do da análise de propósito (mais barato).
    assistant_model: Mapped[str] = mapped_column(String(120), nullable=False)
    assistant_temperature: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)

    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
