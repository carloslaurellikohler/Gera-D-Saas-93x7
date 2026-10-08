"""Acesso à tabela de preços de modelo (FinAI). A resolução por vigência é o coração daqui:
o preço de um evento é a linha com maior `valid_from` menor ou igual à data do evento."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_cost import AiModelPrice, AiUsageOperation


class AiPriceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve(
        self, *, model: str, operation: AiUsageOperation, on_date: date
    ) -> AiModelPrice | None:
        """Vigência aplicável a um evento. None quando o modelo nunca teve preço cadastrado
        (ou só passou a ter depois da data) — o evento então fica com cost_status=NO_PRICE."""
        stmt = (
            select(AiModelPrice)
            .where(
                AiModelPrice.model == model,
                AiModelPrice.operation == operation,
                AiModelPrice.valid_from <= on_date,
            )
            .order_by(AiModelPrice.valid_from.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get(self, price_id: uuid.UUID) -> AiModelPrice | None:
        return self.db.get(AiModelPrice, price_id)

    def list_all(self) -> list[AiModelPrice]:
        stmt = select(AiModelPrice).order_by(
            AiModelPrice.model, AiModelPrice.operation, AiModelPrice.valid_from.desc()
        )
        return list(self.db.execute(stmt).scalars().all())

    def has_placeholder_in_effect(self, *, on_date: date) -> bool:
        """Se alguma vigência ativa hoje é um preço marcado como estimado. A tela avisa
        enquanto isso for verdade — número estimado não pode passar por medido."""
        for price in self.list_all():
            if price.valid_from <= on_date and price.is_placeholder:
                current = self.resolve(
                    model=price.model, operation=price.operation, on_date=on_date
                )
                if current is not None and current.id == price.id:
                    return True
        return False

    def create(self, price: AiModelPrice) -> AiModelPrice:
        self.db.add(price)
        self.db.commit()
        self.db.refresh(price)
        return price

    def update(self, price_id: uuid.UUID, **fields: Any) -> AiModelPrice:
        price = self.get(price_id)
        if price is None:
            raise ValueError(f"AiModelPrice {price_id} not found")
        for key, value in fields.items():
            setattr(price, key, value)
        self.db.commit()
        self.db.refresh(price)
        return price
