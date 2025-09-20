"""
Yahoo Finance news fetcher.
"""
from __future__ import annotations

from typing import List
from urllib.parse import urlencode

import feedparser

from app.models import NewsItem
from app.sources.common import clean_text, make_news_id, parse_utc_datetime


class YahooFinanceFetcher:
    """Fetches news articles from Yahoo Finance RSS feeds."""
    
    BASE_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline"
    SOURCE_DOMAIN = "finance.yahoo.com"

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
            "s": ticker,
            "region": "US", 
            "lang": "en-US"
        })
        url = f"{self.BASE_URL}?{params}"

        try:
            feed = feedparser.parse(url)
        except Exception as e:
            # Log error and return empty list
            print(f"Error fetching Yahoo Finance feed for {ticker}: {e}")
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

                # Generate unique ID
                news_id = make_news_id(link, title, published_at)

                # Create NewsItem
                news_item = NewsItem(
                    id=news_id,
                    source=self.SOURCE_DOMAIN,
                    title=title,
                    url=link,
                    published_at=published_at,
                    text=summary,
                    raw={"yahoo_rss": True, "ticker": ticker},
                )
                
                items.append(news_item)
                
            except Exception as e:
                # Skip malformed entries
                print(f"Error processing Yahoo Finance entry: {e}")
                continue

        return items