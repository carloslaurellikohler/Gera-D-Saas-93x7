from __future__ import annotations

from decimal import Decimal

from app.core.config import Settings
from app.engine_integration.engine_settings_builder import build_engine_settings
from app.models.runtime_settings import RUNTIME_SETTINGS_ID, RuntimeSettings

_APP_SETTINGS = Settings(
    OPENAI_API_KEY="sk-do-ambiente",
    OPENAI_MODEL="gpt-6-luna",
    OPENAI_TEMPERATURE=0.2,
)


def _config() -> RuntimeSettings:
    return RuntimeSettings(
        id=RUNTIME_SETTINGS_ID,
        daily_analysis_limit_per_owner=4,
        assistant_daily_message_limit=30,
        analysis_model="gpt-6-sol",
        analysis_temperature=Decimal("0.90"),
        assistant_model="gpt-4.1",
        assistant_temperature=Decimal("0.30"),
    )


def test_modelo_e_temperatura_vem_do_banco():
    engine_settings = build_engine_settings(_config(), _APP_SETTINGS)

    assert engine_settings.openai_model == "gpt-6-sol"
    assert engine_settings.openai_temperature == 0.9


def test_sem_linha_cai_nos_defaults_do_ambiente():
    engine_settings = build_engine_settings(None, _APP_SETTINGS)

    assert engine_settings.openai_model == "gpt-6-luna"
    assert engine_settings.openai_temperature == 0.2


def test_api_key_nunca_vem_do_banco():
    """A chave é segredo de ambiente, não configuração de admin — e é a mesma usada pelo
    Whisper, já que EngineAdapter compartilha este objeto com load_transcript."""
    engine_settings = build_engine_settings(_config(), _APP_SETTINGS)

    assert engine_settings.openai_api_key == "sk-do-ambiente"


def test_temperatura_sai_como_float():
    """A engine passa isso direto para ChatOpenAI(temperature=...), que não aceita Decimal."""
    engine_settings = build_engine_settings(_config(), _APP_SETTINGS)

    assert isinstance(engine_settings.openai_temperature, float)
