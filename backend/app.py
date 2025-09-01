from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from typing import List, Dict
from fastapi import Query
import httpx
from datetime import datetime, timedelta
from fastapi import HTTPException

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
async def analyze(
    ticker: str = Query(..., min_length=1, max_length=10),
    windowHours: int = Query(settings.WINDOW_HOURS, ge=1, le=72),
    limit: int = Query(10, ge=3, le=30)
) -> Dict:
    try:
        articles = await fetch_news(ticker, windowHours, limit)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"NewsAPI error: {e.response.text[:200]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    items = []
    for i, a in enumerate(articles[:limit]):
        title = a.get("title") or ""
        url = a.get("url") or ""
        domain = (url.split("/")[2] if "//" in url else "").replace("www.", "")
        published_at = a.get("publishedAt") or ""

        # temporary heuristic score; we'll swap to LLM next
        lower = title.lower()
        score = 0.0
        if any(w in lower for w in ["beat", "record", "upgrade", "surge", "growth"]):
            score = 0.6
        if any(w in lower for w in ["miss", "downgrade", "lawsuit", "drop", "delay"]):
            score = -0.6

        items.append({
            "id": f"news-{i}",
            "source": "news",
            "domain": domain or a.get("source", {}).get("name", ""),
            "title": title,
            "url": url,
            "publishedAt": published_at,
            "score": round(score, 2),
            "rationale": "Keyword placeholder; LLM next"
        })

    overall = round(sum(i["score"] for i in items)/len(items), 2) if items else 0.0

    return {
        "ticker": ticker.upper(),
        "windowHours": windowHours,
        "overall": overall,
        "confidence": 0.8,  # placeholder
        "reasons": ["NewsAPI integrated; scoring is temporary"],
        "items": items
    }