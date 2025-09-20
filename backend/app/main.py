"""
Main FastAPI application and routing layer.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import DEFAULT_LOOKBACK_DAYS
from app.core.sentiment import analyze_items
from app.schemas import NewsItem, SentimentResponse
from app.sources.collector import collect_news
from app.services.rationales import chatgpt_rationales
from app.utils import now_utc

# Configure logging
logger = logging.getLogger("uvicorn")


def calculate_overall_sentiment(items: List[NewsItem]) -> float:
    """
    Calculate weighted average sentiment score across all news items.
    
    Args:
        items: List of NewsItem objects with sentiment analysis
        
    Returns:
        Overall sentiment score between -1.0 and 1.0
    """
    if not items:
        return 0.0
    
    numerator = sum(getattr(item, "weighted_score", 0.0) for item in items)
    denominator = sum(getattr(item, "weight", 1.0) for item in items)
    
    return round(numerator / denominator, 4) if denominator else 0.0


def attach_rationales_to_items(items: List[NewsItem], rationales: List[str] | None) -> None:
    """
    Attach AI-generated rationales to news items.
    
    Args:
        items: List of NewsItem objects
        rationales: List of rationale strings (can be None)
    """
    if not items:
        return
    
    rationale_list = rationales or []
    
    for i, item in enumerate(items):
        if i < len(rationale_list) and isinstance(rationale_list[i], str):
            item.rationale = rationale_list[i].strip()
        else:
            item.rationale = getattr(item, "rationale", "").strip()
        
        # Ensure rationale is always a string
        if not item.rationale:
            item.rationale = ""


def build_sentiment_response(
    ticker: str,
    items: List[NewsItem],
    rationales: List[str] | None,
    lookback_days: int,
) -> SentimentResponse:
    """
    Build the final API response with sentiment analysis results.
    
    Args:
        ticker: Stock ticker symbol
        items: List of analyzed NewsItem objects
        rationales: List of rationale strings
        lookback_days: Number of days looked back
        
    Returns:
        SentimentResponse object
    """
    # Attach rationales before building response
    attach_rationales_to_items(items, rationales)
    
    return SentimentResponse(
        ticker=ticker,
        as_of=now_utc().isoformat(),
        lookback_days=lookback_days,
        overall_score=calculate_overall_sentiment(items),
        n_items=len(items),
        items=items,
    )


# Initialize FastAPI app
app = FastAPI(
    title="Stock News Sentiment API",
    version="0.1.0",
    description="API for analyzing stock market sentiment from news articles"
)


@app.on_event("startup")
async def warm_startup():
    """Warm up the sentiment model on startup."""
    async def load_model():
        start_time = time.perf_counter()
        try:
            from app.core.sentiment import _load_model
            loop = asyncio.get_running_loop()
            # Load model in thread to avoid blocking startup
            await loop.run_in_executor(None, _load_model)
            logger.info("FinBERT model loaded in %.1fs", time.perf_counter() - start_time)
        except Exception as e:
            logger.warning("Model warm-up skipped: %s", e)
    
    # Start model loading in background
    asyncio.create_task(load_model())


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "as_of": now_utc().isoformat(),
        "service": "news-sentiment-api"
    }


@app.get("/sentiment", response_model=SentimentResponse)
async def get_sentiment_analysis(
    ticker: str = Query(..., min_length=1, max_length=10, description="Stock ticker symbol (e.g., TSLA)"),
    lookback_days: int = Query(DEFAULT_LOOKBACK_DAYS, ge=1, le=14, description="Days to look back for news"),
    include_rationales: bool = Query(True, description="Include AI-generated explanations"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of news items to analyze"),
):
    """
    Analyze sentiment for a stock ticker based on recent news.
    
    Args:
        ticker: Stock ticker symbol to analyze
        lookback_days: Number of days to look back for news
        include_rationales: Whether to include AI explanations
        limit: Maximum number of news items to analyze
        
    Returns:
        SentimentResponse with analysis results
    """
    # Normalize ticker
    ticker = ticker.upper().strip()
    
    try:
        # Collect news articles
        logger.info(f"Collecting news for {ticker}")
        items = await collect_news(ticker, limit=limit, lookback_days=lookback_days)
        
        if not items:
            logger.warning(f"No news items found for {ticker}")
            return build_sentiment_response(ticker, [], None, lookback_days)
        
        # Analyze sentiment
        logger.info(f"Analyzing sentiment for {len(items)} items")
        analyzed_items = analyze_items(items)
        
        # Generate rationales if requested
        rationales: List[str] | None = None
        if include_rationales and analyzed_items:
            logger.info("Generating rationales")
            rationales = await chatgpt_rationales(analyzed_items, ticker)
        
        # Build and return response
        return build_sentiment_response(ticker, analyzed_items, rationales, lookback_days)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing sentiment for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    # For development
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)