from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from typing import List, Dict
from fastapi import Query
import httpx
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
import asyncio, json
from fastapi import HTTPException
from openai import OpenAI
import traceback
def log_err(prefix: str, e: Exception):
    print(f"[ERROR] {prefix}: {type(e).__name__}: {e}")
    traceback.print_exc()


client = OpenAI(api_key=settings.OPENAI_API_KEY)

# --- Reddit OAuth + fetch ---------------------------------
REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"
REDDIT_SEARCH_URL = "https://oauth.reddit.com/search"

# simple in-memory cache for the bearer token
_reddit_token = {"value": None, "expires_at": 0.0}

async def reddit_token():
    """Get (and cache) an app-only bearer token."""
    import time, base64
    now = time.time()
    if _reddit_token["value"] and _reddit_token["expires_at"] - now > 60:
        return _reddit_token["value"]

    auth = (settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET)
    data = {"grant_type": "client_credentials"}
    headers = {"User-Agent": settings.REDDIT_USER_AGENT or "sentiment-app/0.1"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(REDDIT_AUTH_URL, data=data, auth=auth, headers=headers)
        r.raise_for_status()
        tok = r.json()
        access_token = tok["access_token"]
        expires_in = tok.get("expires_in", 3600)
        _reddit_token["value"] = access_token
        _reddit_token["expires_at"] = now + expires_in
        return access_token

async def fetch_reddit(ticker: str, window_hours: int, limit: int):
    """
    Fetch recent Reddit posts matching the ticker (titles/selftext) from finance subs.
    Returns a list shaped like NewsAPI articles: title, description, url, source{name}, publishedAt.
    """
    token = await reddit_token()
    to_dt = datetime.now(timezone.utc)
    from_dt = to_dt - timedelta(hours=window_hours)

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": settings.REDDIT_USER_AGENT or "sentiment-app/0.1",
    }

    # Search ONLY finance subs via lucene; match in title OR body
    subs = "(subreddit:stocks OR subreddit:investing OR subreddit:wallstreetbets)"
    q = f'({subs}) AND (title:"{ticker}" OR selftext:"{ticker}")'

    params = {
        "q": q,
        "syntax": "lucene",
        "sort": "new",
        "limit": min(limit, 50),
        "restrict_sr": False,           # searching multi-subs via query
        "include_over_18": "off",
        "type": "link,self",
        "t": "week",
    }


    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        r = await client.get(REDDIT_SEARCH_URL, params=params)
        r.raise_for_status()
        data = r.json()

    items = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        created_utc = d.get("created_utc")
        if not created_utc:
            continue
        published = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        if published < from_dt:
            continue

        title = d.get("title") or ""
        body = d.get("selftext") or ""
        url = "https://reddit.com" + (d.get("permalink") or "/")
        subreddit = d.get("subreddit") or "reddit"

        items.append({
            "title": title,
            "description": (body)[:400],
            "url": url,
            "source": {"name": subreddit},
            "publishedAt": published.replace(microsecond=0).isoformat() + "Z",
        })

    return items[:limit]


SYSTEM_PROMPT = ("""
    You are a cautious but decisive financial news sentiment rater. 
    Use the web_search Tool to go on relevent sites to gain more context and information.

    Output ONLY valid JSON in the format:
    {
    "score": number between -1 and 1,
    "rationale": string (<= 25 words)
    }

    Scoring rules:
    - +1.0 = extremely bullish (strong positive news for stock price)
    - 0.0 = neutral / unclear
    - -1.0 = extremely bearish (strong negative news for stock price)
    - Use intermediate values (e.g. +0.3, -0.4, +0.6) for mixed or moderate signals.
    - Favor small non-zero scores (-0.3 to +0.3) instead of always defaulting to 0 when sentiment is weak but leaning.

    Guidelines:
    - Consider earnings, revenue, guidance, analyst ratings, regulation, lawsuits, partnerships, product launches, competition.
    - If news is only indirectly related (mentions rivals, industry shifts), still give a mild score instead of 0.0.
    - Ignore celebrity, rumor, or unrelated entertainment news (score = 0.0).
    - Be consistent: neutral if irrelevant, otherwise lean slightly positive/negative instead of collapsing to zero.

    """
    )

async def llm_score(title: str, text: str, source: str, ticker: str, published_at: str):
    """
    Returns (score: float in [-1,1], rationale: str). Never returns None.
    """
    if not settings.OPENAI_API_KEY:
        return 0.0, "No LLM key; neutral"  

    def _call():
        resp = client.chat.completions.create(
            model="gpt-5",
            tools=[
                {
                "type": "web_search",
                "filters": {
                "allowed_domains": [
                    "https://www.reddit.com/r/investing/",
                    "https://www.reddit.com/r/StockMarket/",
                    "https://www.reddit.com/r/stocks/",
                    "https://www.reddit.com/r/finance/",
                    "https://finance.yahoo.com/",
                    "https://www.wsj.com/",
                    "https://www.cnbc.com/2025/08/28/stock-market-today-live-updates-.html",
                    "https://www.ainvest.com/",
                    "https://www.marketwatch.com/",
                    "https://www.liberatedstocktrader.com/"]}}],
            reasoning={"effort": "high"},
            include=["web_search_call.action.sources"],
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content":
                    f"ITEM:\n"
                    f"Title: {title}\n"
                    f"Snippet: {text}\n"
                    f"Source: {source}\n"
                    f"Ticker: {ticker}\n"
                    f"Date: {published_at}"
                },
            ],
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except Exception:
            data = {}
        s = float(data.get("score", 0.0))
        r = str(data.get("rationale", ""))[:120] or "No rationale"
        s = max(-1.0, min(1.0, s))
        return s, r

    try:
        return await asyncio.to_thread(_call)
    except Exception as e:
        return 0.0, f"LLM error → neutral ({type(e).__name__})"



app = FastAPI(title="Sentiment v1 — News+Reddit")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

@app.get("/health")
def health():
    return {"ok": True, "window_hours": settings.WINDOW_HOURS}

NEWSAPI_URL = "https://newsapi.org/v2/everything"


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"

async def fetch_news(ticker: str, window_hours: int, limit: int):
    if not settings.NEWSAPI_KEY:
        # fall back to stub if no key
        return [{
            "title": f"{ticker} beats earnings expectations",
            "url": "https://example.com/a",
            "source": {"name": "Example"},
            "publishedAt": datetime.utcnow().isoformat() + "Z",
        }]

    to_dt = datetime.utcnow()
    from_dt = to_dt - timedelta(hours=window_hours)

    async def _newsapi(params):
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(NEWSAPI_URL, params=params)
            r.raise_for_status()
            return r.json().get("articles", [])

    def _iso(dt):  # local helper to avoid confusion
        return dt.replace(microsecond=0).isoformat() + "Z"

    to_dt = datetime.utcnow()
    from_dt = to_dt - timedelta(hours=window_hours)

    name = {"AAPL":"Apple","MSFT":"Microsoft","NVDA":"Nvidia","AMZN":"Amazon","META":"Meta","GOOGL":"Google"}.get(ticker.upper(), "")
    title_filter = f"\"{ticker}\"" + (f" OR \"{name}\"" if name else "")

    name = {"AAPL":"Apple","MSFT":"Microsoft","NVDA":"Nvidia","AMZN":"Amazon","META":"Meta","GOOGL":"Google"}.get(ticker.upper(), "")
    title_filter = f"\"{ticker}\"" + (f" OR \"{name}\"" if name else "")

    # TIER 1 — title must contain ticker OR name; search title+desc
    params1 = {
        "q": f"{ticker} OR {name}",
        "qInTitle": title_filter,
        "searchIn": "title,description",
        "from": _iso(from_dt), "to": _iso(to_dt),
        "language": "en", "pageSize": min(limit, 50),
        "sortBy": "publishedAt", "apiKey": settings.NEWSAPI_KEY,
    }
    arts = await _newsapi(params1)
    if arts: return arts

    # TIER 2 — no qInTitle but add finance keywords
    params2 = {
        "q": f"({ticker} OR {name}) AND (earnings OR results OR guidance OR revenue OR upgrade OR downgrade OR stock OR shares)",
        "searchIn": "title,description",
        "from": _iso(from_dt), "to": _iso(to_dt),
        "language": "en", "pageSize": min(limit, 50),
        "sortBy": "publishedAt", "apiKey": settings.NEWSAPI_KEY,
    }
    arts = await _newsapi(params2)
    if arts: return arts

    # TIER 3 — widen window to 72h if still empty
    params3 = dict(params1)
    params3.pop("qInTitle", None)
    params3["from"] = _iso(to_dt - timedelta(hours=max(72, window_hours)))
    arts = await _newsapi(params3)
    return arts

    

@app.get("/analyze")
async def analyze(
    ticker: str = Query(..., min_length=1, max_length=10),
    windowHours: int = Query(settings.WINDOW_HOURS, ge=1, le=72),
    limit: int = Query(10, ge=1, le=50)  # allow 1..50
) -> Dict:

    try:
        # Get News first
        news = await fetch_news(ticker, windowHours, limit)

        # Get Reddit (best-effort)
        reddit = []
        try:
            reddit = await fetch_reddit(ticker, windowHours, limit)
        except Exception as e:
            log_err("fetch_reddit (ignored)", e)
            reddit = []

        print(f"[DEBUG] news={len(news)} reddit={len(reddit)} ticker={ticker}")  # <— add this

        combined = news + reddit
        combined.sort(key=lambda a: a.get("publishedAt",""), reverse=True)
        articles = combined[:limit]
        def is_reddit(a): 
            u = a.get("url","")
            return "reddit.com" in u

        articles.sort(key=lambda a: (is_reddit(a), a.get("publishedAt","")), reverse=True)
        # now first items are news; reddit follows


        # combine then keep the newest first
        combined = news + reddit
        combined.sort(key=lambda a: a.get("publishedAt",""), reverse=True)
        articles = combined[:limit]
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"NewsAPI error: {e.response.text[:200]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    MAX_LLM_ITEMS = 6  # cap to avoid high token costs
    sem = asyncio.Semaphore(4)  # limit concurrency

    async def score_one(i, a):
        title = a.get("title") or ""
        url = a.get("url") or ""
        domain = (url.split("/")[2] if "//" in url else "").replace("www.", "")
        published_at = a.get("publishedAt") or ""
        # NEW: gather snippet from either NewsAPI description or Reddit selftext
        snippet = (a.get("description") or a.get("content") or "")[:400]
        async with sem:
            s, rationale = await llm_score(
                title=title,
                text=snippet, 
                source=domain or a.get("source", {}).get("name", ""),
                ticker=ticker,
                published_at=published_at
            )


        if i < MAX_LLM_ITEMS:
            async with sem:
                s, rationale = await llm_score(
                    title=title,
                    text=snippet,                              
                    source=domain or a.get("source", {}).get("name", ""),
                    ticker=ticker,
                    published_at=published_at
                )
        else:
            lower = (title + " " + snippet).lower()
            s = 0.0
            if any(w in lower for w in ["beat","raise","upgrade","record","surge","strong","guidance"]): s = 0.3
            if any(w in lower for w in ["miss","cut","downgrade","lawsuit","drop","weak","probe","investigation"]): s = -0.3
            rationale = "Heuristic fallback"

        return {
            "id": f"news-{i}",
            "source": "reddit" if "reddit.com" in url else "news",  # better tagging
            "domain": domain or a.get("source", {}).get("name", ""),
            "title": title,
            "url": url,
            "publishedAt": published_at,
            "score": round(max(-1, min(1, s)), 2),
            "rationale": rationale or "N/A",
        }


    items = await asyncio.gather(*(score_one(i, a) for i, a in enumerate(articles[:limit])))

    overall = round(sum(i["score"] for i in items) / len(items), 2) if items else 0.0
    if items:
        scores = [i["score"] for i in items]
        spread = max(scores) - min(scores)
        confidence = round(max(0.0, 1.0 - min(1.0, spread)), 2)
    else:
        confidence = 0.0

    return {
        "ticker": ticker.upper(),
        "windowHours": windowHours,
        "overall": overall,
        "confidence": confidence,
        "reasons": ["LLM (first N) + fallback heuristic"],
        "items": items
    }
