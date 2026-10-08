"""Configuração financeira do FinAI: orçamento por mês e ajustes globais.

Separado de AiPriceRepository porque são ciclos de vida distintos — preço é histórico de
mercado versionado por vigência; orçamento é meta interna por mês.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_cost import AI_COST_SETTINGS_ID, AiCostBudget, AiCostSettings


class AiCostConfigRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Ajustes globais (linha única, de id fixo semeado pela migration) ---

    def get_settings(self) -> AiCostSettings | None:
        """None só se alguém removeu a linha semeada à mão — o service trata como default."""
        return self.db.get(AiCostSettings, AI_COST_SETTINGS_ID)

    def update_settings(self, *, updated_by_id: uuid.UUID | None, **fields) -> AiCostSettings:
        settings = self.get_settings()
        if settings is None:
            # Reconstrói a linha com o ID fixo em vez de gerar um novo: manter o singleton
            # previsível é o que evita get_or_create com corrida.
            settings = AiCostSettings(id=AI_COST_SETTINGS_ID)
            self.db.add(settings)
        for key, value in fields.items():
            setattr(settings, key, value)
        settings.updated_by_id = updated_by_id
        self.db.commit()
        self.db.refresh(settings)
        return settings

    # --- Orçamento mensal ---

    def get_budget(self, month: date) -> AiCostBudget | None:
        stmt = select(AiCostBudget).where(AiCostBudget.month == month)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert_budget(
        self, *, month: date, amount_usd: Decimal, updated_by_id: uuid.UUID | None
    ) -> AiCostBudget:
        budget = self.get_budget(month)
        if budget is None:
            budget = AiCostBudget(month=month, amount_usd=amount_usd, updated_by_id=updated_by_id)
            self.db.add(budget)
        else:
            budget.amount_usd = amount_usd
            budget.updated_by_id = updated_by_id
        self.db.commit()
        self.db.refresh(budget)
        return budget

    def delete_budget(self, month: date) -> None:
        budget = self.get_budget(month)
        if budget is not None:
            self.db.delete(budget)
            self.db.commit()
