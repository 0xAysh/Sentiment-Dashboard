"""
File: app/services/rationales.py
Optional: generate LLM rationales for each news item.
Requires OPENAI_API_KEY in environment.
"""

from __future__ import annotations

from typing import List, Optional

from app.models import NewsItem
from app.config import OPENAI_API_KEY


async def chatgpt_rationales(items: List[NewsItem]) -> List[Optional[str]]:
    """Return 2–3 sentence rationale per item, or None if disabled/error.

    This runs sequentially to keep things simple. You can parallelize with
    care about rate limits. Uses OpenAI Responses API (fallback to Chat Completions).
    """
    if not OPENAI_API_KEY:
        return [None for _ in items]

    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)

        outs: List[Optional[str]] = []
        for it in items:
            prompt = (
                "You are a finance analyst. Given the news headline, snippet, date, "
                "and a model's sentiment probabilities, write a 2-3 sentence rationale "
                "explaining why the sentiment is positive, neutral, or negative for the stock. "
                "Avoid price targets or investment advice.\n\n"
                f"Title: {it.title}\n"
                f"Snippet: {it.text}\n"
                f"Published (UTC): {it.published_at.isoformat()}\n"
                f"Model probs — positive: {it.prob_positive:.3f}, neutral: {it.prob_neutral:.3f}, negative: {it.prob_negative:.3f}\n"
                f"Model score [-1..1]: {it.score:.3f}\n"
            )
            try:
                resp = client.responses.create(
                    model="gpt-4o-mini",
                    input=[{"role": "user", "content": prompt}],
                )
                text = resp.output_text  # type: ignore[attr-defined]
            except Exception:
                chat = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=160,
                )
                text = chat.choices[0].message.content  # type: ignore

            outs.append((text or "").strip())

        return outs

    except Exception:
        # Fail open (no rationales) if OpenAI is unavailable
        return [None for _ in items]
