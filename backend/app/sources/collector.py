# app/sources/collector.py
from __future__ import annotations

import asyncio
from typing import List, Iterable

from app.models import NewsItem
from app.sources.google_news import GoogleNewsFetcher
from app.sources.yfinance import YahooFinanceFetcher
from app.config import MAX_ITEMS, SOURCE_BASE_WEIGHTS, DEFAULT_SOURCE_WEIGHT

def _dedupe(items: Iterable[NewsItem]) -> List[NewsItem]:
    seen_url: set[str] = set()
    seen_title: set[str] = set()
    out: List[NewsItem] = []
    for it in items:
        url_key = (it.url or "").split("?")[0]
        if url_key and url_key in seen_url:
            continue
        t = it.title or ""
        if t and t in seen_title:
            continue
        seen_url.add(url_key)
        seen_title.add(t)
        out.append(it)
    return out

def _is_trusted(domain: str) -> bool:
    # Accept if credibility weight >= 0.6
    w = SOURCE_BASE_WEIGHTS.get(domain, DEFAULT_SOURCE_WEIGHT)
    return w >= 0.6

async def collect_news(ticker: str, lookback_days: int, limit: int | None = None) -> List[NewsItem]:
    # Run both fetchers concurrently
    gfetch = GoogleNewsFetcher()
    yfetch = YahooFinanceFetcher()
    g_items, y_items = await asyncio.gather(
        gfetch.fetch(ticker, lookback_days),
        yfetch.fetch(ticker, lookback_days),
    )

    items: List[NewsItem] = [*g_items, *y_items]

    # Filter to trusted domains
    items = [it for it in items if _is_trusted(it.source)]

    # Newest first
    items.sort(key=lambda it: it.published_at, reverse=True)

    # Dedupe
    items = _dedupe(items)

    # Cap
    cap = min(limit or MAX_ITEMS, len(items))
    return items[:cap]
