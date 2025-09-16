# app/schemas.py
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any

class NewsItem(BaseModel):
    id: str                                  # required string
    source: str
    title: str
    url: str
    published_at: datetime
    text: str = ""                            # fine to default to empty
    label: Literal["positive", "neutral", "negative"]
    prob_positive: float
    prob_neutral: float
    prob_negative: float
    score: float
    weight: float
    weighted_score: float
    rationale: str = Field(default="")                       # <-- non-optional, always a string
    raw: Optional[Dict[str, Any]] = None

class SentimentResponse(BaseModel):
    ticker: str
    as_of: str
    lookback_days: int
    overall_score: float
    n_items: int
    items: list[NewsItem]
