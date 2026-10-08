"""Gravação dos eventos de consumo de IA (FinAI). Só escrita — as agregações da tela ficam
em ai_cost_repository.py, que é só leitura (mesma separação de DashboardRepository).

A gravação é sempre em lote, uma vez por job, e não uma por chamada à OpenAI: o caminho
crítico (pipeline de análise, resposta do assistente) não deve pagar I/O por chamada.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.ai_cost import AiUsageCostStatus, AiUsageEvent


class AiUsageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bulk_create(self, events: Sequence[AiUsageEvent]) -> int:
        if not events:
            return 0
        self.db.add_all(list(events))
        self.db.commit()
        return len(events)

    def list_for_repricing(self, *, model: str, operation, since: date) -> list[AiUsageEvent]:
        """Eventos candidatos a recálculo quando o ADMIN corrige um preço: os que já usam
        alguma vigência desse (modelo, operação) e os que ficaram sem preço."""
        stmt = select(AiUsageEvent).where(
            AiUsageEvent.model == model,
            AiUsageEvent.operation == operation,
            AiUsageEvent.occurred_at >= since,
            AiUsageEvent.cost_status.in_(
                [AiUsageCostStatus.PRICED, AiUsageCostStatus.NO_PRICE]
            ),
        )
        return list(self.db.execute(stmt).scalars().all())

    def apply_repricing(self, updates: Sequence[tuple[uuid.UUID, object, object, object]]) -> int:
        """Aplica (id, cost_usd, cost_status, price_id) em lote, numa transação só."""
        if not updates:
            return 0
        for event_id, cost_usd, cost_status, price_id in updates:
            self.db.execute(
                update(AiUsageEvent)
                .where(AiUsageEvent.id == event_id)
                .values(cost_usd=cost_usd, cost_status=cost_status, price_id=price_id)
            )
        self.db.commit()
        return len(updates)
