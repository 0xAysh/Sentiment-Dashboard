"""
File: app/core/sentiment.py
FinBERT-based sentiment scoring and weighting pipeline.

This version **lazy-imports** heavy libs (torch/transformers) so the API can start
even if those packages aren't installed yet. You'll only need them when the
first sentiment call is made.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Tuple
from datetime import datetime, timezone
import math

from app.models import NewsItem
from app.utils import clamp01
from app.config import (
    HALF_LIFE_HOURS,
    SOURCE_BASE_WEIGHTS,
    DEFAULT_SOURCE_WEIGHT,
)


# --- Model loading ---------------------------------------------------------
@lru_cache(maxsize=1)
def _load_model():
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification  # type: ignore
        import torch  # noqa: F401  # ensure torch is importable
    except Exception as e:
        raise RuntimeError(
            "Sentiment model dependencies are missing. Install transformers and torch.\n"
            "Try: pip install transformers && pip install --index-url https://download.pytorch.org/whl/cpu torch"
        ) from e

    model_name = "yiyanghkust/finbert-tone"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    return tokenizer, model


# --- Sentiment inference ---------------------------------------------------

def finbert_sentiment(texts: List[str]) -> List[Tuple[str, float, float, float, float]]:
    """
    For each text, returns tuple: (label, p_pos, p_neu, p_neg, score)
    where score = p_pos - p_neg, clipped to [-1, 1].
    """
    if not texts:
        return []

    # Lazy imports here as well
    from transformers import AutoTokenizer  # type: ignore  # noqa: F401
    import torch  # type: ignore

    tokenizer, model = _load_model()
    results: List[Tuple[str, float, float, float, float]] = []

    with torch.no_grad():
        for i in range(0, len(texts), 16):
            batch = texts[i : i + 16]
            enc = tokenizer(batch, padding=True, truncation=True, max_length=256, return_tensors="pt")
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            # FinBERT label order: [neutral, positive, negative]
            for p in probs:
                p_neu, p_pos, p_neg = float(p[0]), float(p[1]), float(p[2])
                score = max(-1.0, min(1.0, p_pos - p_neg))
                if p_pos > max(p_neu, p_neg):
                    label = "positive"
                elif p_neg > max(p_pos, p_neu):
                    label = "negative"
                else:
                    label = "neutral"
                results.append((label, p_pos, p_neu, p_neg, score))
    return results


# --- Weighting functions ---------------------------------------------------

def recency_weight(published_at: datetime) -> float:
    """Exponential decay by half-life in hours."""
    age_hours = max(0.0, (datetime.now(timezone.utc) - published_at).total_seconds() / 3600.0)
    return clamp01(2 ** (-(age_hours / max(1e-6, HALF_LIFE_HOURS))))


def source_weight(domain: str) -> float:
    return clamp01(SOURCE_BASE_WEIGHTS.get(domain, DEFAULT_SOURCE_WEIGHT))


def engagement_weight(item: NewsItem) -> float:
    if item.source == "reddit.com":
        ups = int(item.raw.get("ups", 0) or 0)
        com = int(item.raw.get("num_comments", 0) or 0)
        raw = math.log1p(ups) + 0.5 * math.log1p(com)
        return clamp01(raw / 10.0)
    # Articles: baseline engagement
    return 0.5


def combine_weights(rw: float, sw: float, ew: float) -> float:
    # convex combination, sums to 1 with our coefficients
    return clamp01(0.5 * rw + 0.3 * sw + 0.2 * ew)


# --- Main analysis ---------------------------------------------------------

def analyze_items(items: List[NewsItem]) -> List[NewsItem]:
    if not items:
        return []

    texts = [f"{it.title}. {it.text}".strip() for it in items]

    sentiments = finbert_sentiment(texts)

    for it, (label, p_pos, p_neu, p_neg, score) in zip(items, sentiments):
        it.label = label
        it.prob_positive = p_pos
        it.prob_neutral = p_neu
        it.prob_negative = p_neg
        it.score = score

        rw = recency_weight(it.published_at)
        sw = source_weight(it.source)
        ew = engagement_weight(it)
        it.recency_w, it.source_w, it.engage_w = rw, sw, ew
        it.weight = combine_weights(rw, sw, ew)
        it.weighted_score = (it.weight or 0.0) * (it.score or 0.0)

    return items
