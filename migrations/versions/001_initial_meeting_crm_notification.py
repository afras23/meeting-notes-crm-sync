"""Initial tables: meetings, action_items, crm_sync_records, notifications.

Revision ID: 001
Revises:
Create Date: 2026-03-30
"""

# Standard library
from __future__ import annotations

# Third party
import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("meeting_series_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=128), nullable=True),
        sa.Column("project_id", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extraction_json", sa.JSON(), nullable=False),
        sa.Column("crm_updates_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meetings_meeting_series_id", "meetings", ["meeting_series_id"])
    op.create_index("ix_meetings_deal_id", "meetings", ["deal_id"])
    op.create_index("ix_meetings_project_id", "meetings", ["project_id"])

    op.create_table(
        "action_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("meeting_id", sa.String(length=64), nullable=False),
        sa.Column("owner", sa.String(length=256), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "crm_sync_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("meeting_id", sa.String(length=64), nullable=False),
        sa.Column("deal_id", sa.String(length=128), nullable=False),
        sa.Column("changed_properties_json", sa.JSON(), nullable=False),
        sa.Column("previous_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crm_sync_records_meeting_id", "crm_sync_records", ["meeting_id"])
    op.create_index("ix_crm_sync_records_deal_id", "crm_sync_records", ["deal_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("meeting_id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_meeting_id", "notifications", ["meeting_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_meeting_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_crm_sync_records_deal_id", table_name="crm_sync_records")
    op.drop_index("ix_crm_sync_records_meeting_id", table_name="crm_sync_records")
    op.drop_table("crm_sync_records")
    op.drop_table("action_items")
    op.drop_index("ix_meetings_project_id", table_name="meetings")
    op.drop_index("ix_meetings_deal_id", table_name="meetings")
    op.drop_index("ix_meetings_meeting_series_id", table_name="meetings")
    op.drop_table("meetings")
