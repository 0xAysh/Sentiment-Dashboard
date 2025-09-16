"""
File: app/utils.py
Shared helpers + response builder used by the API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import List, Optional
from urllib.parse import urlparse
import re

import tldextract

from app import schemas
from app.models import NewsItem


# --- Time helpers ----------------------------------------------------------

def now_utc() -> datetime:
    """Return current time in UTC with tzinfo."""
    return datetime.now(timezone.utc)


# --- Text/URL helpers ------------------------------------------------------

def norm_text(s: str) -> str:
    """Normalize whitespace in text; safe for None by treating as ''."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def url_domain(u: str) -> str:
    """Extract registrable domain from URL, e.g. https://m.reuters.com -> reuters.com."""
    try:
        ext = tldextract.extract(u)
        domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
        return (domain or urlparse(u).netloc).lower()
    except Exception:
        return urlparse(u).netloc.lower()


def make_id(*parts: str) -> str:
    """Deterministic short id from joined parts."""
    return sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# --- Response builder ------------------------------------------------------

def to_response(
    ticker: str,
    items: List[NewsItem],
    rationales: Optional[List[str]] = None,
    lookback_days: int = 5,
) -> schemas.SentimentResponse:
    """Turn analyzed NewsItems into a SentimentResponse with non-optional rationales."""

    # overall score (weighted average of weighted_score)
    weights = [float(it.weight or 0.0) for it in items]
    wscores = [float(it.weighted_score or 0.0) for it in items]
    overall = (sum(wscores) / (sum(weights) or 1.0)) if (wscores and weights) else 0.0

    # make sure we have a rationale string per item
    n = len(items)
    if not rationales:
        safe_rationales = [""] * n
    else:
        safe_rationales = [str(x or "") for x in rationales]
        if len(safe_rationales) < n:
            safe_rationales += [""] * (n - len(safe_rationales))
        elif len(safe_rationales) > n:
            safe_rationales = safe_rationales[:n]

    # rebuild items as *schemas.NewsItem* (fresh instances) so Pydantic
    # validation never trips over hot-reload class identity
    resp_items: List[schemas.NewsItem] = []
    for idx, it in enumerate(items):
        resp_items.append(
            schemas.NewsItem(
                id=it.id,
                source=it.source,
                title=it.title,
                url=it.url,
                published_at=it.published_at,
                text=it.text or "",
                label=it.label or "neutral",
                prob_positive=float(it.prob_positive or 0.0),
                prob_neutral=float(it.prob_neutral or 0.0),
                prob_negative=float(it.prob_negative or 0.0),
                score=float(it.score or 0.0),
                weight=float(it.weight or 0.0),
                weighted_score=float(it.weighted_score or 0.0),
                rationale=safe_rationales[idx],          # <<< always a string
                raw=getattr(it, "raw", None),
            )
        )

    return schemas.SentimentResponse(
        ticker=ticker,
        as_of=datetime.now(timezone.utc).isoformat(),  # your schema uses str
        lookback_days=lookback_days,
        overall_score=round(overall, 4),
        n_items=len(resp_items),
        items=resp_items,
    )