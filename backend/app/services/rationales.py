# services/rationales.py
import os, logging
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
APIKEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=APIKEY) if APIKEY else None

SYSTEM = (
    "You are a financial news analyst. For each item, write a concise 1–2 sentence "
    "rationale explaining why the article is positive/negative/neutral for the ticker. "
    "No fluff, no emojis."
)

def _prompt(item) -> str:
    # Keep it short; the model just needs enough context
    body = (item.text or "")[:900]
    return (
        f"Title: {item.title}\n"
        f"Source: {item.source}\n"
        f"Excerpt: {body}\n\n"
        f"Label: {item.label}\n"
        "Write a 1–2 sentence rationale."
    )

async def chatgpt_rationales(items: List["schemas.NewsItem"]) -> List[Optional[str]]:
    if not client:
        logger.warning("Rationales disabled: no OPENAI_API_KEY in env.")
        return [None] * len(items)

    outs: List[Optional[str]] = []
    for it in items:
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                temperature=0.2,
                max_tokens=120,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": _prompt(it)},
                ],
            )
            text = (resp.choices[0].message.content or "").strip()
            outs.append(text or None)
        except Exception as e:
            logger.exception("Rationale error for %s (%s): %s", it.id, it.source, e)
            outs.append(None)
    logger.info("Rationales generated: %d/%d non-null", sum(1 for x in outs if x), len(outs))
    return outs
