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
import asyncio, logging, time


log = logging.getLogger("uvicorn")

# --- FastAPI app ---
app = FastAPI(title="Stock News Sentiment API", version="0.1.0")

@app.on_event("startup")
async def _warm_start():
    async def _warm():
        t0 = time.perf_counter()
        try:
            from app.core.sentiment import _load_model
            loop = asyncio.get_running_loop()
            # run sync _load_model() in a thread so startup doesn't block
            await loop.run_in_executor(None, _load_model)
            log.info("FinBERT warm-load done in %.1fs", time.perf_counter() - t0)
        except Exception as e:
            log.warning("Warm-load skipped: %s", e)
    # fire-and-forget, don't block startup
    asyncio.create_task(_warm())

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

        rationales: list[str] = []
        if include_rationales and items:
            rationales = await chatgpt_rationales(items, ticker)  # returns list[str] with fallback
            
        return to_response(ticker, items, rationales, lookback_days)
        

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run locally with `python -m uvicorn app.main:app --reload --reload-dir app`
