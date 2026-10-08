"""Cálculo de custo em USD a partir de unidades consumidas + preço vigente. Funções puras,
sem banco e sem I/O — o que torna cada regra abaixo testável isoladamente.

Duas regras aqui são contraintuitivas e erradas na primeira tentativa de quem implementa
isso, então ficam explícitas:

1. `usage_metadata["output_tokens"]` JÁ INCLUI os reasoning tokens. Somar `reasoning_tokens`
   ao custo cobraria em dobro. Eles existem só como breakdown na tela.
2. `usage_metadata["input_tokens"]` JÁ INCLUI os tokens lidos do cache. O input faturado
   cheio é `input_tokens - cached_input_tokens`, e o restante vai ao preço de cache.

Quando falta unidade medida ou falta preço, o custo é zero mas o **status** diz o porquê
(NO_UNITS / NO_PRICE). Nunca estimamos: um total explicitamente incompleto é honesto; um
total subestimado que se apresenta como completo, não.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.ai_cost.usage import PendingUsage
from app.models.ai_cost import AiUsageCostStatus, AiUsageOperation

_MTOK = Decimal(1_000_000)
_SECONDS_PER_MINUTE = Decimal(60)

# Mesma escala da coluna cost_usd (Numeric(18, 10)). Escala menor zeraria custo de
# embedding: 10 tokens a US$ 0,02/milhão = US$ 0,0000002.
_COST_QUANTUM = Decimal("0.0000000001")


@dataclass(frozen=True)
class PriceSnapshot:
    """Preço já resolvido para a data do evento — desacopla o cálculo do ORM."""

    price_id: uuid.UUID
    input_usd_per_mtok: Decimal | None = None
    cached_input_usd_per_mtok: Decimal | None = None
    output_usd_per_mtok: Decimal | None = None
    usd_per_minute: Decimal | None = None


def has_measured_units(usage: PendingUsage) -> bool:
    """Se há unidade de cobrança medida. Chamada que falhou, resposta sem `usage_metadata` e
    ffprobe indisponível caem todos aqui — e o custo fica 0 com status NO_UNITS."""
    if usage.operation is AiUsageOperation.TRANSCRIPTION:
        return usage.audio_seconds is not None and usage.audio_seconds > 0
    return (usage.input_tokens + usage.output_tokens) > 0


def compute_cost(
    usage: PendingUsage, price: PriceSnapshot | None
) -> tuple[Decimal, AiUsageCostStatus, uuid.UUID | None]:
    """Devolve (custo em USD, status, price_id aplicado)."""
    if not has_measured_units(usage):
        return Decimal("0"), AiUsageCostStatus.NO_UNITS, None

    if price is None or not _covers(usage.operation, price):
        # Preço ausente, ou cadastrado sem o campo que esta operação precisa (ex.: linha de
        # CHAT sem preço de output). Os dois casos são "não sei custear", não "custou zero".
        return Decimal("0"), AiUsageCostStatus.NO_PRICE, None

    if usage.operation is AiUsageOperation.TRANSCRIPTION:
        minutes = Decimal(usage.audio_seconds) / _SECONDS_PER_MINUTE
        raw = minutes * Decimal(price.usd_per_minute)
    elif usage.operation is AiUsageOperation.EMBEDDING:
        raw = Decimal(usage.input_tokens) / _MTOK * Decimal(price.input_usd_per_mtok)
    else:  # CHAT
        raw = _chat_cost(usage, price)

    return _quantize(raw), AiUsageCostStatus.PRICED, price.price_id


def _chat_cost(usage: PendingUsage, price: PriceSnapshot) -> Decimal:
    input_price = Decimal(price.input_usd_per_mtok)
    # Sem preço de cache cadastrado, o token cacheado é cobrado como input cheio: erra para
    # cima, nunca para baixo. Subestimar custo é a falha mais perigosa nesta tela.
    cached_price = (
        Decimal(price.cached_input_usd_per_mtok)
        if price.cached_input_usd_per_mtok is not None
        else input_price
    )
    cached = max(0, min(usage.cached_input_tokens, usage.input_tokens))
    billable_input = usage.input_tokens - cached

    return (
        Decimal(billable_input) / _MTOK * input_price
        + Decimal(cached) / _MTOK * cached_price
        # reasoning_tokens NÃO entra: já está dentro de output_tokens.
        + Decimal(usage.output_tokens) / _MTOK * Decimal(price.output_usd_per_mtok)
    )


def _covers(operation: AiUsageOperation, price: PriceSnapshot) -> bool:
    """Se a vigência tem os campos que a operação exige para ser custeada."""
    if operation is AiUsageOperation.TRANSCRIPTION:
        return price.usd_per_minute is not None
    if operation is AiUsageOperation.EMBEDDING:
        return price.input_usd_per_mtok is not None
    return price.input_usd_per_mtok is not None and price.output_usd_per_mtok is not None


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_COST_QUANTUM, rounding=ROUND_HALF_UP)
