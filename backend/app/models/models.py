"""SQLAlchemy models for Azzurro Review Intelligence."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql.sqltypes import JSON


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_hash(property_id: int, review_date: datetime, rating: int) -> str:
    """Create a deterministic hash used for deduplication."""
    raw = f"{property_id}|{review_date.isoformat()}|{rating}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Base(DeclarativeBase):
    pass


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    property_code = Column(String(64), nullable=False, unique=True)
    booking_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    reviews = relationship("Review", back_populates="review_property", cascade="all, delete-orphan")
    collection_logs = relationship("CollectionLog", back_populates="log_property")
    insights = relationship("Insight", back_populates="insight_property")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Property {self.property_code}>"


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_review_id = Column(String(128), nullable=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    review_date = Column(DateTime(timezone=True), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    positive_text = Column(Text, nullable=True)
    negative_text = Column(Text, nullable=True)
    language = Column(String(8), nullable=True)
    sentiment = Column(String(16), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    topics = Column(JSON, nullable=True)
    source_url = Column(Text, nullable=True)
    review_hash = Column(String(64), nullable=False, unique=True, index=True)
    collected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    review_property = relationship("Property", back_populates="reviews")

    __table_args__ = (
        Index("ix_reviews_property_date", "property_id", "review_date"),
        UniqueConstraint("property_id", "review_hash", name="uq_reviews_property_hash"),
    )

    @property
    def combined_text(self) -> str:
        """Return the full review text for sentiment analysis."""
        parts = []
        if self.positive_text:
            parts.append(self.positive_text)
        if self.negative_text:
            parts.append(self.negative_text)
        return " ".join(parts).strip()

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Review {self.id} rating={self.rating}>"


class CollectionLog(Base):
    __tablename__ = "collection_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), nullable=False)
    reviews_discovered = Column(Integer, default=0, nullable=False)
    reviews_inserted = Column(Integer, default=0, nullable=False)
    duplicates_skipped = Column(Integer, default=0, nullable=False)
    invalid_skipped = Column(Integer, default=0, nullable=False)
    errors = Column(JSON, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    log_property = relationship("Property", back_populates="collection_logs")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<CollectionLog {self.id} status={self.status}>"


class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=True)
    topic = Column(String(64), nullable=False)
    sentiment = Column(String(16), nullable=False)
    mention_count = Column(Integer, default=0, nullable=False)
    percentage = Column(Float, default=0.0, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    insight_property = relationship("Property", back_populates="insights")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Insight {self.topic}/{self.sentiment} {self.percentage:.1f}%>"