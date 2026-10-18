"""Ponte entre a configuração operacional do Postgres e a Settings da engine.

Irmão de calibration_builder.py: tudo que constrói objeto de `gera_d_engine` vive em
engine_integration/, nunca em services ou rotas (ver docstring de adapter.py).

A engine lê o modelo de `os.getenv("OPENAI_MODEL")` em `Settings.load()`. Este módulo existe
para que o caminho do backend NÃO passe mais por ali: o modelo e a temperatura da análise vêm
da tabela runtime_settings, editáveis pelo ADMIN sem rebuild.
"""

from __future__ import annotations

from gera_d_engine.config import Settings as EngineSettings

from app.core.config import Settings as AppSettings
from app.models.runtime_settings import RuntimeSettings


def build_engine_settings(
    config: RuntimeSettings | None, app_settings: AppSettings
) -> EngineSettings:
    """`config` None (linha ausente) cai nos defaults do ambiente, mesmo fallback do resto.

    A `openai_api_key` **não** vem do banco: é segredo de ambiente, não configuração de
    admin. É a mesma chave usada pelo Whisper (EngineAdapter.load_transcript compartilha
    este objeto).
    """
    return EngineSettings(
        openai_api_key=app_settings.OPENAI_API_KEY,
        openai_model=config.analysis_model if config else app_settings.OPENAI_MODEL,
        openai_temperature=(
            float(config.analysis_temperature) if config else app_settings.OPENAI_TEMPERATURE
        ),
    )
