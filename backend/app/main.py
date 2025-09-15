"""
File: app/main.py
Main FastAPI application and routing layer.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import SentimentResponse
from app.sources.collector import collect_news
from app.core.sentiment import analyze_items
from app.services.rationales import chatgpt_rationales
from app.utils import now_utc, to_response
from app.config import DEFAULT_LOOKBACK_DAYS

# --- FastAPI app ---
app = FastAPI(title="Stock News Sentiment API", version="0.1.0")

# Enable CORS for UI consumption
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "as_of": now_utc().isoformat()}


@app.get("/sentiment", response_model= SentimentResponse)
async def sentiment(
    ticker: str = Query(..., min_length=1, max_length=10, description="Stock ticker, e.g., TSLA"),
    lookback_days: int = Query(DEFAULT_LOOKBACK_DAYS, ge=1, le=14),
    include_rationales: bool = Query(False, description="If true, calls ChatGPT to explain each news."),
    limit: int = Query(10, ge=1, le=50)
):
    ticker = ticker.upper().strip()
    try:
        items = await collect_news(ticker, lookback_days, limit)
        items = analyze_items(items)
        rationals = None
        if include_rationales and items:
            rationals = await chatgpt_rationales(items)
        return to_response(ticker, items, rationals, lookback_days)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run locally with `python -m uvicorn app.main:app --reload`
