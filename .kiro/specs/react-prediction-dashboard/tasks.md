# Implementation Plan: React Prediction Dashboard

## Overview

This plan implements a full-stack web layer for the World Cup Predictor: a FastAPI backend exposing REST endpoints (`/api/groups`, `/api/predictions`, `/api/knockout`) and a React + Vite frontend rendering group stage standings and a knockout bracket. The backend wraps the existing `src/` prediction engine; the frontend consumes the backend's JSON responses.

## Tasks

- [x] 1. Set up backend project structure and schemas
  - [x] 1.1 Create backend directory structure and FastAPI entry point
    - Create `backend/` directory with `__init__.py`
    - Create `backend/main.py` with FastAPI app instance, CORS middleware configured for frontend origin, `python-dotenv` loading of `FOOTBALL_DATA_API_KEY`
    - Create `backend/routes/` package with `__init__.py`
    - Add `fastapi`, `uvicorn`, `python-dotenv` to project dependencies
    - _Requirements: 1.1, 1.5, 1.7_

  - [x] 1.2 Define Pydantic response schemas
    - Create `backend/schemas.py` with all response models: `Team`, `Group`, `GroupsResponse`, `MatchPrediction`, `PredictionsResponse`, `KnockoutTeam`, `KnockoutMatch`, `KnockoutRound`, `KnockoutResponse`
    - Ensure `home_win_prob` and `home_loss_prob` are typed as `float` with bounds documented
    - _Requirements: 1.2, 1.3, 1.4, 3.4_

  - [x] 1.3 Implement error handling utility
    - Create `backend/error_handling.py` with `handle_api_error()` function mapping `AuthenticationError` → 502, `RateLimitError` → 503, `APIError(408)` → 504, generic `APIError` → 502, `NoTrainingDataError` → 503, `KeyError`/`ValueError` → 502
    - Each HTTP error response includes a descriptive `detail` message
    - _Requirements: 1.6_

- [x] 2. Implement backend service layer and route handlers
  - [x] 2.1 Implement groups service and route
    - Create `backend/services.py` with `get_group_data()` function that calls `APIClient.get_matches(2000)`, parses standings response, returns groups A-L each with 4 teams including `team_id`, `team_name`, `crest`
    - Create `backend/routes/groups.py` with GET `/api/groups` endpoint returning `GroupsResponse`
    - Handle incomplete group data by returning available groups
    - _Requirements: 1.2, 2.1, 2.2, 2.3, 2.4_

  - [x] 2.2 Implement predictions service and route
    - Add `get_predictions()` to `backend/services.py` that instantiates `Predictor`, calls `run(2000)`, transforms the DataFrame to a list of `MatchPrediction` objects sorted by `match_date` ascending
    - Create `backend/routes/predictions.py` with GET `/api/predictions` endpoint returning `PredictionsResponse`
    - Return empty predictions array with status 200 when no scheduled matches
    - _Requirements: 1.3, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 2.3 Implement knockout service and route
    - Add `get_knockout_data()` to `backend/services.py` that calls `APIClient`, filters knockout stage matches, organizes into rounds (Round_of_32, Round_of_16, Quarter_Finals, Semi_Finals, Final)
    - Use `"TBD"` for undetermined team names and `""` for undetermined crests
    - Include `status` and scores (non-null only when FINISHED)
    - Create `backend/routes/knockout.py` with GET `/api/knockout` endpoint returning `KnockoutResponse`
    - _Requirements: 1.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 2.4 Register all routers in main.py
    - Import and include groups, predictions, and knockout routers in `backend/main.py`
    - Wire error handling into route handlers using try/except with `handle_api_error()`
    - _Requirements: 1.1, 1.6_

- [x] 3. Checkpoint - Backend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Set up frontend project structure
  - [x] 4.1 Initialize Vite + React + TypeScript project
    - Run `npm create vite@latest frontend -- --template react-ts` in project root
    - Install dependencies: `npm install` in `frontend/`
    - Add `fast-check` and `@testing-library/react`, `@testing-library/jest-dom`, `vitest`, `jsdom` as dev dependencies
    - Configure `vitest` in `vite.config.ts`
    - _Requirements: 5.1_

  - [x] 4.2 Create TypeScript interfaces and API client module
    - Create `frontend/src/types.ts` with all TypeScript interfaces: `Team`, `Group`, `GroupsResponse`, `MatchPrediction`, `PredictionsResponse`, `KnockoutTeam`, `KnockoutMatch`, `KnockoutRound`, `KnockoutResponse`
    - Create `frontend/src/api.ts` with `fetchGroups()`, `fetchPredictions()`, `fetchKnockout()` functions using `VITE_API_BASE` env var (default `http://localhost:8000`)
    - _Requirements: 5.3, 5.4_

- [x] 5. Implement frontend components
  - [x] 5.1 Implement TeamCard component
    - Create `frontend/src/components/TeamCard.tsx`
    - Display team crest image with `alt={teamName}` for accessibility
    - Display team name adjacent to crest
    - Implement fallback placeholder icon when `crestUrl` is empty or image fails to load (use `onError` handler)
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 5.2 Implement MatchPredictionCard component
    - Create `frontend/src/components/MatchPredictionCard.tsx`
    - Display home and away team names with win probabilities as percentages rounded to 1 decimal place (e.g., "65.3%")
    - Visually distinguish the favored team (higher probability) with a CSS class
    - Display match date in human-readable locale format
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 5.3 Implement GroupStageView component
    - Create `frontend/src/components/GroupStageView.tsx`
    - Fetch `/api/groups` and `/api/predictions` on mount and tab switch
    - Render responsive grid of group cards (A through L) with group name headers
    - Each group displays `TeamCard` components for its teams
    - Display `MatchPredictionCard` components for group matches
    - Render team crests with appropriate alt text
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 5.4 Implement KnockoutBracketView component
    - Create `frontend/src/components/KnockoutBracketView.tsx`
    - Fetch `/api/knockout` on mount and tab switch
    - Render bracket organized by round columns (Round_of_32 through Final)
    - Display team names and crests for determined teams; "TBD" for undetermined
    - Display final scores for FINISHED matches
    - Visually connect match slots between rounds to show progression
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 5.5 Implement App.tsx with tab navigation and data refresh
    - Create `frontend/src/App.tsx` with tab-based navigation between GroupStageView and KnockoutBracketView
    - Display loading indicator while fetching data
    - Display error message with retry button on backend errors
    - Add refresh button that re-fetches data without clearing displayed content
    - Ensure responsive layout for viewports 320px to 1920px
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 10.1, 10.2, 10.3_

- [x] 6. Checkpoint - Frontend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Backend property-based tests
  - [x] 7.1 Write property test for groups transformation
    - **Property 1: Groups transformation produces complete team data**
    - Use Hypothesis to generate random valid standings API responses with group structures
    - Assert output contains groups A-L, each with exactly 4 teams, every team has non-null `team_id`, `team_name`, and `crest`
    - File: `backend/tests/test_properties.py`
    - **Validates: Requirements 1.2, 2.2, 2.3**

  - [x] 7.2 Write property test for predictions sort order and completeness
    - **Property 2: Predictions response preserves field completeness and sort order**
    - Use Hypothesis to generate random DataFrames matching `PREDICTION_COLUMNS` schema
    - Assert all prediction objects contain required fields and list is sorted by `match_date` ascending
    - File: `backend/tests/test_properties.py`
    - **Validates: Requirements 1.3, 3.2, 3.3**

  - [x] 7.3 Write property test for probability bounds
    - **Property 3: Probability values are bounded**
    - Use Hypothesis to generate random float pairs for `home_win_prob` and `home_loss_prob`
    - Assert both values are in range [0.0, 1.0] after transformation
    - File: `backend/tests/test_properties.py`
    - **Validates: Requirements 3.4**

  - [x] 7.4 Write property test for knockout team resolution
    - **Property 4: Knockout match team resolution**
    - Use Hypothesis to generate random knockout match data with mixed present/absent team IDs
    - Assert determined teams have actual names/crests, undetermined teams get "TBD"/"", and status is always present
    - File: `backend/tests/test_properties.py`
    - **Validates: Requirements 4.3, 4.4, 4.5**

  - [x] 7.5 Write property test for finished match scores
    - **Property 5: Finished knockout matches include scores**
    - Use Hypothesis to generate knockout matches with various statuses
    - Assert FINISHED matches have non-null integer scores; non-FINISHED matches have null scores
    - File: `backend/tests/test_properties.py`
    - **Validates: Requirements 4.6**

  - [x] 7.6 Write property test for API error mapping
    - **Property 6: API error mapping**
    - Use Hypothesis to generate random API exception instances (AuthenticationError, RateLimitError, APIError, NoTrainingDataError)
    - Assert all produce HTTP responses with status ≥ 400 and a `detail` message string
    - File: `backend/tests/test_properties.py`
    - **Validates: Requirements 1.6**

- [x] 8. Frontend property-based tests
  - [x] 8.1 Write property test for probability formatting
    - **Property 7: Probability percentage formatting**
    - Use fast-check to generate random floats in [0.0, 1.0]
    - Assert formatting function produces string matching pattern "X.X%" where numeric part equals `(p * 100).toFixed(1)`
    - File: `frontend/src/__tests__/properties.test.ts`
    - **Validates: Requirements 9.1**

  - [x] 8.2 Write property test for favored team identification
    - **Property 8: Favored team identification**
    - Use fast-check to generate pairs of distinct probability values
    - Assert the team with higher probability receives the favored CSS class/style
    - File: `frontend/src/__tests__/properties.test.ts`
    - **Validates: Requirements 9.3**

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (Properties 1-8 from design)
- Backend uses pytest + hypothesis; frontend uses vitest + fast-check
- The existing `src/` package is not modified — backend imports from it directly
- CORS is configured to allow the Vite dev server origin (default `http://localhost:5173`)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "4.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "4.2"] },
    { "id": 2, "tasks": ["2.1", "2.2", "2.3", "5.1", "5.2"] },
    { "id": 3, "tasks": ["2.4", "5.3", "5.4"] },
    { "id": 4, "tasks": ["5.5"] },
    { "id": 5, "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "8.1", "8.2"] }
  ]
}
```
