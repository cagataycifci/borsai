"""scheduled_reports

Revision ID: d8f4b2a31c67
Revises: b7e3a1c92d55
Create Date: 2026-06-29 18:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d8f4b2a31c67"
down_revision: str | None = "b7e3a1c92d55"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("scheduled_reports", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_scheduled_reports_kind"), ["kind"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_scheduled_reports_created_at"), ["created_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("scheduled_reports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_scheduled_reports_created_at"))
        batch_op.drop_index(batch_op.f("ix_scheduled_reports_kind"))
    op.drop_table("scheduled_reports")
