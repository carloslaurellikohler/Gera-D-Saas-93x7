"""create content and learning_path tables

Revision ID: d4f8a3c1e6b2
Revises: 9c2a1f6e5b7d
Create Date: 2026-10-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4f8a3c1e6b2'
down_revision: Union[str, Sequence[str], None] = '9c2a1f6e5b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CRITERION_KEYS = (
    'POSICIONAMENTO', 'CONEXAO', 'SONDAGEM', 'DIRECIONAMENTO',
    'ENCAMINHAMENTO', 'EFICIENCIA_CONDUCAO',
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'content',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column(
            'criterion_key',
            sa.Enum(*_CRITERION_KEYS, name='content_criterion_key', native_enum=False, length=32),
            nullable=True,
        ),
        sa.Column(
            'kind',
            sa.Enum('FILE', 'LINK', name='content_kind', native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('external_url', sa.String(length=1000), nullable=True),
        sa.Column('uploaded_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_content_uploaded_by_id'), 'content', ['uploaded_by_id'], unique=False)

    op.create_table(
        'learning_paths',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column(
            'criterion_key',
            sa.Enum(*_CRITERION_KEYS, name='learning_path_criterion_key', native_enum=False, length=32),
            nullable=True,
        ),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index(
        op.f('ix_learning_paths_created_by_id'), 'learning_paths', ['created_by_id'], unique=False
    )

    op.create_table(
        'learning_path_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('learning_path_id', sa.UUID(), nullable=False),
        sa.Column('content_id', sa.UUID(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['learning_path_id'], ['learning_paths.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['content_id'], ['content.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('learning_path_id', 'order_index', name='uq_learning_path_item_order'),
        sa.UniqueConstraint('learning_path_id', 'content_id', name='uq_learning_path_item_content'),
    )
    op.create_index(
        op.f('ix_learning_path_items_learning_path_id'),
        'learning_path_items', ['learning_path_id'], unique=False,
    )
    op.create_index(
        op.f('ix_learning_path_items_content_id'),
        'learning_path_items', ['content_id'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_learning_path_items_content_id'), table_name='learning_path_items')
    op.drop_index(op.f('ix_learning_path_items_learning_path_id'), table_name='learning_path_items')
    op.drop_table('learning_path_items')
    op.drop_index(op.f('ix_learning_paths_created_by_id'), table_name='learning_paths')
    op.drop_table('learning_paths')
    op.drop_index(op.f('ix_content_uploaded_by_id'), table_name='content')
    op.drop_table('content')
