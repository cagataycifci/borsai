"""alerts

Revision ID: b7e3a1c92d55
Revises: c4d2e1f0a9b8
Create Date: 2026-06-29 12:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b7e3a1c92d55'
down_revision: str | None = 'c4d2e1f0a9b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('params', sa.JSON(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('cooldown_seconds', sa.Integer(), nullable=False),
        sa.Column('note', sa.String(length=256), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('alerts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_alerts_symbol'), ['symbol'], unique=False)

    op.create_table(
        'alert_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('message', sa.String(length=512), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('alert_events', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_alert_events_alert_id'), ['alert_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_alert_events_symbol'), ['symbol'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_alert_events_created_at'), ['created_at'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('alert_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_alert_events_created_at'))
        batch_op.drop_index(batch_op.f('ix_alert_events_symbol'))
        batch_op.drop_index(batch_op.f('ix_alert_events_alert_id'))
    op.drop_table('alert_events')

    with op.batch_alter_table('alerts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_alerts_symbol'))
    op.drop_table('alerts')
