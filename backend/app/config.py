"""
File: app/config.py
Centralized configuration (env-driven with sensible defaults).
Move/replace your old root-level config.py with this module.
"""

from __future__ import annotations

import os
from typing import Dict

# --- Env helpers -----------------------------------------------------------

def _getenv_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except Exception:
        return default


def _getenv_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except Exception:
        return default


# --- Public settings -------------------------------------------------------

# Optional: enables ChatGPT rationales when provided
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# News collection
DEFAULT_LOOKBACK_DAYS: int = _getenv_int("LOOKBACK_DAYS", 5)
MAX_ITEMS: int = _getenv_int("MAX_ITEMS", 40)

# Weighting
HALF_LIFE_HOURS: float = _getenv_float("HALF_LIFE_HOURS", 24.0)
DEFAULT_SOURCE_WEIGHT: float = _getenv_float("DEFAULT_SOURCE_WEIGHT", 0.75)

# Domain base weights (0..1). Override/add via env if needed.
# You can also split this into a JSON env var later for ops needs.
SOURCE_BASE_WEIGHTS: Dict[str, float] = {
    "reuters.com": 1.00,
    "bloomberg.com": 0.97,
    "wsj.com": 0.95,
    "ft.com": 0.95,
    "cnbc.com": 0.92,
    "seekingalpha.com": 0.85,
    "marketwatch.com": 0.85,
    "yahoo.com": 0.80,
    "investopedia.com": 0.80,
    "reddit.com": 0.65,
}

# HTTP client headers
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}

# CORS (simple default: allow all; lock down in prod via env list)
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
