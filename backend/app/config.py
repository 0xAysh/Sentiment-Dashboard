"""
Application configuration with environment variable support.
"""
from __future__ import annotations

import os
from typing import Dict


def _get_env_float(key: str, default: float) -> float:
    """Get float value from environment variable with fallback."""
    try:
        return float(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


def _get_env_int(key: str, default: int) -> int:
    """Get integer value from environment variable with fallback."""
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


def _get_env_list(key: str, default: list[str], separator: str = ",") -> list[str]:
    """Get list value from environment variable with fallback."""
    value = os.getenv(key)
    if not value:
        return default
    return [item.strip() for item in value.split(separator) if item.strip()]


# API Configuration
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# News Collection Settings
DEFAULT_LOOKBACK_DAYS: int = _get_env_int("LOOKBACK_DAYS", 5)
MAX_ITEMS: int = _get_env_int("MAX_ITEMS", 40)

# Sentiment Analysis Settings
HALF_LIFE_HOURS: float = _get_env_float("HALF_LIFE_HOURS", 24.0)
DEFAULT_SOURCE_WEIGHT: float = _get_env_float("DEFAULT_SOURCE_WEIGHT", 0.75)

# Source Credibility Weights (0.0 to 1.0)
# Higher values indicate more credible sources
SOURCE_BASE_WEIGHTS: Dict[str, float] = {
    # Tier 1: Premium Financial News (0.95-1.00)
    "reuters.com": 1.00,
    "bloomberg.com": 0.97,
    "wsj.com": 0.95,
    "ft.com": 0.95,
    
    # Tier 2: Major Financial News (0.85-0.92)
    "cnbc.com": 0.92,
    "seekingalpha.com": 0.85,
    "marketwatch.com": 0.85,
    "barrons.com": 0.85,
    
    # Tier 3: General Financial News (0.70-0.80)
    "yahoo.com": 0.80,
    "finance.yahoo.com": 0.85,
    "investopedia.com": 0.80,
    "benzinga.com": 0.75,
    "fool.com": 0.70,
    "businessinsider.com": 0.75,
    "simplywall.st": 0.70,
    
    # Tier 4: Lower Credibility Sources (0.60-0.70)
    "msn.com": 0.60,
    "marketbeat.com": 0.60,
    "coincentral.com": 0.60,
}

# HTTP Client Configuration
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
HTTP_HEADERS = {"User-Agent": USER_AGENT}

# CORS Configuration
CORS_ALLOW_ORIGINS: list[str] = _get_env_list("CORS_ALLOW_ORIGINS", ["*"])

# Logging Configuration
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = os.getenv(
    "LOG_FORMAT", 
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)