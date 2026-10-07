"""split analysis owner_id (dono/avaliado) e created_by_id (quem fez upload)

Revision ID: c3f5e9a72d64
Revises: b2e4d8f61c53
Create Date: 2026-10-07 09:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3f5e9a72d64'
down_revision: Union[str, Sequence[str], None] = 'b2e4d8f61c53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # user_id virava "dono" (colaborador avaliado, cujas métricas contam) e passa a
    # se chamar owner_id. created_by_id (quem de fato fez o upload — colaborador ou o
    # Gestor da equipe) é novo; antes desta fase, upload era sempre feito pelo próprio
    # dono, então o backfill com owner_id é fato histórico, não proveniência fictícia.
    op.alter_column('analyses', 'user_id', new_column_name='owner_id')
    op.execute('ALTER INDEX ix_analyses_user_id RENAME TO ix_analyses_owner_id')
    op.execute(
        'ALTER TABLE analyses RENAME CONSTRAINT fk_analyses_user_id_users TO fk_analyses_owner_id_users'
    )

    op.add_column('analyses', sa.Column('created_by_id', sa.UUID(), nullable=True))
    op.execute('UPDATE analyses SET created_by_id = owner_id')
    op.create_foreign_key(
        'fk_analyses_created_by_id_users', 'analyses', 'users', ['created_by_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index(op.f('ix_analyses_created_by_id'), 'analyses', ['created_by_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_analyses_created_by_id'), table_name='analyses')
    op.drop_constraint('fk_analyses_created_by_id_users', 'analyses', type_='foreignkey')
    op.drop_column('analyses', 'created_by_id')

    op.execute(
        'ALTER TABLE analyses RENAME CONSTRAINT fk_analyses_owner_id_users TO fk_analyses_user_id_users'
    )
    op.execute('ALTER INDEX ix_analyses_owner_id RENAME TO ix_analyses_user_id')
    op.alter_column('analyses', 'owner_id', new_column_name='user_id')
