"""Registro de uso ainda não precificado — o que o collector produz e o sink consome.

Fica num módulo próprio (e não em callback.py) para que `pricing.py` possa importá-lo sem
arrastar o LangChain: o cálculo de custo é puro e testável sem nada de IA no caminho.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from app.models.ai_cost import AiUsageFeature, AiUsageOperation


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PendingUsage:
    """Uma chamada à OpenAI, medida mas ainda sem custo. O custo e o `price_id` são
    resolvidos no flush (ver recorder.DbUsageSink), porque dependem da vigência de preço
    válida em `occurred_at` — e isso exige banco."""

    feature: AiUsageFeature
    operation: AiUsageOperation
    model: str
    stage: str | None = None

    occurred_at: datetime = field(default_factory=_utcnow)

    user_id: uuid.UUID | None = None
    analysis_id: uuid.UUID | None = None
    job_run_id: uuid.UUID | None = None
    attempt: int = 0

    calls: int = 1
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    audio_seconds: Decimal | None = None

    tokens_estimated: bool = False
    latency_ms: int | None = None
    error_type: str | None = None
