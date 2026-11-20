"""Sentiment analysis service.

Uses a HuggingFace transformer model when available and falls back to
a deterministic VADER-style lexicon when the model cannot be loaded or
when the AI API is unreachable.  The fallback is deterministic so that
weekly comparisons remain stable.
"""

from __future__ import annotations

import os
import re
from typing import Optional, Tuple

import numpy as np


POSITIVE_WORDS = {
    "excellent", "amazing", "great", "wonderful", "fantastic", "awesome",
    "perfect", "loved", "love", "loved", "beautiful", "nice", "clean",
    "comfortable", "friendly", "helpful", "professional", "spotless",
    "delicious", "tasty", "spacious", "cozy", "warm", " welcoming",
    "recommend", "highly", "best", "good", "positive", "outstanding",
    "superb", "brilliant", "exceptional", "pleasant", "heavenly",
}

NEGATIVE_WORDS = {
    "terrible", "awful", "bad", "poor", "horrible", "disappointing",
    "disappointed", "dirty", "uncomfortable", "rude", "unhelpful",
    "unfriendly", "broken", "noise", "noisy", "loud", "smelly",
    "smell", "stain", "mould", "mold", "bug", "cockroach", "wait",
    "slow", "delay", "late", "overpriced", "expensive", "cheap",
    "worst", "hate", "hated", "disgusting", "disgusted", "pathetic",
    "useless", "unacceptable", "terrible", "wrong", "problem",
    "problems", "issue", "issues", "complaint", "complaints",
}


class SentimentAnalyzer:
    """Hybrid sentiment analyser with a deterministic fallback."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name
        self.pipeline = None
        self._load_model()

    def _load_model(self) -> None:
        """Attempt to load a HuggingFace sentiment pipeline.

        The model is loaded lazily and failures are silently swallowed so
        that the application can start without network access or heavy
        dependencies.  All classification then falls back to the lexicon.
        """
        try:
            from transformers import pipeline  # type: ignore

            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model_name or "cardiffnlp/twitter-roberta-base-sentiment-latest",
                tokenizer=self.model_name or "cardiffnlp/twitter-roberta-base-sentiment-latest",
                truncation=True,
                max_length=512,
            )
        except Exception:
            self.pipeline = None

    def analyze(self, text: Optional[str]) -> Tuple[str, float]:
        """Return ``(sentiment_label, confidence_score)``.

        Labels are one of ``positive``, ``negative`` or ``neutral``.
        """
        if not text or not text.strip():
            return "neutral", 0.0

        if self.pipeline is not None:
            try:
                result = self.pipeline(text[:512])[0]
                label = result["label"].lower()
                score = float(result["score"])
                # Normalise label vocabulary
                if "positive" in label or "pos" in label:
                    return "positive", score
                if "negative" in label or "neg" in label:
                    return "negative", score
                return "neutral", score
            except Exception:
                pass

        return self._lexicon_analyze(text)

    def _lexicon_analyze(self, text: str) -> Tuple[str, float]:
        """Deterministic lexicon-based fallback."""
        words = set(re.findall(r"\b\w+\b", text.lower()))
        pos = len(words & POSITIVE_WORDS)
        neg = len(words & NEGATIVE_WORDS)
        total = pos + neg
        if total == 0:
            return "neutral", 0.0
        if pos > neg:
            return "positive", min(0.95, 0.5 + (pos - neg) / (2 * total))
        if neg > pos:
            return "negative", min(0.95, 0.5 + (neg - pos) / (2 * total))
        return "neutral", 0.5


_analyzer: Optional[SentimentAnalyzer] = None


def get_analyzer() -> SentimentAnalyzer:
    """Return a process-wide singleton analyser."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer