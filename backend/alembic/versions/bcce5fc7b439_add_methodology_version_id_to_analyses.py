"""add methodology_version_id to analyses

Revision ID: bcce5fc7b439
Revises: f49241d88702
Create Date: 2026-10-03 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bcce5fc7b439'
down_revision: Union[str, Sequence[str], None] = 'f49241d88702'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable: análises criadas antes da Fase 7 não têm uma versão de metodologia
    # relacional associada (só a string calibration_version dentro do JSONB
    # analysis_result) — ficam com NULL, sem backfill artificial (mesmo racional de
    # analyses.user_id desde a Fase 3).
    op.add_column('analyses', sa.Column('methodology_version_id', sa.UUID(), nullable=True))
    op.create_index(
        op.f('ix_analyses_methodology_version_id'), 'analyses', ['methodology_version_id'], unique=False
    )
    # RESTRICT (não SET NULL/CASCADE): nunca permitir apagar uma versão de
    # metodologia referenciada por uma análise existente, mesmo já ARCHIVED — o
    # histórico precisa continuar reconstruível (ver MethodologyService.delete_draft,
    # que só apaga rascunhos nunca publicados).
    op.create_foreign_key(
        'fk_analyses_methodology_version_id_methodologies',
        'analyses', 'methodologies',
        ['methodology_version_id'], ['id'],
        ondelete='RESTRICT',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'fk_analyses_methodology_version_id_methodologies', 'analyses', type_='foreignkey'
    )
    op.drop_index(op.f('ix_analyses_methodology_version_id'), table_name='analyses')
    op.drop_column('analyses', 'methodology_version_id')
