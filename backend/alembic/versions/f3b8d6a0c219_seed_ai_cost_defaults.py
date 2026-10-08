"""seed ai cost defaults

Revision ID: f3b8d6a0c219
Revises: e7a2c9f4b1d8
Create Date: 2026-10-08 12:20:00.000000

Semeia a linha única de ai_cost_settings e os preços que são fato público conhecido.

Os modelos de CHAT (OPENAI_MODEL / ASSISTANT_CHAT_MODEL) ficam DELIBERADAMENTE sem seed:
seus nomes vêm do ambiente e variam por deploy, e não existe preço público que eu possa
afirmar. Chutar número numa tela financeira é pior que declarar a ausência — então, até o
ADMIN cadastrar o preço, os eventos de chat ficam com cost_status=NO_PRICE e custo 0, e a
tela avisa em voz alta quantas chamadas estão sem preço e que o total está subestimado.

"""
from typing import Sequence, Union
import uuid
from datetime import date, datetime, timezone

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3b8d6a0c219'
down_revision: Union[str, Sequence[str], None] = 'e7a2c9f4b1d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# IDs fixos (gerados uma vez) para que o downgrade saiba exatamente o que remover — mesma
# técnica de _METHODOLOGY_ID na migration 5b77efb26e8d.
# AI_COST_SETTINGS_ID precisa casar com app/models/ai_cost.py::AI_COST_SETTINGS_ID.
_AI_COST_SETTINGS_ID = uuid.UUID("9f2c1b7e-4d3a-4e58-9c81-0a6b5d2f7c40")
_WHISPER_PRICE_ID = uuid.UUID("2c7d4e91-8b05-4f36-ae12-6d9c3b8f0a41")
_EMBEDDING_PRICE_ID = uuid.UUID("5e1a8c34-9d72-4b60-8f45-27c1e6a9b038")

# valid_from bem no passado para cobrir qualquer evento gravado a partir de agora.
_VALID_FROM = date(2024, 1, 1)
_PRICE_NOTE = (
    "Seed inicial — referencia de 2026-10. Confira na pagina de precos da OpenAI; se "
    "divergir, cadastre uma vigencia nova pela tela em vez de editar esta linha."
)

ai_model_prices = sa.table(
    "ai_model_prices",
    sa.column("id", sa.UUID()),
    sa.column("model", sa.String()),
    sa.column("operation", sa.String()),
    sa.column("valid_from", sa.Date()),
    sa.column("input_usd_per_mtok", sa.Numeric()),
    sa.column("cached_input_usd_per_mtok", sa.Numeric()),
    sa.column("output_usd_per_mtok", sa.Numeric()),
    sa.column("usd_per_minute", sa.Numeric()),
    sa.column("is_placeholder", sa.Boolean()),
    sa.column("notes", sa.String()),
    sa.column("created_at", sa.DateTime(timezone=True)),
)

ai_cost_settings = sa.table(
    "ai_cost_settings",
    sa.column("id", sa.UUID()),
    sa.column("warn_threshold_pct", sa.Integer()),
    sa.column("usd_to_brl_rate", sa.Numeric()),
)


def upgrade() -> None:
    """Upgrade schema."""
    now = datetime.now(timezone.utc)

    op.bulk_insert(
        ai_model_prices,
        [
            {
                "id": _WHISPER_PRICE_ID,
                "model": "whisper-1",
                "operation": "TRANSCRIPTION",
                "valid_from": _VALID_FROM,
                "input_usd_per_mtok": None,
                "cached_input_usd_per_mtok": None,
                "output_usd_per_mtok": None,
                "usd_per_minute": 0.006,
                "is_placeholder": False,
                "notes": _PRICE_NOTE,
                "created_at": now,
            },
            {
                "id": _EMBEDDING_PRICE_ID,
                "model": "text-embedding-3-small",
                "operation": "EMBEDDING",
                "valid_from": _VALID_FROM,
                "input_usd_per_mtok": 0.020,
                "cached_input_usd_per_mtok": None,
                "output_usd_per_mtok": None,
                "usd_per_minute": None,
                "is_placeholder": False,
                "notes": _PRICE_NOTE,
                "created_at": now,
            },
        ],
    )

    # Linha única de configuração financeira. Orçamento começa inexistente (nenhuma linha
    # em ai_cost_budgets): a tela mostra "meta não definida" com CTA, nunca uma meta
    # inventada.
    op.bulk_insert(
        ai_cost_settings,
        [{"id": _AI_COST_SETTINGS_ID, "warn_threshold_pct": 80, "usd_to_brl_rate": None}],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.delete(ai_cost_settings).where(ai_cost_settings.c.id == _AI_COST_SETTINGS_ID))
    op.execute(
        sa.delete(ai_model_prices).where(
            ai_model_prices.c.id.in_([_WHISPER_PRICE_ID, _EMBEDDING_PRICE_ID])
        )
    )
