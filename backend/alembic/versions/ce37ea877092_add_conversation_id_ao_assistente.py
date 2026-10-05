"""add conversation_id ao assistente

Revision ID: ce37ea877092
Revises: 5b77efb26e8d
Create Date: 2026-10-05 23:08:13.771288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ce37ea877092'
down_revision: Union[str, Sequence[str], None] = '5b77efb26e8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable, sem backfill: mensagens/usuários de antes da feature "Nova Conversa"
    # ficam com conversation_id NULL, que continua significando "o histórico único de
    # sempre" (mesmo racional de analyses.methodology_version_id, Fase 7).
    op.add_column('chat_messages', sa.Column('conversation_id', sa.UUID(), nullable=True))
    op.drop_index(op.f('ix_chat_messages_user_created'), table_name='chat_messages')
    op.create_index(
        'ix_chat_messages_user_conversation_created',
        'chat_messages',
        ['user_id', 'conversation_id', 'created_at'],
        unique=False,
    )
    op.add_column('users', sa.Column('current_assistant_conversation_id', sa.UUID(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'current_assistant_conversation_id')
    op.drop_index('ix_chat_messages_user_conversation_created', table_name='chat_messages')
    op.create_index(
        op.f('ix_chat_messages_user_created'), 'chat_messages', ['user_id', 'created_at'], unique=False
    )
    op.drop_column('chat_messages', 'conversation_id')
