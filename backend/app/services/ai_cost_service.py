"""Orquestração do FinAI — observabilidade de custo de IA para o ADMIN.

Só leitura no caminho de consumo (nunca toca engine/storage/OpenAI), mais a gestão de preços
e de configuração financeira. Delega as agregações ao AiCostRepository, que as faz em SQL, e
cuida aqui da formatação (pct, rótulos, conversão Decimal→float na borda) e do cálculo de
orçamento, seguindo o mesmo desenho de DashboardService.

O orçamento **nunca bloqueia nada**: este service não participa de create_and_store nem do
rate limit do assistente. Ele informa.

Sem dados no período é sempre 200 com zeros, listas vazias e None — nunca erro (precedente
explícito da Fase 4).
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.ai_cost.pricing import PriceSnapshot, compute_cost
from app.ai_cost.stages import stage_label
from app.ai_cost.usage import PendingUsage
from app.models.ai_cost import AiModelPrice, AiUsageOperation
from app.models.user import User
from app.repositories.ai_cost_config_repository import AiCostConfigRepository
from app.repositories.ai_cost_repository import AiCostRepository
from app.repositories.ai_price_repository import AiPriceRepository
from app.repositories.ai_usage_repository import AiUsageRepository
from app.schemas.ai_cost import (
    AiCostAnalysisRow,
    AiCostBreakdownItem,
    AiCostBudgetStatusResponse,
    AiCostConfigResponse,
    AiCostKpis,
    AiCostStackedTrendPoint,
    AiCostSummaryResponse,
    AiCostTrendPoint,
    AiCostUserRow,
    AiModelPriceResponse,
    AiUsageEventItem,
    AiUsageEventPage,
    Period,
)

_PERIOD_DAYS: dict[str, int] = {"7d": 7, "30d": 30, "90d": 90}

# Bucket diário para janelas curtas; semanal para 90d, senão o gráfico vira ruído.
_PERIOD_BUCKET: dict[str, str] = {"7d": "day", "30d": "day", "mtd": "day", "90d": "week"}

_FEATURE_LABELS = {
    "ANALYSIS": "Análises",
    "ASSISTANT": "Assistente de IA",
    "INGESTION": "Ingestão do corpus",
}
_OPERATION_LABELS = {
    "CHAT": "Chat (análise e assistente)",
    "TRANSCRIPTION": "Transcrição de áudio",
    "EMBEDDING": "Embeddings",
}

_SECONDS_PER_MINUTE = Decimal(60)


class AiPriceNotFoundError(ValueError):
    def __init__(self) -> None:
        super().__init__("Preço não encontrado.")


class DuplicatePriceVigenciaError(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "Já existe um preço cadastrado para este modelo, operação e data de vigência."
        )


class InvalidPricePayloadError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)


class AiCostService:
    def __init__(
        self,
        repo: AiCostRepository,
        price_repo: AiPriceRepository,
        config_repo: AiCostConfigRepository,
        usage_repo: AiUsageRepository,
    ) -> None:
        self.repo = repo
        self.price_repo = price_repo
        self.config_repo = config_repo
        self.usage_repo = usage_repo

    # --- Leitura ---

    def get_summary(self, *, period: Period = "30d", today: date | None = None) -> AiCostSummaryResponse:
        today = today or date.today()
        since = self._period_start(period, today)
        bucket = _PERIOD_BUCKET[period]

        kpis_row = self.repo.kpis(since=since)
        total = _dec(kpis_row.total_usd)

        settings = self.config_repo.get_settings()

        by_feature = self._breakdown("feature", since, total, _FEATURE_LABELS)
        # Custo do assistente sai do próprio breakdown, em vez de uma query extra só para
        # isso — a média por mensagem é o número que diz se o chat vale o que custa.
        by_feature_usd = {item.key: _dec(item.total_usd) for item in by_feature}
        assistant_usd = by_feature_usd.get("ASSISTANT", Decimal("0"))
        analysis_usd = by_feature_usd.get("ANALYSIS", Decimal("0"))

        return AiCostSummaryResponse(
            period=period,
            trend_bucket=bucket,
            tracking_started_at=self.repo.first_event_at(),
            usd_to_brl_rate=_float_or_none(settings.usd_to_brl_rate if settings else None),
            has_placeholder_prices=self.price_repo.has_placeholder_in_effect(on_date=today),
            kpis=self._build_kpis(kpis_row, analysis_usd=analysis_usd, assistant_usd=assistant_usd),
            by_feature=by_feature,
            by_operation=self._breakdown("operation", since, total, _OPERATION_LABELS),
            by_model=self._breakdown("model", since, total, {}),
            by_stage=self._breakdown("stage", since, total, None),
            trend=[
                AiCostTrendPoint(
                    period_start=row.period_start,
                    total_usd=_float(row.total_usd),
                    events=row.events,
                )
                for row in self.repo.trend(since=since, bucket=bucket)
            ],
            trend_by_feature=self._stacked_trend(since, bucket),
            top_users=[
                AiCostUserRow(
                    user_id=str(row.user_id) if row.user_id else None,
                    name=row.name or "Sem atribuição",
                    role=row.role,
                    manager_name=row.manager_name,
                    total_usd=_float(row.total_usd),
                    events=row.events,
                    analyses=row.analyses,
                )
                for row in self.repo.top_users(since=since)
            ],
            top_analyses=[
                AiCostAnalysisRow(
                    analysis_id=str(row.analysis_id) if row.analysis_id else None,
                    participant_name=row.participant_name,
                    owner_name=row.owner_name,
                    input_type=row.input_type,
                    created_at=row.created_at,
                    attempts=row.attempts or 0,
                    total_usd=_float(row.total_usd),
                    events=row.events,
                )
                for row in self.repo.top_analyses(since=since)
            ],
            budget=self.get_budget_status(today=today),
        )

    def _build_kpis(self, row, *, analysis_usd: Decimal, assistant_usd: Decimal) -> AiCostKpis:
        total = _dec(row.total_usd)
        analyses = row.analyses_with_cost or 0
        messages = row.assistant_messages or 0
        # Média por análise usa só o custo da feature ANALYSIS (transcrição + as 6-7
        # chamadas de chat do pipeline). A ingestão do corpus é custo de manutenção, não
        # de análise, e entraria distorcendo a média se usássemos o total do período.
        return AiCostKpis(
            total_usd=_float(total),
            events=row.events or 0,
            analyses_with_cost=analyses,
            avg_usd_per_analysis=_float(analysis_usd / analyses) if analyses else None,
            assistant_messages=messages,
            avg_usd_per_assistant_message=_float(assistant_usd / messages) if messages else None,
            retry_usd=_float(row.retry_usd),
            retry_events=row.retry_events or 0,
            input_tokens=row.input_tokens or 0,
            output_tokens=row.output_tokens or 0,
            cached_input_tokens=row.cached_input_tokens or 0,
            reasoning_tokens=row.reasoning_tokens or 0,
            audio_minutes=_float(_dec(row.audio_seconds) / _SECONDS_PER_MINUTE),
            unpriced_events=row.unpriced_events or 0,
            no_units_events=row.no_units_events or 0,
            failed_calls=row.failed_calls or 0,
        )

    def _breakdown(
        self, dimension: str, since: date, total: Decimal, labels: dict[str, str] | None
    ) -> list[AiCostBreakdownItem]:
        items = []
        for row in self.repo.breakdown_by(dimension=dimension, since=since):
            key = row.key or "—"
            if labels is None:  # dimensão de etapa: rótulo vem de ai_cost/stages.py
                label = stage_label(row.key)
            else:
                label = labels.get(key, key)
            items.append(
                AiCostBreakdownItem(
                    key=key,
                    label=label,
                    total_usd=_float(row.total_usd),
                    events=row.events,
                    pct=_format_pct(_dec(row.total_usd), total),
                )
            )
        return items

    def _stacked_trend(self, since: date, bucket: str) -> list[AiCostStackedTrendPoint]:
        buckets: dict[date, dict[str, Decimal]] = {}
        for row in self.repo.trend_by_feature(since=since, bucket=bucket):
            slot = buckets.setdefault(row.period_start, {})
            slot[row.feature] = _dec(row.total_usd)
        return [
            AiCostStackedTrendPoint(
                period_start=period_start,
                analysis_usd=_float(values.get("ANALYSIS", Decimal("0"))),
                assistant_usd=_float(values.get("ASSISTANT", Decimal("0"))),
                ingestion_usd=_float(values.get("INGESTION", Decimal("0"))),
            )
            for period_start, values in sorted(buckets.items())
        ]

    def list_events(
        self,
        *,
        period: Period = "30d",
        feature: str | None = None,
        operation: str | None = None,
        model: str | None = None,
        user_id: uuid.UUID | None = None,
        analysis_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        today: date | None = None,
    ) -> AiUsageEventPage:
        since = self._period_start(period, today or date.today())
        rows, total = self.repo.list_events(
            since=since,
            feature=feature,
            operation=operation,
            model=model,
            user_id=user_id,
            analysis_id=analysis_id,
            offset=offset,
            limit=limit,
        )
        return AiUsageEventPage(
            items=[
                AiUsageEventItem(
                    id=str(row.id),
                    occurred_at=row.occurred_at,
                    feature=row.feature,
                    operation=row.operation,
                    stage=row.stage,
                    stage_label=stage_label(row.stage),
                    model=row.model,
                    user_id=str(row.user_id) if row.user_id else None,
                    user_name=row.user_name,
                    analysis_id=str(row.analysis_id) if row.analysis_id else None,
                    attempt=row.attempt,
                    calls=row.calls,
                    input_tokens=row.input_tokens,
                    output_tokens=row.output_tokens,
                    cached_input_tokens=row.cached_input_tokens,
                    audio_seconds=_float_or_none(row.audio_seconds),
                    cost_usd=_float(row.cost_usd),
                    cost_status=row.cost_status,
                    tokens_estimated=row.tokens_estimated,
                    latency_ms=row.latency_ms,
                    error_type=row.error_type,
                )
                for row in rows
            ],
            total=total,
            offset=offset,
            limit=limit,
            models=list(self.repo.distinct_models()),
        )

    # --- Orçamento e configuração ---

    def get_budget_status(self, *, today: date | None = None) -> AiCostBudgetStatusResponse:
        today = today or date.today()
        month_start = today.replace(day=1)
        next_month = _next_month(month_start)

        spent = _dec(self.repo.spend_between(start=month_start, end=next_month))
        budget = self.config_repo.get_budget(month_start)
        settings = self.config_repo.get_settings()
        threshold = settings.warn_threshold_pct if settings else 80

        amount = _dec(budget.amount_usd) if budget else None
        if amount is None or amount == 0:
            return AiCostBudgetStatusResponse(
                month=month_start,
                amount_usd=_float_or_none(amount),
                spent_usd=_float(spent),
                pct=None,
                warn_threshold_pct=threshold,
                status="unset",
                projected_month_end_usd=_float_or_none(_project(spent, today)),
            )

        pct = spent / amount * 100
        if pct >= 100:
            status = "over"
        elif pct >= threshold:
            status = "warn"
        else:
            status = "ok"

        return AiCostBudgetStatusResponse(
            month=month_start,
            amount_usd=_float(amount),
            spent_usd=_float(spent),
            pct=_float(pct),
            warn_threshold_pct=threshold,
            status=status,
            projected_month_end_usd=_float_or_none(_project(spent, today)),
        )

    def get_config(self, *, today: date | None = None) -> AiCostConfigResponse:
        today = today or date.today()
        month_start = today.replace(day=1)
        settings = self.config_repo.get_settings()
        budget = self.config_repo.get_budget(month_start)
        return AiCostConfigResponse(
            warn_threshold_pct=settings.warn_threshold_pct if settings else 80,
            usd_to_brl_rate=_float_or_none(settings.usd_to_brl_rate if settings else None),
            usd_to_brl_rate_updated_at=settings.usd_to_brl_rate_updated_at if settings else None,
            current_month=month_start,
            current_month_budget_usd=_float_or_none(budget.amount_usd if budget else None),
        )

    def update_config(
        self,
        *,
        current_user: User,
        warn_threshold_pct: int,
        usd_to_brl_rate: float | None,
        budget_month: date | None,
        monthly_budget_usd: float | None,
        today: date | None = None,
    ) -> AiCostConfigResponse:
        today = today or date.today()
        existing = self.config_repo.get_settings()
        fields: dict = {"warn_threshold_pct": warn_threshold_pct}
        # Só registra a data da taxa quando ela de fato muda — assim a tela pode dizer
        # "cotação de dd/mm" com honestidade.
        previous_rate = existing.usd_to_brl_rate if existing else None
        new_rate = Decimal(str(usd_to_brl_rate)) if usd_to_brl_rate is not None else None
        fields["usd_to_brl_rate"] = new_rate
        if new_rate != previous_rate:
            fields["usd_to_brl_rate_updated_at"] = datetime.now(timezone.utc)
        self.config_repo.update_settings(updated_by_id=current_user.id, **fields)

        month_start = (budget_month or today).replace(day=1)
        if monthly_budget_usd is None:
            self.config_repo.delete_budget(month_start)
        else:
            self.config_repo.upsert_budget(
                month=month_start,
                amount_usd=Decimal(str(monthly_budget_usd)),
                updated_by_id=current_user.id,
            )
        return self.get_config(today=today)

    # --- Preços ---

    def list_prices(self, *, today: date | None = None) -> list[AiModelPriceResponse]:
        today = today or date.today()
        prices = self.price_repo.list_all()
        current_ids = set()
        for model, operation in {(p.model, p.operation) for p in prices}:
            current = self.price_repo.resolve(model=model, operation=operation, on_date=today)
            if current is not None:
                current_ids.add(current.id)
        return [_price_response(price, is_current=price.id in current_ids) for price in prices]

    def create_price(self, *, current_user: User, payload, today: date | None = None) -> AiModelPriceResponse:
        self._validate_price_payload(payload)
        if self._vigencia_exists(payload.model, payload.operation, payload.valid_from):
            raise DuplicatePriceVigenciaError()
        price = self.price_repo.create(
            AiModelPrice(
                model=payload.model.strip(),
                operation=AiUsageOperation(payload.operation),
                valid_from=payload.valid_from,
                input_usd_per_mtok=_dec_or_none(payload.input_usd_per_mtok),
                cached_input_usd_per_mtok=_dec_or_none(payload.cached_input_usd_per_mtok),
                output_usd_per_mtok=_dec_or_none(payload.output_usd_per_mtok),
                usd_per_minute=_dec_or_none(payload.usd_per_minute),
                notes=payload.notes,
                # Preço cadastrado pelo ADMIN é preço confirmado, nunca estimado.
                is_placeholder=False,
                updated_by_id=current_user.id,
            )
        )
        return _price_response(price, is_current=True)

    def update_price(
        self, price_id: uuid.UUID, *, current_user: User, payload, today: date | None = None
    ) -> AiModelPriceResponse:
        self._validate_price_payload(payload)
        if self.price_repo.get(price_id) is None:
            raise AiPriceNotFoundError()
        if self._vigencia_exists(
            payload.model, payload.operation, payload.valid_from, excluding=price_id
        ):
            raise DuplicatePriceVigenciaError()
        price = self.price_repo.update(
            price_id,
            model=payload.model.strip(),
            operation=AiUsageOperation(payload.operation),
            valid_from=payload.valid_from,
            input_usd_per_mtok=_dec_or_none(payload.input_usd_per_mtok),
            cached_input_usd_per_mtok=_dec_or_none(payload.cached_input_usd_per_mtok),
            output_usd_per_mtok=_dec_or_none(payload.output_usd_per_mtok),
            usd_per_minute=_dec_or_none(payload.usd_per_minute),
            notes=payload.notes,
            # Edição do ADMIN é a confirmação humana do preço.
            is_placeholder=False,
            updated_by_id=current_user.id,
        )
        current = self.price_repo.resolve(
            model=price.model, operation=price.operation, on_date=today or date.today()
        )
        return _price_response(price, is_current=current is not None and current.id == price.id)

    def recalculate_price(self, price_id: uuid.UUID) -> int:
        """Reaplica o preço aos eventos já gravados a partir da vigência.

        Ação explícita e manual de propósito: `cost_usd` é um snapshot congelado, e é isso
        que mantém meses fechados imutáveis quando a OpenAI muda de preço. Reescrever
        histórico é decisão humana, não efeito colateral de editar um campo.
        """
        price = self.price_repo.get(price_id)
        if price is None:
            raise AiPriceNotFoundError()

        candidates = self.usage_repo.list_for_repricing(
            model=price.model, operation=price.operation, since=price.valid_from
        )
        updates = []
        for event in candidates:
            applicable = self.price_repo.resolve(
                model=event.model, operation=event.operation, on_date=event.occurred_at.date()
            )
            snapshot = _snapshot(applicable) if applicable else None
            cost, status, applied_id = compute_cost(_as_pending(event), snapshot)
            if (cost, status, applied_id) != (event.cost_usd, event.cost_status, event.price_id):
                updates.append((event.id, cost, status, applied_id))
        return self.usage_repo.apply_repricing(updates)

    def _validate_price_payload(self, payload) -> None:
        operation = payload.operation
        if operation == "TRANSCRIPTION":
            if payload.usd_per_minute is None:
                raise InvalidPricePayloadError(
                    "Transcrição é faturada por minuto de áudio: informe o preço por minuto."
                )
        elif operation == "EMBEDDING":
            if payload.input_usd_per_mtok is None:
                raise InvalidPricePayloadError(
                    "Embedding é faturado por token de entrada: informe o preço de entrada."
                )
        elif payload.input_usd_per_mtok is None or payload.output_usd_per_mtok is None:
            raise InvalidPricePayloadError(
                "Chat precisa de preço de entrada e de saída, senão as chamadas ficam sem "
                "preço e o total aparece subestimado."
            )

    def _vigencia_exists(
        self, model: str, operation: str, valid_from: date, *, excluding: uuid.UUID | None = None
    ) -> bool:
        return any(
            price.model == model.strip()
            and price.operation.value == operation
            and price.valid_from == valid_from
            and price.id != excluding
            for price in self.price_repo.list_all()
        )

    def _period_start(self, period: Period, today: date) -> date:
        if period == "mtd":
            return today.replace(day=1)
        return today - timedelta(days=_PERIOD_DAYS[period])


def _price_response(price: AiModelPrice, *, is_current: bool) -> AiModelPriceResponse:
    return AiModelPriceResponse(
        id=str(price.id),
        model=price.model,
        operation=price.operation.value,
        valid_from=price.valid_from,
        input_usd_per_mtok=_float_or_none(price.input_usd_per_mtok),
        cached_input_usd_per_mtok=_float_or_none(price.cached_input_usd_per_mtok),
        output_usd_per_mtok=_float_or_none(price.output_usd_per_mtok),
        usd_per_minute=_float_or_none(price.usd_per_minute),
        is_placeholder=price.is_placeholder,
        notes=price.notes,
        is_current=is_current,
        updated_at=price.updated_at,
    )


def _snapshot(price: AiModelPrice) -> PriceSnapshot:
    return PriceSnapshot(
        price_id=price.id,
        input_usd_per_mtok=price.input_usd_per_mtok,
        cached_input_usd_per_mtok=price.cached_input_usd_per_mtok,
        output_usd_per_mtok=price.output_usd_per_mtok,
        usd_per_minute=price.usd_per_minute,
    )


def _as_pending(event) -> PendingUsage:
    """Adapta um evento já persistido de volta para o shape que compute_cost espera —
    reaproveita exatamente a mesma regra de cálculo do caminho de gravação."""
    return PendingUsage(
        feature=event.feature,
        operation=event.operation,
        model=event.model,
        occurred_at=event.occurred_at,
        input_tokens=event.input_tokens,
        output_tokens=event.output_tokens,
        cached_input_tokens=event.cached_input_tokens,
        reasoning_tokens=event.reasoning_tokens,
        audio_seconds=event.audio_seconds,
        error_type=event.error_type,
    )


def _project(spent: Decimal, today: date) -> Decimal | None:
    """Run-rate linear ingênuo: gasto médio diário até agora × dias do mês. Documentado
    como estimativa grosseira — não tenta modelar sazonalidade de dia útil."""
    if spent == 0:
        return None
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    return spent / max(1, today.day) * days_in_month


def _next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def _dec(value) -> Decimal:
    return Decimal(value) if value is not None else Decimal("0")


def _dec_or_none(value) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _float(value) -> float:
    return float(value if value is not None else 0)


def _float_or_none(value) -> float | None:
    return float(value) if value is not None else None


def _format_pct(part: Decimal, total: Decimal) -> str:
    if total == 0:
        return "0%"
    return f"{round(part / total * 100)}%"
