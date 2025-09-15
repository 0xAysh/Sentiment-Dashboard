"""
File: app/sources/reddit.py
Reddit search JSON fetcher (unauthenticated). For production, prefer OAuth API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from urllib.parse import urlencode

import httpx

from app.models import NewsItem
from app.utils import norm_text, make_id
from app.config import HEADERS


class RedditFetcher:
    async def fetch(self, ticker: str, lookback_days: int) -> List[NewsItem]:
        # Use a simple query; you can enrich with subreddit filters later
        q = f"{ticker} stock"
        url = "https://www.reddit.com/search.json?" + urlencode({"q": q, "sort": "new", "limit": 50})

        async with httpx.AsyncClient(headers=HEADERS, timeout=20) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()

        items: List[NewsItem] = []
        for child in data.get("data", {}).get("children", []):
            p = child.get("data", {})
            created_utc = p.get("created_utc")
            dt = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else datetime.now(timezone.utc)

            title = norm_text(p.get("title", ""))
            selftext = norm_text(p.get("selftext", ""))
            permalink = p.get("permalink", "")
            link = f"https://www.reddit.com{permalink}" if permalink else p.get("url", "")

            if not title or not link:
                continue

            items.append(
                NewsItem(
                    id=make_id("rd", str(p.get("id", link))),
                    source="reddit.com",
                    title=title,
                    url=link,
                    published_at=dt,
                    text=selftext or title,
                    raw={
                        "source": "reddit",
                        "ups": p.get("ups", 0),
                        "num_comments": p.get("num_comments", 0),
                        "subreddit": p.get("subreddit", ""),
                    },
                )
            )

        return items
