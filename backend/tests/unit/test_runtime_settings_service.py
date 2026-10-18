from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.core.security import hash_password
from app.models.ai_cost import AiModelPrice, AiUsageOperation
from app.models.runtime_settings import RUNTIME_SETTINGS_ID, RuntimeSettings
from app.models.user import User, UserRole, UserStatus
from app.repositories.ai_price_repository import AiPriceRepository
from app.repositories.runtime_settings_repository import RuntimeSettingsRepository
from app.repositories.user_repository import UserRepository
from app.schemas.runtime_settings import RuntimeSettingsIn
from app.services.runtime_settings_service import (
    RuntimeSettingsService,
    build_effective_settings,
)

_BASE = Settings(
    DAILY_ANALYSIS_LIMIT_PER_OWNER=4,
    ASSISTANT_DAILY_MESSAGE_LIMIT=30,
    OPENAI_MODEL="gpt-6-luna",
    OPENAI_TEMPERATURE=0.2,
    ASSISTANT_CHAT_MODEL="gpt-6-luna",
    ASSISTANT_CHAT_TEMPERATURE=0.3,
)


def _config() -> RuntimeSettings:
    return RuntimeSettings(
        id=RUNTIME_SETTINGS_ID,
        daily_analysis_limit_per_owner=1,
        assistant_daily_message_limit=9,
        analysis_model="gpt-6-sol",
        analysis_temperature=Decimal("0.70"),
        assistant_model="gpt-4.1",
        assistant_temperature=Decimal("1.10"),
    )


# --- build_effective_settings (função pura) ---


def test_sem_linha_no_banco_devolve_o_base_intacto():
    assert build_effective_settings(_BASE, None) is _BASE


def test_banco_vence_o_ambiente_nos_seis_campos():
    eff = build_effective_settings(_BASE, _config())

    assert eff.DAILY_ANALYSIS_LIMIT_PER_OWNER == 1
    assert eff.ASSISTANT_DAILY_MESSAGE_LIMIT == 9
    assert eff.OPENAI_MODEL == "gpt-6-sol"
    assert eff.OPENAI_TEMPERATURE == 0.7
    assert eff.ASSISTANT_CHAT_MODEL == "gpt-4.1"
    assert eff.ASSISTANT_CHAT_TEMPERATURE == 1.1


def test_temperatura_sai_como_float_e_nao_decimal():
    """Regressão: model_copy(update=...) não valida nem coage tipos. Sem o cast explícito, o
    Decimal do Numeric vazaria para ChatOpenAI(temperature=...) e para a borda HTTP."""
    eff = build_effective_settings(_BASE, _config())

    assert isinstance(eff.OPENAI_TEMPERATURE, float)
    assert isinstance(eff.ASSISTANT_CHAT_TEMPERATURE, float)


def test_nao_muta_o_settings_de_entrada():
    build_effective_settings(_BASE, _config())

    assert _BASE.OPENAI_MODEL == "gpt-6-luna"
    assert _BASE.DAILY_ANALYSIS_LIMIT_PER_OWNER == 4


# --- RuntimeSettingsService ---


@pytest.fixture()
def service(db_session) -> RuntimeSettingsService:
    return RuntimeSettingsService(
        repo=RuntimeSettingsRepository(db_session),
        user_repo=UserRepository(db_session),
        price_repo=AiPriceRepository(db_session),
        settings=_BASE,
    )


@pytest.fixture()
def admin(db_session) -> User:
    return UserRepository(db_session).create(
        User(
            name="Admin Config",
            email="admin-svc@example.com",
            password_hash=hash_password("x"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
    )


def _payload(**overrides) -> RuntimeSettingsIn:
    defaults = dict(
        daily_analysis_limit_per_owner=2,
        assistant_daily_message_limit=5,
        analysis_model="gpt-6-sol",
        analysis_temperature=0.5,
        assistant_model="gpt-4.1",
        assistant_temperature=0.9,
    )
    defaults.update(overrides)
    return RuntimeSettingsIn(**defaults)


def test_get_config_sem_linha_devolve_os_defaults_do_ambiente(service):
    """Sem a linha a tela não pode dar 404: o que está valendo de fato é o fallback, e é isso
    que o ADMIN precisa ver."""
    response = service.get_config()

    assert response.daily_analysis_limit_per_owner == 4
    assert response.analysis_model == "gpt-6-luna"
    assert response.updated_at is None
    assert response.updated_by_name is None


def test_update_config_persiste_e_reflete_no_get(service, admin):
    service.update_config(current_user=admin, payload=_payload())

    response = service.get_config()
    assert response.daily_analysis_limit_per_owner == 2
    assert response.assistant_daily_message_limit == 5
    assert response.analysis_model == "gpt-6-sol"
    assert response.assistant_temperature == 0.9


def test_update_config_resolve_o_nome_do_editor(service, admin):
    response = service.update_config(current_user=admin, payload=_payload())

    assert response.updated_by_name == "Admin Config"


def test_update_config_remove_espacos_do_nome_do_modelo(service, admin):
    response = service.update_config(current_user=admin, payload=_payload(analysis_model="  gpt-6-sol  "))

    assert response.analysis_model == "gpt-6-sol"


def test_editor_removido_devolve_nome_nulo(service, admin, db_session):
    """FK users.id é ondelete=SET NULL: apagar o usuário não apaga a configuração."""
    service.update_config(current_user=admin, payload=_payload())
    db_session.delete(admin)
    db_session.commit()

    assert service.get_config().updated_by_name is None


def test_flags_de_preco_falsas_quando_o_modelo_nao_tem_vigencia(service):
    response = service.get_config()

    assert response.analysis_model_priced is False
    assert response.assistant_model_priced is False


def test_flags_de_preco_verdadeiras_com_vigencia_cadastrada(service, admin, db_session):
    db_session.add(
        AiModelPrice(
            model="gpt-6-sol",
            operation=AiUsageOperation.CHAT,
            valid_from=date(2024, 1, 1),
            input_usd_per_mtok=Decimal("1.0"),
            output_usd_per_mtok=Decimal("2.0"),
        )
    )
    db_session.commit()

    service.update_config(current_user=admin, payload=_payload(analysis_model="gpt-6-sol"))
    response = service.get_config()

    assert response.analysis_model_priced is True
    # O modelo do assistente continua sem preço — as duas flags são independentes.
    assert response.assistant_model_priced is False


def test_response_carrega_os_prefixos_de_reasoning(service):
    """A tela desabilita o campo de temperatura com esta lista, em vez de manter uma cópia."""
    assert "gpt-6" in service.get_config().reasoning_model_prefixes
