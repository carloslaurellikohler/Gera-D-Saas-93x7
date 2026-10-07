"""add manager_id to users

Revision ID: b2e4d8f61c53
Revises: a1f3c7d92b40
Create Date: 2026-10-07 09:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2e4d8f61c53'
down_revision: Union[str, Sequence[str], None] = 'a1f3c7d92b40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Só relevante quando role == COLABORADOR (validado em UserService, não via CHECK
    # de banco — mesmo estilo de CannotDeactivateSelfError). SET NULL: remover o
    # Gestor não deve apagar o colaborador, só órfã-lo até o ADMIN reatribuir.
    op.add_column('users', sa.Column('manager_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_users_manager_id_users', 'users', 'users', ['manager_id'], ['id'], ondelete='SET NULL'
    )
    op.create_index(op.f('ix_users_manager_id'), 'users', ['manager_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_manager_id'), table_name='users')
    op.drop_constraint('fk_users_manager_id_users', 'users', type_='foreignkey')
    op.drop_column('users', 'manager_id')
