"""Acesso à linha única de configuração operacional (tabela runtime_settings).

Mesmo formato de AiCostConfigRepository: singleton de id fixo, sem get_or_create. Separado
dele porque são domínios distintos — lá é configuração financeira do FinAI, aqui são limites
de uso e escolha de modelo.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.runtime_settings import RUNTIME_SETTINGS_ID, RuntimeSettings


class RuntimeSettingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self) -> RuntimeSettings | None:
        """None se a migration de seed não rodou ou alguém removeu a linha à mão — quem chama
        trata como default do ambiente (ver build_effective_settings)."""
        return self.db.get(RuntimeSettings, RUNTIME_SETTINGS_ID)

    def update(self, *, updated_by_id: uuid.UUID | None, **fields) -> RuntimeSettings:
        config = self.get()
        if config is None:
            # Reconstrói a linha com o ID fixo em vez de gerar um novo: manter o singleton
            # previsível é o que evita get_or_create com corrida.
            config = RuntimeSettings(id=RUNTIME_SETTINGS_ID)
            self.db.add(config)
        for key, value in fields.items():
            setattr(config, key, value)
        config.updated_by_id = updated_by_id
        self.db.commit()
        self.db.refresh(config)
        return config
