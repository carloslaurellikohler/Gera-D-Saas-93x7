"""create assistant tables

Revision ID: 080c74a6ab60
Revises: 5c4395d2de1c
Create Date: 2026-10-02 20:51:34.173683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '080c74a6ab60'
down_revision: Union[str, Sequence[str], None] = '5c4395d2de1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'methodology_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column('source_file', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chunk_index'),
    )

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', name='chat_message_role', native_enum=False, length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(
        'ix_chat_messages_user_created', 'chat_messages', ['user_id', 'created_at'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_chat_messages_user_created', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_table('methodology_chunks')
