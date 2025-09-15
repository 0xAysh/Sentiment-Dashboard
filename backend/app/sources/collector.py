"""
File: app/sources/collector.py
Aggregates news from individual fetchers (Google News, Reddit, etc.).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List

from app.models import NewsItem
from app.config import MAX_ITEMS

# Import fetchers (to be created next)
from .google_news import GoogleNewsFetcher
from .reddit import RedditFetcher



def _within_lookback(dt: datetime, days: int) -> bool:
    return dt >= datetime.now(timezone.utc) - timedelta(days=days)


def _dedupe(items: List[NewsItem]) -> List[NewsItem]:
    seen: set[str] = set()
    out: List[NewsItem] = []
    for it in items:
        key = it.url or it.title.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


# Register available fetchers here
FETCHERS = [GoogleNewsFetcher(), RedditFetcher()]


async def collect_news(ticker: str, lookback_days: int) -> List[NewsItem]:
    """Run all fetchers concurrently, clean, filter, sort, and cap."""
    results = await asyncio.gather(
        *[f.fetch(ticker, lookback_days) for f in FETCHERS],
        return_exceptions=True,
    )

    all_items: List[NewsItem] = []
    for res in results:
        if isinstance(res, Exception):
            continue
        all_items.extend(res)

    # Filter by window
    all_items = [it for it in all_items if _within_lookback(it.published_at, lookback_days)]

    # Dedupe by URL/title
    all_items = _dedupe(all_items)

    # Order newest-first and cap
    all_items.sort(key=lambda x: x.published_at, reverse=True)
    cap = min(MAX_ITEMS, len(all_items))
    return all_items[:MAX_ITEMS]

