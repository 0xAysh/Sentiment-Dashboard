"""
Shared utility functions for the news sentiment application.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List

import tldextract
from app.models import NewsItem
from app.schemas import SentimentResponse


def now_utc() -> datetime:
    """
    Get current UTC datetime with timezone information.
    
    Returns:
        Current UTC datetime
    """
    return datetime.now(timezone.utc)


def normalize_text(text: str | None) -> str:
    """
    Normalize whitespace in text content.
    
    Args:
        text: Input text string (can be None)
        
    Returns:
        Normalized text with single spaces and trimmed edges
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def extract_domain_from_url(url: str) -> str:
    """
    Extract the main domain from a URL.
    
    Args:
        url: Full URL string
        
    Returns:
        Normalized domain name in lowercase
    """
    try:
        extracted = tldextract.extract(url)
        domain = f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else extracted.domain
        return (domain or tldextract.extract(url).domain).lower()
    except Exception:
        # Fallback to simple parsing
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()


def generate_id(*parts: str) -> str:
    """
    Generate a deterministic short ID from multiple string parts.
    
    Args:
        *parts: Variable number of string arguments
        
    Returns:
        16-character hexadecimal string
    """
    from hashlib import sha256
    key = "|".join(parts).encode("utf-8")
    return sha256(key).hexdigest()[:16]


def clamp_to_unit_range(value: float) -> float:
    """
    Clamp a float value to the range [0.0, 1.0].
    
    Args:
        value: Input float value
        
    Returns:
        Value clamped to [0.0, 1.0] range
    """
    return max(0.0, min(1.0, value))


def calculate_overall_sentiment(items: List[NewsItem]) -> float:
    """
    Calculate weighted average sentiment score across all news items.
    
    Args:
        items: List of NewsItem objects with sentiment analysis
        
    Returns:
        Overall sentiment score between -1.0 and 1.0
    """
    if not items:
        return 0.0
    
    numerator = sum(getattr(item, "weighted_score", 0.0) for item in items)
    denominator = sum(getattr(item, "weight", 1.0) for item in items)
    
    return round(numerator / denominator, 4) if denominator else 0.0


def attach_rationales_to_items(items: List[NewsItem], rationales: List[str] | None) -> None:
    """
    Attach AI-generated rationales to news items.
    
    Args:
        items: List of NewsItem objects
        rationales: List of rationale strings (can be None)
    """
    if not items:
        return
    
    rationale_list = rationales or []
    
    for i, item in enumerate(items):
        if i < len(rationale_list) and isinstance(rationale_list[i], str):
            item.rationale = rationale_list[i].strip()
        else:
            item.rationale = getattr(item, "rationale", "").strip()
        
        # Ensure rationale is always a string
        if not item.rationale:
            item.rationale = ""


def build_sentiment_response(
    ticker: str,
    items: List[NewsItem],
    rationales: List[str] | None,
    lookback_days: int,
) -> SentimentResponse:
    """
    Build the final API response with sentiment analysis results.
    
    Args:
        ticker: Stock ticker symbol
        items: List of analyzed NewsItem objects
        rationales: List of rationale strings
        lookback_days: Number of days looked back
        
    Returns:
        SentimentResponse object
    """
    # Attach rationales before building response
    attach_rationales_to_items(items, rationales)
    
    return SentimentResponse(
        ticker=ticker,
        as_of=now_utc().isoformat(),
        lookback_days=lookback_days,
        overall_score=calculate_overall_sentiment(items),
        n_items=len(items),
        items=items,
    )