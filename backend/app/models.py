"""
File: app/models.py
Internal data structures used during collection/analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


JsonDict = Dict[str, Any]


@dataclass
class NewsItem:
    """Unified representation of a news/post item prior to response marshalling.

    Fields with Optional[...] are filled during the analysis stage.
    """

    # Identity & content
    id: str
    source: str  # domain, e.g., "reuters.com" or "reddit.com"
    title: str
    url: str
    published_at: datetime
    text: str

    # Raw metadata from the source fetcher (for debugging/engagement calc)
    raw: JsonDict = field(default_factory=dict)

    # Sentiment outputs (set by core/sentiment)
    label: Optional[str] = None  # "positive" | "neutral" | "negative"
    prob_positive: Optional[float] = None
    prob_neutral: Optional[float] = None
    prob_negative: Optional[float] = None
    score: Optional[float] = None  # [-1, 1], typically p_pos - p_neg

    # Weighting components and results (set by core/sentiment)
    recency_w: Optional[float] = None
    source_w: Optional[float] = None
    engage_w: Optional[float] = None
    weight: Optional[float] = None        # [0, 1]
    weighted_score: Optional[float] = None # weight * score


__all__ = ["NewsItem", "JsonDict"]
