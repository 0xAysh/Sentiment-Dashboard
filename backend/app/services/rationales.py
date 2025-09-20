"""
AI-powered rationale generation for sentiment analysis results.
"""
from __future__ import annotations

import json
import os
from textwrap import shorten
from typing import List

from app.schemas import NewsItem

# OpenAI client setup with graceful fallback
try:
    from openai import AsyncOpenAI
    _has_openai = True
except ImportError:
    _has_openai = False
    AsyncOpenAI = None


def _get_openai_client():
    """Get OpenAI client only when needed and API key is available."""
    if not _has_openai or not os.environ.get("OPENAI_API_KEY"):
        return None
    return AsyncOpenAI()


SYSTEM_PROMPT = (
    "You are a financial analyst. For each news item, write a 2-3 sentence rationale "
    "explaining *why* it is positive/neutral/negative for the given ticker. "
    "Be specific and use plain language. Do not include disclaimers."
)


def generate_fallback_rationales(items: List[NewsItem], ticker: str) -> List[str]:
    """
    Generate fallback rationales using rule-based templates.
    
    Args:
        items: List of NewsItem objects
        ticker: Stock ticker symbol
        
    Returns:
        List of rationale strings
    """
    rationales = []
    
    for item in items:
        label = item.label.lower()
        title = shorten(item.title, width=140, placeholder="…")
        source = item.source
        
        if label == "positive":
            rationale = f"Positive for {ticker}: {title}. Tone and content suggest supportive implications; source: {source}."
        elif label == "negative":
            rationale = f"Negative for {ticker}: {title}. Tone and details imply headwinds/risks; source: {source}."
        else:
            rationale = f"Mixed/neutral for {ticker}: {title}. Limited directional impact; source: {source}."
        
        rationales.append(rationale)
    
    return rationales


async def generate_ai_rationales(
    items: List[NewsItem], 
    ticker: str, 
    model: str = "gpt-4o-mini"
) -> List[str]:
    """
    Generate AI-powered rationales using OpenAI's API.
    
    Args:
        items: List of NewsItem objects
        ticker: Stock ticker symbol
        model: OpenAI model to use
        
    Returns:
        List of rationale strings (same length as items)
    """
    # Get OpenAI client (returns None if not available)
    client = _get_openai_client()
    if not client:
        return generate_fallback_rationales(items, ticker)

    # Prepare compact data for AI processing
    compact_items = [
        {
            "title": item.title,
            "source": item.source,
            "published_at": item.published_at.isoformat(),
            "label": item.label,
            "score": round(item.score, 4),
            "weighted_score": round(item.weighted_score, 4),
            "url": item.url,
        }
        for item in items
    ]

    user_prompt = (
        f"Ticker: {ticker}\n\n"
        "Items (JSON):\n"
        + json.dumps(compact_items, ensure_ascii=False)
        + "\n\nReturn a JSON array of rationales (strings), one per item, same order. No extra text."
    )

    try:
        # Call OpenAI API
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        
        # Validate response format
        if not isinstance(data, list):
            raise ValueError("AI did not return a JSON array")
        
        # Normalize length to match input items
        if len(data) < len(items):
            data.extend([""] * (len(items) - len(data)))
        elif len(data) > len(items):
            data = data[:len(items)]
        
        # Ensure all elements are strings
        data = [str(x or "") for x in data]
        
        # Fill empty rationales with fallback
        fallback_rationales = generate_fallback_rationales(items, ticker)
        data = [rationale if rationale.strip() else fallback_rationales[i] 
                for i, rationale in enumerate(data)]
        
        return data
        
    except Exception as e:
        print(f"Error generating AI rationales: {e}")
        # Fallback to rule-based rationales
        return generate_fallback_rationales(items, ticker)


# Backward compatibility alias
chatgpt_rationales = generate_ai_rationales