"""create runtime settings table

Revision ID: 93e1ffef482c
Revises: f3b8d6a0c219
Create Date: 2026-10-18 10:00:00.000000

Tabela de linha única para a configuração operacional editável pelo ADMIN em /configuracoes:
os dois limites diários de uso e o modelo+temperatura da análise e do assistente.

Só DDL aqui. O seed da linha vem na revision seguinte (8fedcfaf1406), separado porque é ele
que carrega a decisão de onde vêm os valores iniciais — e porque um downgrade de dados não
deve arrastar o schema.

As temperaturas são Numeric(3, 2) e não Float: o valor volta para um <input type="number"> na
tela, e ruído de ponto flutuante numa tela de administração é bug de percepção.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '93e1ffef482c'
down_revision: Union[str, Sequence[str], None] = 'f3b8d6a0c219'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'runtime_settings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column(
            'daily_analysis_limit_per_owner',
            sa.Integer(),
            server_default=sa.text('4'),
            nullable=False,
        ),
        sa.Column(
            'assistant_daily_message_limit',
            sa.Integer(),
            server_default=sa.text('30'),
            nullable=False,
        ),
        sa.Column('analysis_model', sa.String(length=120), nullable=False),
        sa.Column('analysis_temperature', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('assistant_model', sa.String(length=120), nullable=False),
        sa.Column('assistant_temperature', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_runtime_settings_updated_by_id'), 'runtime_settings', ['updated_by_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_runtime_settings_updated_by_id'), table_name='runtime_settings')
    op.drop_table('runtime_settings')
