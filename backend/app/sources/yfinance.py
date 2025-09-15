from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode
import hashlib

import feedparser
from dateutil import parser as dateparser

from app.models import NewsItem


def _to_utc(s: Optional[str]) -> datetime:
    if not s:
        return datetime.now(timezone.utc)
    d = dateparser.parse(s)
    return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _make_id(url: str, title: str, published_at: datetime) -> str:
    key = f"{url}|{title}|{published_at.isoformat()}".encode("utf-8", "ignore")
    return hashlib.blake2b(key, digest_size=8).hexdigest()


class YahooFinanceFetcher:
    BASE = "https://feeds.finance.yahoo.com/rss/2.0/headline"

    async def fetch(self, ticker: str, lookback_days: int) -> List[NewsItem]:
        params = urlencode({"s": ticker, "region": "US", "lang": "en-US"})
        url = f"{self.BASE}?{params}"

        feed = feedparser.parse(url)
        items: List[NewsItem] = []

        for e in feed.entries:
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            summary = (e.get("summary") or "").strip()
            published_at = _to_utc(e.get("published"))

            nid = _make_id(link, title, published_at)

            items.append(
                NewsItem(
                    id=nid,                           # string id (Pydantic fix)
                    source="finance.yahoo.com",
                    title=title,
                    url=link,
                    published_at=published_at,
                    text=summary,
                    raw={"yahoo_rss": True},
                )
            )
        return items
