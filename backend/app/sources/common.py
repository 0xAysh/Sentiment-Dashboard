"""
Common utilities for news source fetchers.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from dateutil import parser as dateparser


def make_news_id(url: str, title: str, published_at: datetime) -> str:
    """
    Generate a deterministic unique ID for a news item.
    
    Args:
        url: News article URL
        title: News article title
        published_at: Publication timestamp
        
    Returns:
        16-character hexadecimal string ID
    """
    key = f"{url}|{title}|{published_at.isoformat()}".encode("utf-8", "ignore")
    return hashlib.blake2b(key, digest_size=8).hexdigest()


def parse_utc_datetime(date_string: Optional[str]) -> datetime:
    """
    Parse a date string and convert to UTC datetime.
    
    Args:
        date_string: Date string in various formats, or None
        
    Returns:
        UTC datetime object, or current UTC time if input is None/empty
    """
    if not date_string:
        return datetime.now(timezone.utc)
    
    parsed_date = dateparser.parse(date_string)
    if parsed_date.tzinfo:
        return parsed_date.astimezone(timezone.utc)
    else:
        return parsed_date.replace(tzinfo=timezone.utc)


def clean_text(text: Optional[str]) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text string or None
        
    Returns:
        Cleaned text string, empty string if input is None
    """
    if not text:
        return ""
    return text.strip()


def extract_domain_from_url(url: str) -> str:
    """
    Extract domain from URL, handling common variations.
    
    Args:
        url: Full URL string
        
    Returns:
        Normalized domain name
    """
    if not url:
        return "unknown.com"
    
    # Remove protocol and path
    domain = url.replace("https://", "").replace("http://", "").split("/")[0]
    
    # Remove www prefix
    if domain.startswith("www."):
        domain = domain[4:]
    
    return domain.lower()
