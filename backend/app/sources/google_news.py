"""
Google News fetcher with publisher domain mapping.
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urlencode

import feedparser

from app.models import NewsItem
from app.sources.common import clean_text, make_news_id, parse_utc_datetime


# Publisher name to domain mapping
PUBLISHER_DOMAIN_MAP = {
    "Reuters": "reuters.com",
    "Bloomberg": "bloomberg.com",
    "Wall Street Journal": "wsj.com",
    "The Wall Street Journal": "wsj.com",
    "Financial Times": "ft.com",
    "CNBC": "cnbc.com",
    "MarketWatch": "marketwatch.com",
    "Benzinga": "benzinga.com",
    "Seeking Alpha": "seekingalpha.com",
    "The Motley Fool": "fool.com",
    "Business Insider": "businessinsider.com",
    "Barron's": "barrons.com",
    "Forbes": "forbes.com",
    "MSN": "msn.com",
    "MarketBeat": "marketbeat.com",
    "CoinCentral": "coincentral.com",
    "Simply Wall St": "simplywall.st",
    "Yahoo Finance": "finance.yahoo.com",
}


def extract_publisher_from_entry(entry) -> Optional[str]:
    """
    Extract publisher name from RSS entry.
    
    Args:
        entry: RSS feed entry
        
    Returns:
        Publisher name or None if not found
    """
    # Try to get publisher from source title
    source = entry.get("source")
    if isinstance(source, dict):
        title = source.get("title")
        if title:
            return clean_text(title)
    
    # Fallback: extract from summary font tags
    summary = entry.get("summary", "") or ""
    font_matches = re.findall(r"<font[^>]*>([^<]+)</font>", summary, flags=re.IGNORECASE)
    return clean_text(font_matches[-1]) if font_matches else None


def map_publisher_to_domain(publisher_name: Optional[str]) -> str:
    """
    Map publisher name to domain.
    
    Args:
        publisher_name: Publisher name from RSS entry
        
    Returns:
        Domain name
    """
    if not publisher_name:
        return "google.com"
    
    publisher_name = clean_text(publisher_name)
    
    # Check direct mapping
    if publisher_name in PUBLISHER_DOMAIN_MAP:
        return PUBLISHER_DOMAIN_MAP[publisher_name]
    
    # If it looks like a domain, normalize it
    normalized = publisher_name.lower().strip()
    if "." in normalized and " " not in normalized:
        if normalized.startswith("www."):
            normalized = normalized[4:]
        return normalized
    
    return "google.com"


class GoogleNewsFetcher:
    """Fetches news articles from Google News RSS feeds."""
    
    BASE_URL = "https://news.google.com/rss/search"
    DEFAULT_DOMAIN = "google.com"

    async def fetch(self, ticker: str, lookback_days: int) -> List[NewsItem]:
        """
        Fetch news articles for a given ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'TSLA', 'AAPL')
            lookback_days: Number of days to look back (not used in RSS)
            
        Returns:
            List of NewsItem objects
        """
        params = urlencode({
            "q": f"{ticker} stock",
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en"
        })
        url = f"{self.BASE_URL}?{params}"

        try:
            feed = feedparser.parse(url)
        except Exception as e:
            # Log error and return empty list
            print(f"Error fetching Google News feed for {ticker}: {e}")
            return []

        items: List[NewsItem] = []

        for entry in feed.entries:
            try:
                # Extract and clean data from RSS entry
                title = clean_text(entry.get("title"))
                link = clean_text(entry.get("link"))
                summary = clean_text(entry.get("summary"))
                published_at = parse_utc_datetime(entry.get("published"))

                # Skip if essential data is missing
                if not title or not link:
                    continue

                # Extract publisher and map to domain
                publisher = extract_publisher_from_entry(entry)
                domain = map_publisher_to_domain(publisher)

                # Generate unique ID
                news_id = make_news_id(link, title, published_at)

                # Create NewsItem
                news_item = NewsItem(
                    id=news_id,
                    source=domain,
                    title=title,
                    url=link,
                    published_at=published_at,
                    text=summary,
                    raw={
                        "publisher": publisher,
                        "google_rss": True,
                        "ticker": ticker
                    },
                )
                
                items.append(news_item)
                
            except Exception as e:
                # Skip malformed entries
                print(f"Error processing Google News entry: {e}")
                continue

        return items