"""Text and date normalisation utilities."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional


def normalize_text(text: Optional[str]) -> Optional[str]:
    """Clean review text: collapse whitespace, strip, remove control chars."""
    if not text:
        return None
    # Remove zero-width and control characters (keep newlines/tabs)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    # Collapse all whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def parse_review_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse a review date from various Booking.com formats.

    Returns a timezone-aware UTC datetime or ``None`` when parsing fails.
    """
    if not date_str:
        return None
    s = date_str.strip()
    # Common patterns seen on Booking.com public pages
    formats = [
        "%B %d, %Y",      # "January 15, 2024"
        "%b %d, %Y",      # "Jan 15, 2024"
        "%d %B %Y",       # "15 January 2024"
        "%d %b %Y",       # "15 Jan 2024"
        "%Y-%m-%d",       # "2024-01-15"
        "%d/%m/%Y",       # "15/01/2024"
        "%m/%d/%Y",       # "01/15/2024"
        "%d-%m-%Y",       # "15-01-2024"
    ]
    # Try stripping a trailing "ago" suffix like "Posted 2 weeks ago"
    s = re.sub(r"(?i)posted\s+", "", s).strip()
    s = re.sub(r"(?i)\s+ago$", "", s).strip()

    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # Try ISO format with optional offset
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def normalize_rating(value) -> Optional[int]:
    """Validate and normalise a rating to an integer 1-10 or 1-5.

    Booking.com typically uses a 10-point scale.  Values outside the
    valid range are rejected.
    """
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        rating = float(value)
    except (TypeError, ValueError):
        return None

    # Accept both 1-5 and 1-10 scales.  Convert 1-5 to 1-10 for storage.
    if 0 < rating <= 5:
        rating = rating * 2
    if 0 < rating <= 10:
        return int(round(rating))
    return None


def extract_language(text: Optional[str]) -> Optional[str]:
    """Naive language detection fallback.

    The scraper should set language when Booking.com provides it.  This
    heuristic only applies when no language metadata is available.
    """
    if not text:
        return None
    # Very small heuristic dictionary – real detection uses the model
    sample = text.lower()
    if any(w in sample for w in ["the ", "and ", "with ", "was ", "for "]):
        return "en"
    if any(w in sample for w in ["der ", "die ", "und ", "von ", "mit "]):
        return "de"
    if any(w in sample for w in ["le ", "la ", "les ", "des ", "et "]):
        return "fr"
    return None