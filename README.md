# World Cup 2026 Predictor

A machine learning system that predicts FIFA World Cup 2026 match outcomes using XGBoost trained on 5,600+ recent international football matches. The project produces three-way predictions (home win, draw, away win), predicted scorelines, and over/under probabilities. It includes a command-line interface for quick predictions, a prediction accuracy tracker, and a full-stack web dashboard.

## Overview

This project combines a large historical dataset of international match results (2020-2026) with live data from the football-data.org API. An XGBoost gradient-boosted classifier is trained on 20 engineered features — including FIFA rankings, head-to-head records, recent form, and goal statistics — with exponential recency weighting so that current team strength matters more than older results. A Poisson goals model produces predicted scorelines and over/under probabilities.

## Architecture

```
WorldCupPredictor/
├── src/                    # Core prediction engine
│   ├── api_client.py       # football-data.org API client with rate limit handling
│   ├── data_pipeline.py    # Raw data parsing and match extraction
│   ├── feature_engine.py   # 20-feature computation (rankings, form, h2h, etc.)
│   ├── historical_data.py  # Kaggle dataset loader with recency weighting
│   ├── goals_model.py      # Poisson model for scoreline predictions
│   ├── model.py            # XGBoost 3-class classifier
│   ├── predictor.py        # Pipeline orchestrator
│   └── scaler.py           # Feature scaling
├── backend/                # FastAPI REST API
│   ├── main.py             # Application entry point with CORS config
│   ├── routes/             # Endpoint handlers (groups, predictions, knockout)
│   ├── schemas.py          # Pydantic response models
│   ├── services.py         # Business logic, caching, and data transformation
│   └── error_handling.py   # Exception-to-HTTP mapping
├── frontend/               # React + Vite + TypeScript SPA
│   └── src/
│       ├── components/     # UI components (GroupStageView, KnockoutBracketView, etc.)
│       ├── api.ts          # Frontend API client
│       └── types.ts        # TypeScript interfaces
├── data/                   # Training data and tracking
│   ├── international_results.csv  # 49,000+ historical international matches
│   ├── fifa_rankings.csv          # Current FIFA world rankings
│   ├── saved_predictions.csv      # Pre-match prediction snapshots
│   └── prediction_results.csv     # Accuracy tracking results
├── tests/                  # Unit and property-based tests
├── predict.py              # Interactive CLI for terminal predictions
├── track_results.py        # Prediction accuracy tracker
└── pyproject.toml          # Project configuration and dependencies
```

## How It Works

1. The system loads 5,600+ international matches from 2020-2026 (historical dataset) and combines them with live data from the football-data.org API (World Cup 2026, European Championship, Copa America).

2. Exponential recency weighting is applied — a match from 1 year ago has 50% the weight of today's match, and a match from 3 years ago has about 12%. This ensures the model reflects current team strength rather than outdated rosters.

3. The feature engine computes 20 features per match including overall win/draw rates, recent form (last 5 matches), average goals scored/conceded, FIFA ranking gap, head-to-head history, and neutral venue flag.

4. An XGBoost classifier is trained on 3 outcome classes (home win, draw, away win) with sample weights. XGBoost captures non-linear patterns and feature interactions that simpler models cannot.

5. A separate Poisson goals model estimates expected goals for each team, producing predicted scorelines and over/under probabilities.

6. For each scheduled match, the system outputs: win/draw/loss probabilities, predicted score, expected goals, over/under 2.5 and 3.5 goals, and the top 3 most likely scorelines.

## Model Features (20 total)

| Category | Features |
|----------|----------|
| Overall strength | home/away win_rate, draw_rate |
| Offensive ability | home/away avg_goals_scored |
| Defensive ability | home/away avg_goals_conceded |
| Current form | home/away recent_win_rate (last 5 matches) |
| Recent attack | home/away recent_goals_scored |
| FIFA ranking | home/away fifa_rank, rank_gap |
| FIFA points | home/away fifa_points, points_gap |
| Head-to-head | h2h_home_win_rate, h2h_draw_rate |
| Venue | is_neutral |

## Training Data

The model trains on data from two sources:

**Historical dataset (primary):** 49,000+ international matches from 1872-2026, filtered to 5,600+ matches since January 2020. Sourced from the open-source Kaggle/GitHub international results dataset. Includes World Cup qualifiers, continental championships, Nations League, friendlies, and more across 255 national teams.

**Live API data (supplementary):** Current-season matches fetched from football-data.org for World Cup 2026 (competition 2000), European Championship (2018), and Copa America (2152). These receive 2x weight as the most current data available.

**Recency weighting:** Exponential decay with a 1-year half-life. This means:
- A match from last month: ~97% weight
- A match from 1 year ago: 50% weight
- A match from 2 years ago: 25% weight
- A match from 4 years ago: 6% weight

This prevents stale roster data from polluting predictions while still capturing long-term team program strength.

## Tools and Technologies

### Machine Learning
- **XGBoost** - Gradient-boosted decision trees for 3-class outcome prediction
- **scikit-learn** - Feature scaling and model utilities
- **pandas / numpy** - Data manipulation and numerical computing
- **Poisson distribution** - Scoreline and over/under probability modeling

### Backend
- **Python 3.10+** - Primary language
- **FastAPI** - Async REST framework with automatic OpenAPI documentation
- **Pydantic** - Data validation and response serialization

### Frontend
- **React 19** - Component-based UI library
- **TypeScript** - Static typing
- **Vite** - Build tool and development server

### Testing
- **pytest + Hypothesis** - Backend property-based testing
- **Vitest + fast-check** - Frontend property-based testing

### External Services
- **football-data.org API v4** - Live match data, standings, and team information

## Dependencies

### Python (install with pip)
```
pandas>=2.0.0
scikit-learn>=1.3.0
xgboost>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
requests>=2.31.0
fastapi>=0.104.0
uvicorn>=0.24.0
python-dotenv>=1.0.0
```

### Python Dev Dependencies
```
hypothesis>=6.82.0
pytest>=7.4.0
pytest-cov>=4.1.0
```

### Frontend (managed via npm in frontend/)
```
react, react-dom, vite, typescript, vitest, fast-check,
@testing-library/react, @testing-library/jest-dom, jsdom
```

## Setup

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher
- A football-data.org API key (free tier available at https://www.football-data.org/)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/RanniWitch/WorldCupPredictor.git
cd WorldCupPredictor
```

2. Install Python dependencies:
```bash
pip install -e .
```

3. Create a `.env` file in the project root:
```
FOOTBALL_DATA_API_KEY=your_api_key_here
```

4. Install frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

## Usage

### Command-Line Predictions

Run the interactive predictor from the project root:
```bash
python predict.py
```

You will be prompted for how many upcoming matches you want predictions for. Each prediction includes:
- Win/draw/loss probabilities
- Predicted scoreline with probability
- Expected goals per team
- Over/under 2.5 and 3.5 goals probabilities
- Top 3 most likely scorelines

### Tracking Prediction Accuracy

Save predictions for upcoming matches (run before matches start):
```bash
python track_results.py save
```

Check results after matches finish:
```bash
python track_results.py check
```

Or run both at once (check results then save new predictions):
```bash
python track_results.py
```

Results are logged to `data/prediction_results.csv` with cumulative accuracy statistics displayed in the terminal.

### Web Dashboard

Start the backend API server:
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

In a separate terminal, start the frontend development server:
```bash
cd frontend
npm run dev
```

Open http://localhost:5173 in your browser. The dashboard provides two views:
- **Group Stage** - All 12 groups with team listings and match predictions
- **Knockout Bracket** - Tournament bracket from Round of 32 through the Final

### Running Tests

Backend tests:
```bash
python -m pytest backend/tests/ -v
```

Prediction engine tests:
```bash
python -m pytest tests/ -v
```

Frontend tests:
```bash
cd frontend
npm test
```

## Rate Limiting

The football-data.org free tier allows 10 requests per minute. This project handles rate limiting through:

- Response header tracking (`X-RequestsAvailable`, `X-RequestCounter-Reset`) to monitor remaining request budget
- Proactive throttling that waits for the counter to reset when fewer than 2 requests remain
- Automatic retry with appropriate wait times on 429 responses
- Server-side response caching (5-minute TTL) to minimize redundant API calls

## License

MIT
