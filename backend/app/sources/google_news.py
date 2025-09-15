"""
File: app/sources/google_news.py
Google News RSS fetcher for ticker-related headlines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from urllib.parse import urlencode

import feedparser
import httpx
from dateutil import parser as dateparser

from app.models import NewsItem
from app.utils import norm_text, url_domain, make_id
from app.config import HEADERS


class GoogleNewsFetcher:
    """Fetch news via Google News RSS. We query "{TICKER} stock" and let
    Google aggregate from mainstream sources. We score titles/summaries.
    """

    async def fetch(self, ticker: str, lookback_days: int) -> List[NewsItem]:
        query = f"{ticker} stock"
        q = {
            "q": f"{query} when:{lookback_days}d",
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        }
        url = f"https://news.google.com/rss/search?{urlencode(q)}"

        async with httpx.AsyncClient(headers=HEADERS, timeout=20) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)

        items: List[NewsItem] = []
        for e in feed.entries:
            title = norm_text(getattr(e, "title", ""))
            link = norm_text(getattr(e, "link", ""))
            summary = norm_text(getattr(e, "summary", getattr(e, "description", "")))
            published = getattr(e, "published", getattr(e, "updated", ""))

            if not title or not link:
                continue

            try:
                dt = dateparser.parse(published) if published else None
                if dt is None:
                    dt = datetime.now(timezone.utc)
                elif dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
            except Exception:
                dt = datetime.now(timezone.utc)

            items.append(
                NewsItem(
                    id=make_id("gn", link),
                    source=url_domain(link),
                    title=title,
                    url=link,
                    published_at=dt,
                    text=summary,
                    raw={"source": "googlenews", "entry_id": getattr(e, "id", "")},
                )
            )

        return items
