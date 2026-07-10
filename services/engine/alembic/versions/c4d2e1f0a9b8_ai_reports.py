"""ai_reports

Revision ID: c4d2e1f0a9b8
Revises: f2b025ee9893
Create Date: 2026-06-29 09:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c4d2e1f0a9b8'
down_revision: str | None = 'f2b025ee9893'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'ai_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('model', sa.String(length=64), nullable=False),
        sa.Column('sentiment', sa.String(length=16), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('ai_reports', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_ai_reports_symbol'), ['symbol'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_ai_reports_created_at'), ['created_at'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('ai_reports', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ai_reports_created_at'))
        batch_op.drop_index(batch_op.f('ix_ai_reports_symbol'))

    op.drop_table('ai_reports')
