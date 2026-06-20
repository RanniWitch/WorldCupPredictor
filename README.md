# World Cup 2026 Predictor

A machine learning system that predicts FIFA World Cup 2026 match outcomes using Logistic Regression trained on international football data. The project includes a command-line interface for quick predictions and a full-stack web dashboard for browsing group standings, match predictions, and the knockout bracket.

## Overview

This project fetches live match and standings data from the football-data.org API, trains a Logistic Regression model on historical international match results, and produces win probability estimates for upcoming World Cup 2026 fixtures. Predictions are served through both a terminal CLI and a React-based web dashboard backed by a FastAPI REST API.

## Architecture

```
WorldCupPredictor/
├── src/                  # Core prediction engine
│   ├── api_client.py     # football-data.org API client with rate limit handling
│   ├── data_pipeline.py  # Raw data parsing and match extraction
│   ├── feature_engine.py # Feature computation for model training
│   ├── model.py          # Logistic Regression wrapper
│   ├── predictor.py      # Pipeline orchestrator
│   └── scaler.py         # Feature scaling
├── backend/              # FastAPI REST API
│   ├── main.py           # Application entry point with CORS config
│   ├── routes/           # Endpoint handlers (groups, predictions, knockout)
│   ├── schemas.py        # Pydantic response models
│   ├── services.py       # Business logic and data transformation
│   └── error_handling.py # Exception-to-HTTP mapping
├── frontend/             # React + Vite + TypeScript SPA
│   └── src/
│       ├── components/   # UI components (GroupStageView, KnockoutBracketView, etc.)
│       ├── api.ts        # Frontend API client
│       └── types.ts      # TypeScript interfaces
├── tests/                # Unit and property-based tests for the prediction engine
├── predict.py            # Interactive CLI for terminal predictions
└── pyproject.toml        # Project configuration and dependencies
```

## How It Works

1. The prediction engine fetches match data from football-data.org for the World Cup 2026 competition, along with supplementary training data from the European Championship and Copa America.

2. Finished matches are parsed into a training dataset. The feature engine computes per-team performance metrics (win rates, goal averages, form) from historical results.

3. A Logistic Regression model is trained on the computed features with binary labels (home win vs. not).

4. For each scheduled match, the system builds a feature vector from both teams' statistics, scales it, and predicts the probability of a home win or loss.

5. Results are returned sorted by match date, with each prediction containing team names, crest URLs, and probability values between 0.0 and 1.0.

## Tools and Technologies

### Backend
- **Python 3.10+** - Primary language for the prediction engine and API server
- **FastAPI** - Async REST framework with automatic OpenAPI documentation
- **Pydantic** - Data validation and response serialization
- **scikit-learn** - Logistic Regression model implementation
- **pandas** - Data manipulation and pipeline processing
- **Hypothesis** - Property-based testing for backend services
- **pytest** - Test framework

### Frontend
- **React 19** - Component-based UI library
- **TypeScript** - Static typing for frontend code
- **Vite** - Build tool and development server
- **Vitest** - Unit testing framework
- **fast-check** - Property-based testing for frontend logic

### External Services
- **football-data.org API v4** - Live match data, standings, and team information

## Dependencies

### Python (install with pip)
```
pandas>=2.0.0
scikit-learn>=1.3.0
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

You will be prompted to enter the number of upcoming matches you want predictions for. The output includes the predicted winner and confidence level for each match.

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
