"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PropertyResponse(BaseModel):
    id: int
    name: str
    property_code: str
    booking_url: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReviewResponse(BaseModel):
    id: int
    external_review_id: Optional[str] = None
    property_id: int
    review_date: datetime
    rating: int
    positive_text: Optional[str] = None
    negative_text: Optional[str] = None
    language: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    topics: Optional[list] = None
    source_url: Optional[str] = None
    review_hash: str
    collected_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    items: List[ReviewResponse]
    total: int
    page: int
    page_size: int


class CollectionLogResponse(BaseModel):
    id: int
    property_id: Optional[int] = None
    status: str
    reviews_discovered: int
    reviews_inserted: int
    duplicates_skipped: int
    invalid_skipped: int
    errors: Optional[list] = None
    duration_seconds: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InsightResponse(BaseModel):
    id: int
    property_id: Optional[int] = None
    topic: str
    sentiment: str
    mention_count: int
    percentage: float
    generated_at: datetime

    model_config = {"from_attributes": True}


class KPIResponse(BaseModel):
    label: str
    value: float | int
    change: Optional[float] = None
    change_direction: Optional[str] = None  # "up" | "down" | "flat"


class OverviewResponse(BaseModel):
    kpis: List[KPIResponse]
    weekly_trends: List[dict]
    pos_neg_trends: List[dict]
    property_comparison: List[dict]
    volume_by_property: List[dict]
    topic_distribution: List[dict]
    date_range: dict
    data_source: str = "live"


class PropertyDetailResponse(PropertyResponse):
    avg_rating: Optional[float] = None
    total_reviews: int = 0
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    weekly_performance: List[dict] = Field(default_factory=list)
    top_complaints: List[dict] = Field(default_factory=list)
    top_compliments: List[dict] = Field(default_factory=list)
    recent_reviews: List[ReviewResponse] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class CollectionRunRequest(BaseModel):
    property_code: Optional[str] = None
    incremental: bool = True


class CollectionRunResponse(BaseModel):
    status: str
    message: str
    logs: List[CollectionLogResponse]


class ImportRequest(BaseModel):
    data: List[dict]
    source: str = "imported"
    clear_existing: bool = False


class ImportResponse(BaseModel):
    status: str
    inserted: int
    updated: int
    duplicates_skipped: int
    invalid_skipped: int
    errors: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    timestamp: datetime