"""seed runtime settings

Revision ID: 8fedcfaf1406
Revises: 93e1ffef482c
Create Date: 2026-10-18 10:05:00.000000

Semeia a linha única de runtime_settings. **A partir desta revision, o Postgres é a fonte de
verdade** dos seis valores; as variáveis de ambiente correspondentes passam a ser só bootstrap
(ver app/models/runtime_settings.py e o bloco de comentário em app/core/config.py).

Os valores vêm do AMBIENTE, não de literais, e isso é a decisão central desta migration: um
deploy que hoje roda OPENAI_MODEL=gpt-6-sol tem que continuar nele depois do upgrade. Literais
aqui trocariam o modelo de produção em silêncio, no meio de um `alembic upgrade head`.

O container `backend` recebe essas vars (docker-compose.yml) e roda `alembic upgrade head` no
CMD, então o seed enxerga o ambiente real do deploy.
"""
import os
import uuid
from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8fedcfaf1406'
down_revision: Union[str, Sequence[str], None] = '93e1ffef482c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ID fixo para que o downgrade saiba exatamente o que remover — mesma técnica de
# _AI_COST_SETTINGS_ID (f3b8d6a0c219) e _METHODOLOGY_ID (5b77efb26e8d).
# Precisa casar com app/models/runtime_settings.py::RUNTIME_SETTINGS_ID.
_RUNTIME_SETTINGS_ID = uuid.UUID("9978481d-2674-4baa-baed-3b4d5e495f07")

# Estes defaults precisam ser IDÊNTICOS aos de app/core/config.py (que é o fallback usado
# quando esta linha não existe). É o ponto de divergência futura mais provável desta feature:
# mudar um lado sem o outro faz um banco novo nascer diferente de um banco sem seed.
_DEFAULTS = {
    "DAILY_ANALYSIS_LIMIT_PER_OWNER": "4",
    "ASSISTANT_DAILY_MESSAGE_LIMIT": "30",
    "OPENAI_MODEL": "gpt-6-luna",
    "OPENAI_TEMPERATURE": "0.2",
    "ASSISTANT_CHAT_MODEL": "gpt-6-luna",
    "ASSISTANT_CHAT_TEMPERATURE": "0.3",
}

runtime_settings = sa.table(
    "runtime_settings",
    sa.column("id", sa.UUID()),
    sa.column("daily_analysis_limit_per_owner", sa.Integer()),
    sa.column("assistant_daily_message_limit", sa.Integer()),
    sa.column("analysis_model", sa.String()),
    sa.column("analysis_temperature", sa.Numeric()),
    sa.column("assistant_model", sa.String()),
    sa.column("assistant_temperature", sa.Numeric()),
)


def _env(key: str) -> str:
    """Valor do ambiente com o default de config.py. Vazio conta como ausente: no compose uma
    var não preenchida chega como string vazia, e int("") explodiria no meio do upgrade."""
    return os.getenv(key) or _DEFAULTS[key]


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(
        runtime_settings,
        [
            {
                "id": _RUNTIME_SETTINGS_ID,
                "daily_analysis_limit_per_owner": int(_env("DAILY_ANALYSIS_LIMIT_PER_OWNER")),
                "assistant_daily_message_limit": int(_env("ASSISTANT_DAILY_MESSAGE_LIMIT")),
                "analysis_model": _env("OPENAI_MODEL"),
                "analysis_temperature": Decimal(_env("OPENAI_TEMPERATURE")),
                "assistant_model": _env("ASSISTANT_CHAT_MODEL"),
                "assistant_temperature": Decimal(_env("ASSISTANT_CHAT_TEMPERATURE")),
            }
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Sem a linha, o sistema volta a usar os defaults de app/core/config.py — é o fallback
    # por design, não um estado de erro.
    op.execute(sa.delete(runtime_settings).where(runtime_settings.c.id == _RUNTIME_SETTINGS_ID))
