"""create methodology tables

Revision ID: f49241d88702
Revises: 080c74a6ab60
Create Date: 2026-10-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f49241d88702'
down_revision: Union[str, Sequence[str], None] = '080c74a6ab60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'methodologies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('calibration_version', sa.String(length=128), nullable=False),
        sa.Column('methodology_name', sa.String(length=64), nullable=False),
        sa.Column('project', sa.String(length=128), nullable=False),
        sa.Column(
            'status',
            sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='methodology_status', native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('calibration_version', name='uq_methodologies_calibration_version'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_methodologies_status'), 'methodologies', ['status'], unique=False)
    op.create_index(op.f('ix_methodologies_created_by_id'), 'methodologies', ['created_by_id'], unique=False)
    # No máximo 1 PUBLISHED por vez — invariante garantida no banco (sobrevive a
    # publicações concorrentes), não só por regra de aplicação.
    op.create_index(
        'uq_methodology_single_published',
        'methodologies',
        ['status'],
        unique=True,
        postgresql_where=sa.text("status = 'PUBLISHED'"),
    )

    op.create_table(
        'methodology_categories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('methodology_id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(length=32), nullable=False),
        sa.Column('label', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['methodology_id'], ['methodologies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('methodology_id', 'key', name='uq_methodology_category_key'),
    )
    op.create_index(
        op.f('ix_methodology_categories_methodology_id'),
        'methodology_categories', ['methodology_id'], unique=False,
    )

    op.create_table(
        'calibrators',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('methodology_id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(length=32), nullable=False),
        sa.Column('label', sa.String(length=64), nullable=False),
        sa.Column(
            'color',
            sa.Enum('verde', 'amarelo', 'laranja', 'vermelho', name='calibrator_color', native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column('min', sa.Float(), nullable=False),
        sa.Column('max', sa.Float(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['methodology_id'], ['methodologies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('methodology_id', 'key', name='uq_calibrator_key'),
    )
    op.create_index(
        op.f('ix_calibrators_methodology_id'), 'calibrators', ['methodology_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_calibrators_methodology_id'), table_name='calibrators')
    op.drop_table('calibrators')
    op.drop_index(op.f('ix_methodology_categories_methodology_id'), table_name='methodology_categories')
    op.drop_table('methodology_categories')
    op.drop_index('uq_methodology_single_published', table_name='methodologies')
    op.drop_index(op.f('ix_methodologies_created_by_id'), table_name='methodologies')
    op.drop_index(op.f('ix_methodologies_status'), table_name='methodologies')
    op.drop_table('methodologies')
