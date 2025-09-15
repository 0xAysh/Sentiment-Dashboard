# app/services/rationales.py
import os
import json
from typing import List
from textwrap import shorten

from app.schemas import NewsItem

# Optional: OpenAI client (support both async v1+ and absence)
try:
    from openai import AsyncOpenAI
    _openai_client = AsyncOpenAI()
    _has_openai = True
except Exception:
    _has_openai = False
    _openai_client = None


SYSTEM_PROMPT = (
    "You are a concise equity analyst. For each news item, write a 1–2 sentence rationale "
    "explaining *why* it is positive/neutral/negative for the given ticker. "
    "Be specific and use plain language. Do not include disclaimers."
)

def _fallback_rationales(items: List[NewsItem], ticker: str) -> List[str]:
    out = []
    for it in items:
        label = it.label.lower()
        title = shorten(it.title, width=140, placeholder="…")
        src = it.source
        if label == "positive":
            msg = f"Positive for {ticker}: {title}. Tone and content suggest supportive implications; source: {src}."
        elif label == "negative":
            msg = f"Negative for {ticker}: {title}. Tone and details imply headwinds/risks; source: {src}."
        else:
            msg = f"Mixed/neutral for {ticker}: {title}. Limited directional impact; source: {src}."
        out.append(msg)
    return out


async def chatgpt_rationales(items: List[NewsItem], ticker: str, model: str = "gpt-4o-mini") -> List[str]:
    """
    Always returns a list of len(items) with string rationales.
    Falls back to heuristics if GPT is unavailable or errors.
    """
    # If no OpenAI available or key is missing, fallback immediately
    if not _has_openai or not os.environ.get("OPENAI_API_KEY"):
        return _fallback_rationales(items, ticker)

    # Build compact payload for GPT
    compact_items = [
        {
            "title": it.title,
            "source": it.source,
            "published_at": it.published_at.isoformat(),
            "label": it.label,
            "score": round(it.score, 4),
            "weighted_score": round(it.weighted_score, 4),
            "url": it.url,
        }
        for it in items
    ]

    user_prompt = (
        f"Ticker: {ticker}\n\n"
        "Items (JSON):\n"
        + json.dumps(compact_items, ensure_ascii=False)
        + "\n\nReturn a JSON array of rationales (strings), one per item, same order. No extra text."
    )

    try:
        # Try chat.completions first (widely supported)
        resp = await _openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        content = resp.choices[0].message.content.strip()
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("GPT did not return a JSON array.")
        # Normalize length
        if len(data) < len(items):
            data += [""] * (len(items) - len(data))
        elif len(data) > len(items):
            data = data[: len(items)]
        # Ensure strings
        data = [str(x or "") for x in data]
        # If any are empty, patch with fallback for that slot
        patched = _fallback_rationales(items, ticker)
        data = [d if d.strip() else patched[i] for i, d in enumerate(data)]
        return data
         
    except Exception:
        # Any failure → safe fallback
        return _fallback_rationales(items, ticker)
