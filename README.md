# News Sentiment Dashboard - Backend

A FastAPI-based backend service for analyzing stock market sentiment from news articles using FinBERT and AI-powered rationales.

## 🏗️ Architecture

```
backend/app/
├── main.py                 # FastAPI application and routes
├── config.py              # Configuration management
├── models.py              # Data models
├── schemas.py             # Pydantic schemas for API
├── utils.py               # Shared utility functions
├── core/
│   └── sentiment.py       # FinBERT sentiment analysis
├── services/
│   └── rationales.py      # AI rationale generation
└── sources/
    ├── common.py          # Shared source utilities
    ├── collector.py       # News collection coordinator
    ├── google_news.py     # Google News fetcher
    └── yfinance.py        # Yahoo Finance fetcher
```

## 🚀 Features

- **Multi-Source News Collection**: Yahoo Finance and Google News RSS feeds
- **Financial Sentiment Analysis**: FinBERT model for domain-specific analysis
- **Intelligent Weighting**: Multi-factor weighting (recency, source credibility, engagement)
- **AI-Powered Rationales**: ChatGPT explanations for sentiment classifications
- **Deduplication**: Smart removal of duplicate news articles
- **Source Filtering**: Only trusted news sources included
- **Async Processing**: Non-blocking news collection and analysis

## 📦 Dependencies

### Core Dependencies
```bash
pip install fastapi uvicorn pydantic feedparser python-dateutil
```

### Optional Dependencies
```bash
# For sentiment analysis
pip install transformers torch

# For AI rationales
pip install openai

# For domain extraction
pip install tldextract
```

## ⚙️ Configuration

Environment variables (all optional):

```bash
# API Keys
OPENAI_API_KEY=your_openai_key_here

# News Collection
LOOKBACK_DAYS=5
MAX_ITEMS=40

# Sentiment Analysis
HALF_LIFE_HOURS=24.0
DEFAULT_SOURCE_WEIGHT=0.75

# CORS
CORS_ALLOW_ORIGINS=*
```

## 🏃‍♂️ Running the Application

### Development
```bash
cd backend
python -m uvicorn app.main:app --reload --reload-dir app
```

### Production
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### Health Check
```http
GET /health
```

### Sentiment Analysis
```http
GET /sentiment?ticker=TSLA&lookback_days=7&include_rationales=true&limit=20
```

**Parameters:**
- `ticker` (required): Stock ticker symbol
- `lookback_days` (optional): Days to look back (1-14, default: 5)
- `include_rationales` (optional): Include AI explanations (default: true)
- `limit` (optional): Max news items (1-50, default: 10)

**Response:**
```json
{
  "ticker": "TSLA",
  "as_of": "2024-01-15T10:30:00Z",
  "lookback_days": 7,
  "overall_score": 0.2345,
  "n_items": 15,
  "items": [
    {
      "id": "a1b2c3d4e5f6g7h8",
      "source": "reuters.com",
      "title": "Tesla reports record Q4 deliveries",
      "url": "https://reuters.com/...",
      "published_at": "2024-01-15T09:00:00Z",
      "text": "Tesla delivered 484,507 vehicles...",
      "label": "positive",
      "prob_positive": 0.85,
      "prob_neutral": 0.10,
      "prob_negative": 0.05,
      "score": 0.8,
      "weight": 0.9,
      "weighted_score": 0.72,
      "rationale": "Positive for TSLA: Tesla reports record Q4 deliveries..."
    }
  ]
}
```

## 🔧 Code Quality Improvements

### ✅ Completed Cleanup Tasks

1. **Import Organization**: Cleaned up imports and removed unused dependencies
2. **Documentation**: Added comprehensive docstrings to all functions
3. **Code Duplication**: Consolidated duplicate utility functions
4. **Error Handling**: Improved error handling with proper logging
5. **Type Hints**: Added complete type annotations
6. **Configuration**: Centralized configuration management
7. **Logging**: Added proper logging throughout the application
8. **Code Formatting**: Standardized code formatting and structure

### 🏗️ Architecture Improvements

- **Separation of Concerns**: Clear separation between data models, business logic, and API layer
- **Modular Design**: Each module has a single responsibility
- **Error Resilience**: Graceful handling of missing dependencies and API failures
- **Performance**: Lazy loading of heavy ML models
- **Maintainability**: Clean, readable code with comprehensive documentation

### 📊 Sentiment Analysis Pipeline

1. **News Collection**: Fetch from multiple sources concurrently
2. **Source Filtering**: Keep only trusted sources (weight ≥ 0.6)
3. **Deduplication**: Remove duplicate articles
4. **Sentiment Analysis**: FinBERT model with financial domain expertise
5. **Weighting**: Multi-factor importance scoring
6. **Rationale Generation**: AI explanations for sentiment classifications
7. **Response Building**: Structured API response

### 🎯 Weighting System

- **Recency Weight (50%)**: Exponential decay based on article age
- **Source Weight (30%)**: Credibility based on news source
- **Engagement Weight (20%)**: User interaction (Reddit upvotes/comments)

## 🧪 Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test sentiment analysis
curl "http://localhost:8000/sentiment?ticker=TSLA&limit=5"
```

## 📈 Performance

- **Startup Time**: < 1 second (with lazy loading)
- **Model Loading**: 5-15 seconds (first sentiment call)
- **API Response**: 1-3 seconds (depending on news volume)
- **Memory Usage**: ~500MB (with loaded model)

## 🔒 Security

- **Input Validation**: Pydantic schemas validate all inputs
- **Rate Limiting**: Built-in FastAPI rate limiting
- **CORS**: Configurable CORS settings
- **Error Handling**: No sensitive information in error messages

## 🚀 Deployment

The application is ready for deployment on:
- **Docker**: Use the provided Dockerfile
- **Cloud Platforms**: AWS, GCP, Azure
- **Container Orchestration**: Kubernetes, Docker Swarm
- **Serverless**: AWS Lambda, Google Cloud Functions

## 📝 License

This project is licensed under the MIT License.
