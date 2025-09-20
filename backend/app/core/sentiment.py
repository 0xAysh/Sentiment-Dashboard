"""
FinBERT-based sentiment analysis and weighting pipeline.

This module provides financial domain-specific sentiment analysis using the
FinBERT model with sophisticated multi-factor weighting for news importance.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from functools import lru_cache
from typing import List, Tuple

from app.config import (
    DEFAULT_SOURCE_WEIGHT,
    HALF_LIFE_HOURS,
    SOURCE_BASE_WEIGHTS,
)
from app.models import NewsItem
from app.utils import clamp_to_unit_range


@lru_cache(maxsize=1)
def _load_sentiment_model() -> Tuple:
    """
    Load the FinBERT sentiment analysis model.
    
    Returns:
        Tuple of (tokenizer, model) for sentiment analysis
        
    Raises:
        RuntimeError: If required dependencies are not installed
    """
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch
    except ImportError as e:
        raise RuntimeError(
            "Sentiment model dependencies are missing. Install transformers and torch.\n"
            "Try: pip install transformers && pip install --index-url https://download.pytorch.org/whl/cpu torch"
        ) from e

    model_name = "yiyanghkust/finbert-tone"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    
    return tokenizer, model


def analyze_sentiment_batch(texts: List[str]) -> List[Tuple[str, float, float, float, float]]:
    """
    Analyze sentiment for a batch of texts using FinBERT.
    
    Args:
        texts: List of text strings to analyze
        
    Returns:
        List of tuples: (label, p_pos, p_neu, p_neg, score)
        where score = p_pos - p_neg, clipped to [-1, 1]
    """
    if not texts:
        return []

    # Lazy imports to avoid startup overhead
    from transformers import AutoTokenizer
    import torch

    tokenizer, model = _load_sentiment_model()
    results: List[Tuple[str, float, float, float, float]] = []

    with torch.no_grad():
        # Process in batches of 16 for memory efficiency
        for i in range(0, len(texts), 16):
            batch = texts[i : i + 16]
            
            # Tokenize batch
            encoded = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt"
            )
            
            # Get model predictions
            logits = model(**encoded).logits
            probabilities = torch.softmax(logits, dim=-1).cpu().numpy()
            
            # Process each item in the batch
            # FinBERT label order: [neutral, positive, negative]
            for prob in probabilities:
                p_neutral, p_positive, p_negative = float(prob[0]), float(prob[1]), float(prob[2])
                
                # Calculate sentiment score
                score = max(-1.0, min(1.0, p_positive - p_negative))
                
                # Determine label based on highest probability
                if p_positive > max(p_neutral, p_negative):
                    label = "positive"
                elif p_negative > max(p_positive, p_neutral):
                    label = "negative"
                else:
                    label = "neutral"
                
                results.append((label, p_positive, p_neutral, p_negative, score))
    
    return results


def calculate_recency_weight(published_at: datetime) -> float:
    """
    Calculate recency weight using exponential decay.
    
    Args:
        published_at: Publication timestamp
        
    Returns:
        Weight between 0.0 and 1.0 (higher for newer news)
    """
    age_hours = max(0.0, (datetime.now(timezone.utc) - published_at).total_seconds() / 3600.0)
    decay_factor = 2 ** (-(age_hours / max(1e-6, HALF_LIFE_HOURS)))
    return clamp_to_unit_range(decay_factor)


def calculate_source_weight(domain: str) -> float:
    """
    Calculate source credibility weight based on domain.
    
    Args:
        domain: News source domain
        
    Returns:
        Weight between 0.0 and 1.0 (higher for more credible sources)
    """
    weight = SOURCE_BASE_WEIGHTS.get(domain, DEFAULT_SOURCE_WEIGHT)
    return clamp_to_unit_range(weight)


def calculate_engagement_weight(item: NewsItem) -> float:
    """
    Calculate engagement weight based on user interaction.
    
    Args:
        item: NewsItem with raw metadata
        
    Returns:
        Weight between 0.0 and 1.0 (higher for more engaging content)
    """
    if item.source == "reddit.com":
        # Use upvotes and comments for Reddit posts
        upvotes = int(item.raw.get("ups", 0) or 0)
        comments = int(item.raw.get("num_comments", 0) or 0)
        
        # Logarithmic scaling to prevent extreme values
        raw_score = math.log1p(upvotes) + 0.5 * math.log1p(comments)
        return clamp_to_unit_range(raw_score / 10.0)
    
    # Default engagement for articles
    return 0.5


def combine_weights(recency_weight: float, source_weight: float, engagement_weight: float) -> float:
    """
    Combine individual weights into a final importance score.
    
    Args:
        recency_weight: Weight based on news age
        source_weight: Weight based on source credibility
        engagement_weight: Weight based on user engagement
        
    Returns:
        Combined weight between 0.0 and 1.0
    """
    # Weighted combination: 50% recency, 30% source, 20% engagement
    combined = 0.5 * recency_weight + 0.3 * source_weight + 0.2 * engagement_weight
    return clamp_to_unit_range(combined)


def analyze_news_items(items: List[NewsItem]) -> List[NewsItem]:
    """
    Perform complete sentiment analysis and weighting on news items.
    
    Args:
        items: List of NewsItem objects to analyze
        
    Returns:
        List of NewsItem objects with sentiment analysis and weights applied
    """
    if not items:
        return []

    # Prepare texts for sentiment analysis
    texts = [f"{item.title}. {item.text}".strip() for item in items]

    # Analyze sentiment for all items
    sentiment_results = analyze_sentiment_batch(texts)

    # Apply sentiment analysis and weights to each item
    for item, (label, p_positive, p_neutral, p_negative, score) in zip(items, sentiment_results):
        # Set sentiment analysis results
        item.label = label
        item.prob_positive = p_positive
        item.prob_neutral = p_neutral
        item.prob_negative = p_negative
        item.score = score

        # Calculate individual weights
        recency_w = calculate_recency_weight(item.published_at)
        source_w = calculate_source_weight(item.source)
        engagement_w = calculate_engagement_weight(item)

        # Store individual weights
        item.recency_w = recency_w
        item.source_w = source_w
        item.engage_w = engagement_w

        # Calculate combined weight and weighted score
        item.weight = combine_weights(recency_w, source_w, engagement_w)
        item.weighted_score = (item.weight or 0.0) * (item.score or 0.0)

    return items


# Backward compatibility alias
analyze_items = analyze_news_items