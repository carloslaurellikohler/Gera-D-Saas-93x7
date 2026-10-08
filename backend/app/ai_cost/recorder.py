"""Escopo de contabilização de custo de IA.

====================== INVARIANTE DESTA FEATURE ======================
Falha em contabilizar custo NUNCA falha uma análise nem uma resposta do assistente.
======================================================================

Garantido em quatro camadas:
1. `UsageCollector.raise_error = False` e try/except dentro de cada callback;
2. `track_ai_usage` nunca levanta — o flush inteiro vive num try/except no `finally`;
3. persistência em sessão PRÓPRIA e curta, fora da transação de negócio;
4. ffprobe/tiktoken/preço ausentes degradam para um evento com `cost_status` explícito.

Por que sessão separada, sempre:
- o evento precisa sobreviver a um rollback da transação de negócio — se o pipeline falhou
  no meio, os tokens já queimados são exatamente o número que o dono quer ver;
- uma falha ao gravar custo não pode envenenar nem abortar a sessão do AnalysisRepository;
- e torna o sink injetável nos testes.

O flush acontece no `finally`, ou seja, também quando o bloco levanta. Isso é intencional.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol

from app.ai_cost.callback import UsageCollector, collector_var
from app.ai_cost.pricing import PriceSnapshot, compute_cost
from app.ai_cost.usage import PendingUsage
from app.models.ai_cost import AiUsageEvent, AiUsageFeature

log = logging.getLogger(__name__)


class UsageSink(Protocol):
    """Destino dos eventos acumulados num escopo."""

    def flush(self, events: list[PendingUsage]) -> None: ...


class NullUsageSink:
    """Descarta tudo — usado quando AI_COST_TRACKING_ENABLED é falso."""

    def flush(self, events: list[PendingUsage]) -> None:  # noqa: ARG002
        return None


class DbUsageSink:
    """Precifica e grava os eventos no Postgres, em sessão própria e curta.

    Resolve a vigência de preço de cada evento com cache local por (modelo, operação, data):
    uma análise faz 6-7 chamadas do mesmo modelo no mesmo dia, então é 1 query, não 7.
    """

    def __init__(self, session_factory=None) -> None:
        if session_factory is None:
            from app.db.session import SessionLocal

            session_factory = SessionLocal
        self._session_factory = session_factory

    def flush(self, events: list[PendingUsage]) -> None:
        if not events:
            return

        # Imports locais: evitam ciclo (repositories → models → ... ) e mantêm o módulo
        # importável em teste sem banco configurado.
        from app.repositories.ai_price_repository import AiPriceRepository
        from app.repositories.ai_usage_repository import AiUsageRepository

        session = self._session_factory()
        try:
            prices = AiPriceRepository(session)
            cache: dict[tuple[str, object, object], PriceSnapshot | None] = {}
            rows: list[AiUsageEvent] = []

            for event in events:
                snapshot = _resolve_cached(prices, cache, event)
                cost_usd, cost_status, price_id = compute_cost(event, snapshot)
                rows.append(
                    AiUsageEvent(
                        occurred_at=event.occurred_at,
                        feature=event.feature,
                        operation=event.operation,
                        stage=event.stage,
                        model=event.model,
                        user_id=event.user_id,
                        analysis_id=event.analysis_id,
                        job_run_id=event.job_run_id,
                        attempt=event.attempt,
                        calls=event.calls,
                        input_tokens=event.input_tokens,
                        output_tokens=event.output_tokens,
                        cached_input_tokens=event.cached_input_tokens,
                        reasoning_tokens=event.reasoning_tokens,
                        audio_seconds=event.audio_seconds,
                        tokens_estimated=event.tokens_estimated,
                        cost_usd=cost_usd,
                        cost_status=cost_status,
                        price_id=price_id,
                        latency_ms=event.latency_ms,
                        error_type=event.error_type,
                    )
                )
            AiUsageRepository(session).bulk_create(rows)
        finally:
            session.close()


def _resolve_cached(
    prices, cache: dict, event: PendingUsage
) -> PriceSnapshot | None:
    key = (event.model, event.operation, event.occurred_at.date())
    if key not in cache:
        price = prices.resolve(
            model=event.model, operation=event.operation, on_date=event.occurred_at.date()
        )
        cache[key] = (
            PriceSnapshot(
                price_id=price.id,
                input_usd_per_mtok=price.input_usd_per_mtok,
                cached_input_usd_per_mtok=price.cached_input_usd_per_mtok,
                output_usd_per_mtok=price.output_usd_per_mtok,
                usd_per_minute=price.usd_per_minute,
            )
            if price is not None
            else None
        )
    return cache[key]


def get_usage_sink() -> UsageSink:
    """Sink padrão, respeitando o kill switch de configuração."""
    from app.core.config import get_settings

    if not get_settings().AI_COST_TRACKING_ENABLED:
        return NullUsageSink()
    return DbUsageSink()


@contextmanager
def track_ai_usage(
    *,
    feature: AiUsageFeature,
    user_id: uuid.UUID | None = None,
    analysis_id: uuid.UUID | None = None,
    job_run_id: uuid.UUID | None = None,
    attempt: int = 0,
    default_stage: str | None = None,
    sink: UsageSink | None = None,
) -> Iterator[UsageCollector]:
    """Contabiliza todas as chamadas de LLM feitas dentro do bloco — inclusive as que
    acontecem dentro de `engine/`, via o hook de ContextVar (ver callback.py).

    Nunca levanta: qualquer falha de contabilização é logada e engolida.
    """
    collector = UsageCollector(
        feature=feature,
        user_id=user_id,
        analysis_id=analysis_id,
        job_run_id=job_run_id,
        attempt=attempt,
        default_stage=default_stage,
    )
    resolved_sink = sink if sink is not None else get_usage_sink()

    token = collector_var.set(collector)
    try:
        yield collector
    finally:
        try:
            collector_var.reset(token)
        except Exception:  # noqa: BLE001
            log.warning("falha ao limpar o contexto de contabilizacao de IA", exc_info=True)
        try:
            resolved_sink.flush(collector.drain())
        except Exception:  # noqa: BLE001 — o INVARIANTE desta feature, ver docstring
            log.exception("falha ao persistir consumo de IA; a operacao segue normalmente")
