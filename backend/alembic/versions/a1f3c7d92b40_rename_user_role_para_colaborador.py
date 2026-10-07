"""rename user role USER para COLABORADOR, adiciona GESTOR

Revision ID: a1f3c7d92b40
Revises: ce37ea877092
Create Date: 2026-10-07 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1f3c7d92b40'
down_revision: Union[str, Sequence[str], None] = 'ce37ea877092'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # role é armazenado como VARCHAR(32) puro (Enum(native_enum=False), sem CHECK no
    # banco) — renomear/adicionar valor de enum é só UPDATE de dados, nunca ALTER TYPE.
    op.execute("UPDATE users SET role = 'COLABORADOR' WHERE role = 'USER'")


def downgrade() -> None:
    """Downgrade schema."""
    # Lossy para quem foi promovido a GESTOR neste intervalo: não há como saber quem
    # era USER antes — só os que ainda são COLABORADOR voltam a ser USER.
    op.execute("UPDATE users SET role = 'USER' WHERE role = 'COLABORADOR'")
