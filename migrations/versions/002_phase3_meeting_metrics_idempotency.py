"""Phase 3: add meeting idempotency + metrics fields.

Revision ID: 002
Revises: 001
Create Date: 2026-03-30
"""

# Standard library
from __future__ import annotations

# Third party
import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("transcript_hash", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("meetings", sa.Column("status", sa.String(length=32), nullable=False, server_default="processed"))
    op.add_column("meetings", sa.Column("processing_ms", sa.Float(), nullable=False, server_default="0"))
    op.add_column("meetings", sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"))
    op.add_column("meetings", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")))

    op.create_index("ix_meetings_transcript_hash", "meetings", ["transcript_hash"])
    op.create_index("ix_meetings_status", "meetings", ["status"])
    op.create_index("ix_meetings_created_at", "meetings", ["created_at"])
    op.create_unique_constraint("uq_meetings_transcript_hash", "meetings", ["transcript_hash"])

    op.add_column("action_items", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")))
    op.create_index("ix_action_items_created_at", "action_items", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_action_items_created_at", table_name="action_items")
    op.drop_column("action_items", "created_at")

    op.drop_constraint("uq_meetings_transcript_hash", "meetings", type_="unique")
    op.drop_index("ix_meetings_created_at", table_name="meetings")
    op.drop_index("ix_meetings_status", table_name="meetings")
    op.drop_index("ix_meetings_transcript_hash", table_name="meetings")

    op.drop_column("meetings", "created_at")
    op.drop_column("meetings", "cost_usd")
    op.drop_column("meetings", "processing_ms")
    op.drop_column("meetings", "status")
    op.drop_column("meetings", "transcript_hash")

