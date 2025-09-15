"""
File: app/main.py
Main FastAPI application and routing layer.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import SentimentResponse
from app.schemas import NewsItem
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

def calc_overall(items: list[NewsItem]) -> float:
    num = sum(getattr(it, "weighted_score", 0.0) for it in items)
    den = sum(getattr(it, "weight", 1.0) for it in items)
    return round(num / den, 4) if den else 0.0

def _attach_rationales(items: list[NewsItem], rationales: list[str] | None) -> None:
    if not items:
        return
    r = rationales or []
    for i, it in enumerate(items):
        it.rationale = (r[i].strip() if i < len(r) and isinstance(r[i], str) else it.rationale).strip()
        if not it.rationale:
            it.rationale = ""   # guarantee string

def to_response(
    ticker: str,
    items: list[NewsItem],
    rationales: list[str] | None,
    lookback_days: int,
):
    _attach_rationales(items, rationales)  # <- attach before building the response
    return SentimentResponse(
        ticker=ticker,
        as_of=now_utc().isoformat(),
        lookback_days=lookback_days,
        overall_score=calc_overall(items),
        n_items=len(items),
        items=items,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "as_of": now_utc().isoformat()}


@app.get("/sentiment", response_model=SentimentResponse)
async def sentiment(
    ticker: str = Query(..., min_length=1, max_length=10, description="Stock ticker, e.g., TSLA"),
    lookback_days: int = Query(DEFAULT_LOOKBACK_DAYS, ge=1, le=14),
    include_rationales: bool = Query(True, description="If False, doesn't call ChatGPT to explain each news."),
    limit: int = Query(10, ge=1, le=50),
):
    ticker = ticker.upper().strip()
    try:
        items = await collect_news(ticker, limit=limit, lookback_days=lookback_days)
        items = analyze_items(items)
        rationales: list[str] | None = None

        if include_rationales and items:
            rationales = await chatgpt_rationales(items, ticker)   # <-- pass ticker
            # EITHER attach to items here:
            _attach_rationales(items, rationales)
            # and then return without passing rationales:
            return to_response(ticker, items, lookback_days)
            # OR, if your to_response() does the attaching, keep your current call:
            # return to_response(ticker, items, rationales, lookback_days)

        if include_rationales and items:
            rationales = await chatgpt_rationales(items)

        # return to_response(ticker, items, rationales, lookback_days)  # <-- always return
        

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run locally with `python -m uvicorn app.main:app --reload --reload-dir app`
