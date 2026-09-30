"""add user_id to analyses

Revision ID: 9c2a1f6e5b7d
Revises: 68011652cc23
Create Date: 2026-09-30 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9c2a1f6e5b7d'
down_revision: Union[str, Sequence[str], None] = '68011652cc23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable: análises existentes não têm dono real (criadas antes da Fase 3, via
    # DEFAULT_CS_ID) — ficam órfãs (user_id NULL) em vez de receber uma proveniência
    # fictícia. A partir desta fase, toda análise criada via rota autenticada sempre
    # recebe um user_id real (ver AnalysisService.create_and_store).
    op.add_column('analyses', sa.Column('user_id', sa.UUID(), nullable=True))
    # SET NULL (não CASCADE): apagar um usuário não deve apagar o histórico de
    # análises — a análise fica órfã, preservada para auditoria/ADMIN.
    op.create_foreign_key(
        'fk_analyses_user_id_users', 'analyses', 'users', ['user_id'], ['id'], ondelete='SET NULL'
    )
    op.create_index(op.f('ix_analyses_user_id'), 'analyses', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_analyses_user_id'), table_name='analyses')
    op.drop_constraint('fk_analyses_user_id_users', 'analyses', type_='foreignkey')
    op.drop_column('analyses', 'user_id')
