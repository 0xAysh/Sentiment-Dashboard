# app/sources/google_news.py
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlencode   # <-- add

import feedparser
from dateutil import parser as dateparser

from app.models import NewsItem
# add import
import hashlib

# helper
def _make_id(url: str, title: str, published_at: datetime) -> str:
    key = f"{url}|{title}|{published_at.isoformat()}".encode("utf-8", "ignore")
    return hashlib.blake2b(key, digest_size=8).hexdigest()

_PUBLISHER_DOMAIN_MAP = {
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

def _to_utc(dt: Optional[str]) -> datetime:
    if not dt:
        return datetime.now(timezone.utc)
    d = dateparser.parse(dt)
    return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)

def _publisher_from_entry(entry) -> Optional[str]:
    # Prefer <source><title>
    src = entry.get("source")
    if isinstance(src, dict):
        t = src.get("title")
        if t:
            return t.strip()
    # Fallback: last <font> tag in summary
    summary = entry.get("summary", "") or ""
    m = re.findall(r"<font[^>]*>([^<]+)</font>", summary, flags=re.I)
    return m[-1].strip() if m else None

def _domain_from_publisher(name: Optional[str]) -> str:
    if not name:
        return "google.com"
    name = name.strip()
    if name in _PUBLISHER_DOMAIN_MAP:
        return _PUBLISHER_DOMAIN_MAP[name]
    # If looks like a domain, normalize cheaply (no external deps)
    nm = name.lower().strip()
    if "." in nm and " " not in nm:
        if nm.startswith("www."):
            nm = nm[4:]
        return nm
    return "google.com"

class GoogleNewsFetcher:
    BASE = "https://news.google.com/rss/search"

    async def fetch(self, ticker: str, lookback_days: int) -> List[NewsItem]:
        params = urlencode({"q": f"{ticker} stock", "hl": "en-US", "gl": "US", "ceid": "US:en"})
        url = f"{self.BASE}?{params}"     # <-- encoded, no spaces

        feed = feedparser.parse(url)
        items: List[NewsItem] = []

        for e in feed.entries:
            published_at = _to_utc(e.get("published"))
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            summary = (e.get("summary") or "").strip()

            publisher = _publisher_from_entry(e)
            domain = _domain_from_publisher(publisher)
            nid = _make_id(link, title, published_at)
            items.append(
                NewsItem(
                    id=nid,                       # <-- set string id
                    source=domain,
                    title=title,
                    url=link,
                    published_at=published_at,
                    text=summary,
                    raw={"publisher": publisher, "google_rss": True},
                )
            )
        return items
