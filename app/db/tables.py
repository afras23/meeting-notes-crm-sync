"""
SQLAlchemy ORM tables for persisted meetings, CRM sync, and notifications.
"""

# Standard library
from __future__ import annotations

from datetime import datetime
from typing import Any

# Third party
from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Local
from app.db.base import Base


class MeetingORM(Base):
    """Persisted meeting aggregate."""

    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    meeting_series_id: Mapped[str] = mapped_column(String(64), index=True)
    deal_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    transcript: Mapped[str] = mapped_column(Text())
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extraction_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    crm_updates_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float())
    transcript_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="processed", index=True)
    processing_ms: Mapped[float] = mapped_column(Float(), default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float(), default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (UniqueConstraint("transcript_hash", name="uq_meetings_transcript_hash"),)

    action_items: Mapped[list["ActionItemORM"]] = relationship(
        "ActionItemORM",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )


class ActionItemORM(Base):
    """Persisted action item."""

    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    meeting_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("meetings.id", ondelete="CASCADE")
    )
    owner: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str] = mapped_column(Text())
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    meeting: Mapped["MeetingORM"] = relationship("MeetingORM", back_populates="action_items")


class CrmSyncRecordORM(Base):
    """Audit row for CRM diff application."""

    __tablename__ = "crm_sync_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    meeting_id: Mapped[str] = mapped_column(String(64), index=True)
    deal_id: Mapped[str] = mapped_column(String(128), index=True)
    changed_properties_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    previous_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class NotificationORM(Base):
    """Outbound notification log."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    meeting_id: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
