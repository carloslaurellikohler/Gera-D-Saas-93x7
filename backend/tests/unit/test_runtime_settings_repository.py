from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.security import hash_password
from app.models.runtime_settings import RUNTIME_SETTINGS_ID
from app.models.user import User, UserRole, UserStatus
from app.repositories.runtime_settings_repository import RuntimeSettingsRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def repo(db_session) -> RuntimeSettingsRepository:
    return RuntimeSettingsRepository(db_session)


def _admin(db_session, email: str = "admin-rs@example.com") -> User:
    return UserRepository(db_session).create(
        User(
            name="Admin Config",
            email=email,
            password_hash=hash_password("x"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
    )


_PAYLOAD = dict(
    daily_analysis_limit_per_owner=7,
    assistant_daily_message_limit=50,
    analysis_model="gpt-6-sol",
    analysis_temperature=Decimal("0.40"),
    assistant_model="gpt-4.1",
    assistant_temperature=Decimal("0.70"),
)


def test_get_returns_none_quando_a_linha_nao_foi_semeada(repo):
    """As migrations não rodam nos testes (create_all), então o banco de teste nasce sem a
    linha semeada — exatamente o cenário de fallback que o service precisa cobrir."""
    assert repo.get() is None


def test_update_cria_a_linha_com_o_id_fixo(repo, db_session):
    admin = _admin(db_session)

    config = repo.update(updated_by_id=admin.id, **_PAYLOAD)

    assert config.id == RUNTIME_SETTINGS_ID
    assert config.analysis_model == "gpt-6-sol"
    assert config.daily_analysis_limit_per_owner == 7
    assert repo.get() is not None


def test_update_grava_o_editor_e_o_timestamp(repo, db_session):
    admin = _admin(db_session)

    config = repo.update(updated_by_id=admin.id, **_PAYLOAD)

    assert config.updated_by_id == admin.id
    # updated_at usa onupdate, não server_default: no INSERT ele fica nulo e só passa a ter
    # valor no primeiro UPDATE. A tela trata None como "nunca editado".
    assert config.updated_at is None


def test_segundo_update_sobrescreve_o_editor(repo, db_session):
    primeiro = _admin(db_session, email="primeiro@example.com")
    segundo = _admin(db_session, email="segundo@example.com")

    repo.update(updated_by_id=primeiro.id, **_PAYLOAD)
    config = repo.update(updated_by_id=segundo.id, **{**_PAYLOAD, "analysis_model": "gpt-6-lua"})

    # Auditoria é só do último editor, por decisão de escopo — não há histórico.
    assert config.updated_by_id == segundo.id
    assert config.analysis_model == "gpt-6-lua"
    assert config.updated_at is not None
