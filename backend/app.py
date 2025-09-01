from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from typing import List, Dict
from fastapi import Query
import httpx
from datetime import datetime, timedelta

app = FastAPI(title="Sentiment v1 — News+Reddit")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

@app.get("/health")
def health():
    return {"ok": True, "window_hours": settings.WINDOW_HOURS}

NEWSAPI_URL = "https://newsapi.org/v2/everything"

def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"

async def fetch_news(ticker: str, window_hours: int, limit: int):
    if not settings.NEWSAPI_KEY:
        # fall back to stub if no key
        return [{
            "title": f"{ticker} beats earnings expectations",
            "url": "https://example.com/a",
            "source": {"name": "Example"},
            "publishedAt": datetime.utcnow().isoformat() + "Z",
        }]

    to_dt = datetime.utcnow()
    from_dt = to_dt - timedelta(hours=window_hours)
    params = {
        "q": ticker,
        "from": iso(from_dt),
        "to": iso(to_dt),
        "language": "en",
        "pageSize": min(limit, 50),
        "sortBy": "publishedAt",
        "apiKey": settings.NEWSAPI_KEY,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(NEWSAPI_URL, params=params)
        r.raise_for_status()
        data = r.json()
        return data.get("articles", [])

@app.get("/analyze")
def analyze(ticker: str = Query(..., min_length=1, max_length=10),
            windowHours: int = Query(settings.WINDOW_HOURS, ge=1, le=72),
            limit: int = Query(10, ge=3, le=30)) -> Dict:
    items = [
        {
            "id": "news-0",
            "source": "news",
            "domain": "example.com",
            "title": f"{ticker} beats earnings expectations",
            "url": "https://example.com/a",
            "publishedAt": "2025-08-31T00:00:00Z",
            "score": 0.6,
            "rationale": "Placeholder"
        }
    ]
    overall = round(sum(i["score"] for i in items)/len(items), 2)
    return {
        "ticker": ticker.upper(),
        "windowHours": windowHours,
        "overall": overall,
        "confidence": 0.8,
        "reasons": ["Stub data — will replace with NewsAPI + LLM"],
        "items": items
    }