"""create learning path enrollment tables

Revision ID: 5c4395d2de1c
Revises: d4f8a3c1e6b2
Create Date: 2026-10-02 19:16:25.942599

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c4395d2de1c'
down_revision: Union[str, Sequence[str], None] = 'd4f8a3c1e6b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'learning_path_enrollments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('learning_path_id', sa.UUID(), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['learning_path_id'], ['learning_paths.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'learning_path_id', name='uq_enrollment_user_path'),
    )
    op.create_index(
        op.f('ix_learning_path_enrollments_user_id'), 'learning_path_enrollments', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_learning_path_enrollments_learning_path_id'),
        'learning_path_enrollments', ['learning_path_id'], unique=False,
    )

    op.create_table(
        'learning_path_item_completions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('enrollment_id', sa.UUID(), nullable=False),
        sa.Column('learning_path_item_id', sa.UUID(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['enrollment_id'], ['learning_path_enrollments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['learning_path_item_id'], ['learning_path_items.id'], ondelete='CASCADE'),
        sa.UniqueConstraint(
            'enrollment_id', 'learning_path_item_id', name='uq_completion_enrollment_item'
        ),
    )
    op.create_index(
        op.f('ix_learning_path_item_completions_enrollment_id'),
        'learning_path_item_completions', ['enrollment_id'], unique=False,
    )
    op.create_index(
        op.f('ix_learning_path_item_completions_learning_path_item_id'),
        'learning_path_item_completions', ['learning_path_item_id'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_learning_path_item_completions_learning_path_item_id'),
        table_name='learning_path_item_completions',
    )
    op.drop_index(
        op.f('ix_learning_path_item_completions_enrollment_id'),
        table_name='learning_path_item_completions',
    )
    op.drop_table('learning_path_item_completions')
    op.drop_index(
        op.f('ix_learning_path_enrollments_learning_path_id'), table_name='learning_path_enrollments'
    )
    op.drop_index(op.f('ix_learning_path_enrollments_user_id'), table_name='learning_path_enrollments')
    op.drop_table('learning_path_enrollments')
