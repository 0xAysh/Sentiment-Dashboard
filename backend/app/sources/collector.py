"""
News collection coordinator that aggregates from multiple sources.
"""
from __future__ import annotations

import asyncio
from typing import List, Iterable

from app.models import NewsItem
from app.sources.google_news import GoogleNewsFetcher
from app.sources.yfinance import YahooFinanceFetcher
from app.config import MAX_ITEMS, SOURCE_BASE_WEIGHTS, DEFAULT_SOURCE_WEIGHT


def deduplicate_news_items(items: Iterable[NewsItem]) -> List[NewsItem]:
    """
    Remove duplicate news items based on URL and title.
    
    Args:
        items: Iterable of NewsItem objects
        
    Returns:
        List of unique NewsItem objects
    """
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique_items: List[NewsItem] = []
    
    for item in items:
        # Normalize URL by removing query parameters
        url_key = (item.url or "").split("?")[0]
        
        # Skip if URL already seen
        if url_key and url_key in seen_urls:
            continue
            
        # Skip if title already seen
        title = item.title or ""
        if title and title in seen_titles:
            continue
        
        # Add to seen sets and result
        seen_urls.add(url_key)
        seen_titles.add(title)
        unique_items.append(item)
    
    return unique_items


def is_trusted_source(domain: str) -> bool:
    """
    Check if a news source is trusted based on credibility weight.
    
    Args:
        domain: News source domain
        
    Returns:
        True if source is trusted (weight >= 0.6)
    """
    weight = SOURCE_BASE_WEIGHTS.get(domain, DEFAULT_SOURCE_WEIGHT)
    return weight >= 0.6


async def collect_news(ticker: str, lookback_days: int, limit: int | None = None) -> List[NewsItem]:
    """
    Collect news articles from multiple sources for a given ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'TSLA', 'AAPL')
        lookback_days: Number of days to look back
        limit: Maximum number of items to return (defaults to MAX_ITEMS)
        
    Returns:
        List of NewsItem objects, sorted by publication date (newest first)
    """
    # Initialize fetchers
    google_fetcher = GoogleNewsFetcher()
    yahoo_fetcher = YahooFinanceFetcher()
    
    # Fetch from all sources concurrently
    try:
        google_items, yahoo_items = await asyncio.gather(
            google_fetcher.fetch(ticker, lookback_days),
            yahoo_fetcher.fetch(ticker, lookback_days),
        )
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []

    # Combine all items
    all_items = [*google_items, *yahoo_items]

    # Filter to trusted sources only
    trusted_items = [item for item in all_items if is_trusted_source(item.source)]

    # Sort by publication date (newest first)
    trusted_items.sort(key=lambda item: item.published_at, reverse=True)

    # Remove duplicates
    unique_items = deduplicate_news_items(trusted_items)

    # Apply limit
    max_items = min(limit or MAX_ITEMS, len(unique_items))
    return unique_items[:max_items]