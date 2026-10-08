"""Camada de leitura dos indicadores de custo de IA (FinAI). Só consulta `ai_usage_events` —
nunca grava (a gravação é de AiUsageRepository). Devolve tuplas cruas; formatação (pct,
rótulos, conversão para float na borda) fica no service, como em DashboardRepository.

**Toda agregação acontece em SQL**, diferente de MetricsRepository, que traz linhas cruas e
soma em Python. Aqui o volume é outro: são 6-10 linhas por análise (uma por chamada à
OpenAI), uma ordem de grandeza acima de `analyses`.

As somas saem como `Decimal` (coluna Numeric) e devem permanecer `Decimal` até a borda
pydantic — somar custo em float desvia.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import Date, Row, String, cast, distinct, func, select
from sqlalchemy.orm import Session, aliased

from app.models.ai_cost import AiUsageCostStatus, AiUsageEvent
from app.models.analysis import Analysis
from app.models.user import User

_ZERO = Decimal("0")
_TOTAL = func.coalesce(func.sum(AiUsageEvent.cost_usd), _ZERO)

Dimension = Literal["feature", "operation", "model", "stage"]
TrendBucket = Literal["day", "week"]

_DIMENSION_COLUMNS = {
    "feature": AiUsageEvent.feature,
    "operation": AiUsageEvent.operation,
    "model": AiUsageEvent.model,
    "stage": AiUsageEvent.stage,
}


class AiCostRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def kpis(self, *, since: date) -> Row:
        """Um único SELECT com todos os totais do período. FILTER (padrão SQL, suportado
        pelo Postgres) evita uma query por recorte."""
        stmt = select(
            _TOTAL.label("total_usd"),
            func.count().label("events"),
            func.count(distinct(AiUsageEvent.analysis_id)).label("analyses_with_cost"),
            func.count()
            .filter(AiUsageEvent.feature == "ASSISTANT", AiUsageEvent.operation == "CHAT")
            .label("assistant_messages"),
            # attempt > 0 é custo de retentativa: o pipeline inteiro reexecutado.
            func.coalesce(
                func.sum(AiUsageEvent.cost_usd).filter(AiUsageEvent.attempt > 0), _ZERO
            ).label("retry_usd"),
            func.count().filter(AiUsageEvent.attempt > 0).label("retry_events"),
            func.coalesce(func.sum(AiUsageEvent.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(AiUsageEvent.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(AiUsageEvent.cached_input_tokens), 0).label("cached_input_tokens"),
            func.coalesce(func.sum(AiUsageEvent.reasoning_tokens), 0).label("reasoning_tokens"),
            func.coalesce(func.sum(AiUsageEvent.audio_seconds), _ZERO).label("audio_seconds"),
            # Os dois contadores que mantêm a tela honesta sobre subcontagem.
            func.count()
            .filter(AiUsageEvent.cost_status == AiUsageCostStatus.NO_PRICE)
            .label("unpriced_events"),
            func.count()
            .filter(AiUsageEvent.cost_status == AiUsageCostStatus.NO_UNITS)
            .label("no_units_events"),
            func.count().filter(AiUsageEvent.error_type.is_not(None)).label("failed_calls"),
        ).where(AiUsageEvent.occurred_at >= since)
        return self.db.execute(stmt).one()

    def breakdown_by(self, *, dimension: Dimension, since: date) -> list[Row]:
        column = _DIMENSION_COLUMNS[dimension]
        stmt = (
            select(cast(column, String).label("key"), _TOTAL.label("total_usd"), func.count().label("events"))
            .where(AiUsageEvent.occurred_at >= since)
            .group_by(column)
            .order_by(_TOTAL.desc())
        )
        return list(self.db.execute(stmt).all())

    def trend(self, *, since: date, bucket: TrendBucket) -> list[Row]:
        period_start = cast(func.date_trunc(bucket, AiUsageEvent.occurred_at), Date)
        stmt = (
            select(period_start.label("period_start"), _TOTAL.label("total_usd"), func.count().label("events"))
            .where(AiUsageEvent.occurred_at >= since)
            .group_by(period_start)
            .order_by(period_start)
        )
        return list(self.db.execute(stmt).all())

    def trend_by_feature(self, *, since: date, bucket: TrendBucket) -> list[Row]:
        """Série empilhada: mostra como a composição do gasto muda, não só o total."""
        period_start = cast(func.date_trunc(bucket, AiUsageEvent.occurred_at), Date)
        stmt = (
            select(
                period_start.label("period_start"),
                cast(AiUsageEvent.feature, String).label("feature"),
                _TOTAL.label("total_usd"),
            )
            .where(AiUsageEvent.occurred_at >= since)
            .group_by(period_start, AiUsageEvent.feature)
            .order_by(period_start)
        )
        return list(self.db.execute(stmt).all())

    def top_users(self, *, since: date, limit: int = 10) -> list[Row]:
        """Ranking por usuário, com o gestor de cada um (hierarquia de equipe via
        users.manager_id) — é o que responde "qual equipe está gastando"."""
        manager = aliased(User)
        stmt = (
            select(
                AiUsageEvent.user_id,
                User.name.label("name"),
                cast(User.role, String).label("role"),
                manager.name.label("manager_name"),
                _TOTAL.label("total_usd"),
                func.count().label("events"),
                func.count(distinct(AiUsageEvent.analysis_id)).label("analyses"),
            )
            .outerjoin(User, User.id == AiUsageEvent.user_id)
            .outerjoin(manager, manager.id == User.manager_id)
            .where(AiUsageEvent.occurred_at >= since)
            .group_by(AiUsageEvent.user_id, User.name, User.role, manager.name)
            .order_by(_TOTAL.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).all())

    def top_analyses(self, *, since: date, limit: int = 10) -> list[Row]:
        owner = aliased(User)
        stmt = (
            select(
                AiUsageEvent.analysis_id,
                Analysis.participant_name,
                Analysis.input_type,
                Analysis.created_at,
                owner.name.label("owner_name"),
                func.max(AiUsageEvent.attempt).label("attempts"),
                _TOTAL.label("total_usd"),
                func.count().label("events"),
            )
            .join(Analysis, Analysis.id == AiUsageEvent.analysis_id)
            .outerjoin(owner, owner.id == Analysis.owner_id)
            .where(AiUsageEvent.occurred_at >= since)
            .group_by(
                AiUsageEvent.analysis_id,
                Analysis.participant_name,
                Analysis.input_type,
                Analysis.created_at,
                owner.name,
            )
            .order_by(_TOTAL.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).all())

    def spend_between(self, *, start: date, end: date) -> Decimal:
        """Gasto em [start, end) — usado para o consumo do mês corrente."""
        stmt = select(_TOTAL).where(
            AiUsageEvent.occurred_at >= start, AiUsageEvent.occurred_at < end
        )
        return self.db.execute(stmt).scalar_one()

    def first_event_at(self) -> datetime | None:
        """Início da contabilização. A tela declara essa data, porque não há backfill —
        análises anteriores simplesmente não têm dados de token."""
        return self.db.execute(select(func.min(AiUsageEvent.occurred_at))).scalar_one()

    def list_events(
        self,
        *,
        since: date,
        feature: str | None = None,
        operation: str | None = None,
        model: str | None = None,
        user_id: uuid.UUID | None = None,
        analysis_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Row], int]:
        """Eventos crus paginados, com o total REAL de linhas.

        O total vem de um COUNT próprio, e não de len(itens) como em routes/analyses.py —
        numa tela financeira saber quantos eventos existem de fato é o ponto.
        """
        filters = [AiUsageEvent.occurred_at >= since]
        if feature:
            filters.append(AiUsageEvent.feature == feature)
        if operation:
            filters.append(AiUsageEvent.operation == operation)
        if model:
            filters.append(AiUsageEvent.model == model)
        if user_id is not None:
            filters.append(AiUsageEvent.user_id == user_id)
        if analysis_id is not None:
            filters.append(AiUsageEvent.analysis_id == analysis_id)

        total = self.db.execute(
            select(func.count()).select_from(AiUsageEvent).where(*filters)
        ).scalar_one()

        stmt = (
            select(
                AiUsageEvent.id,
                AiUsageEvent.occurred_at,
                cast(AiUsageEvent.feature, String).label("feature"),
                cast(AiUsageEvent.operation, String).label("operation"),
                AiUsageEvent.stage,
                AiUsageEvent.model,
                AiUsageEvent.user_id,
                User.name.label("user_name"),
                AiUsageEvent.analysis_id,
                AiUsageEvent.attempt,
                AiUsageEvent.calls,
                AiUsageEvent.input_tokens,
                AiUsageEvent.output_tokens,
                AiUsageEvent.cached_input_tokens,
                AiUsageEvent.audio_seconds,
                AiUsageEvent.cost_usd,
                cast(AiUsageEvent.cost_status, String).label("cost_status"),
                AiUsageEvent.tokens_estimated,
                AiUsageEvent.latency_ms,
                AiUsageEvent.error_type,
            )
            .outerjoin(User, User.id == AiUsageEvent.user_id)
            .where(*filters)
            .order_by(AiUsageEvent.occurred_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).all()), total

    def distinct_models(self) -> Sequence[str]:
        """Alimenta o filtro de modelo na tela, sem o frontend adivinhar nomes."""
        stmt = select(AiUsageEvent.model).distinct().order_by(AiUsageEvent.model)
        return list(self.db.execute(stmt).scalars().all())
