from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_entry_id() -> str:
    return f"fp_{uuid_lib.uuid4().hex[:8]}"


class FootprintEntry(Base):
    """A single ingested baseline data point (caption + optional image signals).

    Replaces the old in-memory UserFootprint list — same fields, persisted
    per session_id instead of living only for the lifetime of the process.
    """

    __tablename__ = "footprint_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_entry_id)
    session_id: Mapped[str] = mapped_column(String, index=True)
    label: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    entities: Mapped[dict] = mapped_column(JSON)
    # Named image_metadata, not metadata — SQLAlchemy reserves Base.metadata.
    image_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    time_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    has_gps: Mapped[bool] = mapped_column(Boolean, default=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "text": self.text,
            "entities": self.entities,
            "metadata": self.image_metadata or {},
            "time_context": self.time_context,
            "has_gps": self.has_gps,
            "ingested_at": self.ingested_at.isoformat(),
        }


class ScoreHistoryEntry(Base):
    """One row per completed analysis run — replaces the jsonblob.com history blob."""

    __tablename__ = "score_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    breach_probability: Mapped[float] = mapped_column(Float)
    severity_counts: Mapped[dict] = mapped_column(JSON)
    entity_counts: Mapped[dict] = mapped_column(JSON)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "breach_probability": self.breach_probability,
            "severity_counts": self.severity_counts,
            "entity_counts": self.entity_counts,
        }


class AnalysisResult(Base):
    """Full analysis payload per run — powers the "view past report" dashboard feature."""

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    breach_probability: Mapped[float] = mapped_column(Float)
    result: Mapped[dict] = mapped_column(JSON)


class GeocodeCache(Base):
    """Postgres-backed cache in front of Nominatim (1 req/sec limit) — no Redis needed at this scale."""

    __tablename__ = "geocode_cache"

    query_text: Mapped[str] = mapped_column(String, primary_key=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
