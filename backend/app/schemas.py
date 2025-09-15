from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

class SentimentItem(BaseModel):
    id: str
    source: str
    title: str
    url: str
    published_at: datetime
    text: str
    label: str
    prob_positive: float
    prob_neutral: float
    prob_negative: float
    score: float
    weight: float
    weighted_score: float
    rationale: Optional[str] = None

class SentimentResponse(BaseModel):
    ticker: str
    as_of: datetime
    lookback_days: int
    overall_score: float
    n_items: int
    items: List[SentimentItem]
