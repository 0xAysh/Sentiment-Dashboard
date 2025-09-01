# News Sentiment Dashboard

A full‑stack web application that fetches stock‑related news and community posts, runs sentiment analysis using LLMs, and displays interactive sentiment scores between -1 (bearish) and +1 (bullish).

## Features
- Enter a stock ticker symbol (e.g., AAPL, TSLA)
- Fetches recent news headlines from NewsAPI (and Reddit in later versions)
- Uses an LLM to score sentiment (-1 = extreme bearish, 0 = neutral, +1 = extreme bullish)
- Interactive React dashboard showing scores, rationales, and news sources
- FastAPI backend with clear API endpoints

## Tech Stack
- **Backend**: FastAPI (Python), httpx, pydantic
- **Frontend**: React + Vite
- **APIs**: NewsAPI, OpenAI (for LLM scoring)
- **Deployment**: (Vercel/Netlify for frontend, Render/Fly.io for backend)

## Project Structure
```
News-Sentiment-Dash/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   ├── .env.example
│   └── .env (ignored in git)
└── frontend/
    ├── package.json
    ├── src/
    └── public/
```

## Setup

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --reload --port 8000
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

Frontend runs on [http://localhost:5173](http://localhost:5173)  
Backend runs on [http://localhost:8000](http://localhost:8000)

## Environment Variables
See `.env.example` for required keys:
```
NEWSAPI_KEY=your_newsapi_key_here
OPENAI_API_KEY=your_openai_key_here
WINDOW_HOURS=24
PORT=8000
```

## API Endpoints
- `GET /health` → Health check
- `GET /analyze?ticker=AAPL&windowHours=24&limit=10` → Returns sentiment analysis results

## Roadmap
- [x] Setup FastAPI backend
- [x] Connect NewsAPI headlines
- [ ] Integrate OpenAI LLM for real sentiment scoring
- [ ] Add Reddit posts as a data source
- [ ] Improve UI with gauges, charts, and filters

## License
MIT License
