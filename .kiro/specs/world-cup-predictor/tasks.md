# Implementation Plan: World Cup Predictor

## Overview

Implement a Python-based World Cup match prediction system using Logistic Regression. The system fetches data from the football-data.org API, computes team performance features, scales them with StandardScaler, trains a classifier, and outputs prediction probabilities for upcoming matches. Implementation follows a bottom-up approach: project setup → error hierarchy → individual components → orchestrator → integration wiring.

## Tasks

- [x] 1. Set up project structure and dependencies
  - [x] 1.1 Create project directory structure and install dependencies
    - Create `src/` package with `__init__.py`
    - Create `tests/` directory with `conftest.py`
    - Create `requirements.txt` with: pandas, scikit-learn, requests, hypothesis, pytest, pytest-cov
    - Create `pyproject.toml` or `setup.cfg` for project metadata
    - _Requirements: 1.1, 1.2, 5.1, 4.1_

  - [x] 1.2 Define error hierarchy and custom exceptions
    - Create `src/exceptions.py` with all custom exception classes: `WorldCupPredictorError`, `APIError`, `AuthenticationError`, `RateLimitError`, `InsufficientDataError`, `SingleClassError`, `NotFittedError`, `NoTrainingDataError`
    - Each exception must include appropriate attributes (e.g., `status_code` for `APIError`)
    - _Requirements: 1.4, 1.5, 1.6, 1.7, 4.3, 5.4, 5.5, 6.5_

- [x] 2. Implement API Client
  - [x] 2.1 Implement APIClient class with retry logic
    - Create `src/api_client.py` with `APIClient` class
    - Implement `__init__` accepting `api_key` and optional `base_url`
    - Implement `get_matches(competition_id, timeout=60)` that fetches `/v4/competitions/{id}/matches`
    - Implement `_request_with_retry(url, max_retries=3, timeout=60)` with rate-limit handling
    - Use `X-Auth-Token` header for authentication
    - Raise `AuthenticationError` on 401/403 without retry
    - Raise `RateLimitError` after 3 failed retries on 429
    - Raise `APIError` with status code and message for other HTTP errors
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 2.2 Write unit tests for APIClient
    - Mock HTTP responses using `unittest.mock.patch` on `requests.get`
    - Test successful response returns parsed JSON
    - Test 401/403 raises `AuthenticationError` immediately
    - Test 429 triggers retry logic up to 3 times then raises `RateLimitError`
    - Test other HTTP errors raise `APIError` with status code and message
    - Test timeout raises `APIError`
    - _Requirements: 1.4, 1.5, 1.6, 1.7_

- [x] 3. Implement Data Pipeline
  - [x] 3.1 Implement DataPipeline class
    - Create `src/data_pipeline.py` with `DataPipeline` class
    - Implement `parse_matches(raw_response)` that filters for FINISHED status, excludes null scores with warning log, and returns DataFrame with columns: home_team_id, away_team_id, home_score, away_score, match_date
    - Implement `get_scheduled_matches(raw_response)` that extracts SCHEDULED matches as list of dicts
    - Return empty DataFrame with correct schema when no finished matches exist
    - Use Python `logging` module for warnings about excluded matches
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 7.2_

  - [x] 3.2 Write property test for data parsing (Property 1)
    - **Property 1: Data parsing preserves match information**
    - Use Hypothesis to generate valid API response dicts with mixed statuses
    - Assert: one row per FINISHED match with non-null scores
    - Assert: columns match input JSON values exactly
    - Assert: non-FINISHED matches and null-score matches excluded
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

  - [x] 3.3 Write property test for match classification (Property 13)
    - **Property 13: Match classification by status**
    - Use Hypothesis to generate responses with mixed FINISHED/SCHEDULED statuses
    - Assert: FINISHED matches go to training set only
    - Assert: SCHEDULED matches go to prediction set only
    - Assert: no overlap between the two sets
    - **Validates: Requirements 7.2**

- [x] 4. Implement Feature Engine
  - [x] 4.1 Implement FeatureEngine class
    - Create `src/feature_engine.py` with `FeatureEngine` class
    - Implement `compute_features(matches_df)` computing win_rate, avg_goals_scored, avg_goals_conceded per team counting both home and away appearances
    - Implement `get_match_features(home_team_id, away_team_id, features_df)` building a 6-column feature vector
    - Use default values for unknown teams: win_rate=0.5, avg_goals_scored=0.0, avg_goals_conceded=0.0
    - Return DataFrame indexed by team_id
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 4.2 Write property test for feature computation (Property 2)
    - **Property 2: Feature computation correctness**
    - Use Hypothesis to generate match DataFrames
    - Assert: win_rate = wins / total_matches for each team
    - Assert: avg_goals_scored = total_goals_scored / total_matches
    - Assert: avg_goals_conceded = total_goals_conceded / total_matches
    - Assert: both home and away appearances counted
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.5**

  - [x] 4.3 Write property test for unknown team defaults (Property 11)
    - **Property 11: Unknown teams receive default features**
    - Use Hypothesis to generate team IDs not present in features DataFrame
    - Assert: get_match_features returns win_rate=0.5, avg_goals_scored=0.0, avg_goals_conceded=0.0 for unknown teams
    - Assert: valid output structure with all 6 columns
    - **Validates: Requirements 6.6**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Feature Scaler
  - [x] 6.1 Implement FeatureScaler class
    - Create `src/scaler.py` with `FeatureScaler` class
    - Implement `fit_transform(features)` using sklearn StandardScaler, preserving column names
    - Implement `transform(features)` using fitted parameters
    - Track `_is_fitted` state and `_n_features` count
    - Raise `ValueError` for NaN inputs
    - Raise `NotFittedError` if transform called before fit
    - Raise `ValueError` if column count mismatch on transform
    - Handle zero-variance columns (scale to zero without error)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 6.2 Write property test for scaler normalization (Property 3)
    - **Property 3: Scaler normalization invariant**
    - Use Hypothesis to generate numeric DataFrames with ≥2 rows and non-zero variance
    - Assert: after fit_transform, each non-zero-variance column has mean within ±1e-7 of 0.0
    - Assert: each non-zero-variance column has std within ±1e-7 of 1.0
    - **Validates: Requirements 4.1**

  - [x] 6.3 Write property test for scaler shape preservation (Property 4)
    - **Property 4: Scaler transform preserves shape and column names**
    - Use Hypothesis to generate training and prediction DataFrames with same column count
    - Assert: transform output has identical column names
    - Assert: transform output has identical row count
    - **Validates: Requirements 4.2**

  - [x] 6.4 Write property test for scaler column mismatch rejection (Property 5)
    - **Property 5: Scaler rejects column count mismatch**
    - Use Hypothesis to generate DataFrames with different column counts
    - Assert: transform raises ValueError when M ≠ N columns
    - **Validates: Requirements 4.4**

  - [x] 6.5 Write property test for scaler zero-variance handling (Property 6)
    - **Property 6: Scaler handles zero-variance columns**
    - Use Hypothesis to generate DataFrames with at least one constant column
    - Assert: fit_transform scales constant columns to all zeros
    - Assert: no error is raised
    - **Validates: Requirements 4.5**

  - [x] 6.6 Write property test for scaler NaN rejection (Property 7)
    - **Property 7: Scaler rejects NaN values**
    - Use Hypothesis to generate DataFrames with at least one NaN
    - Assert: fit_transform raises ValueError
    - Assert: transform raises ValueError
    - **Validates: Requirements 4.6**

- [x] 7. Implement Prediction Model
  - [x] 7.1 Implement PredictionModel class
    - Create `src/model.py` with `PredictionModel` class
    - Implement `train(features, labels)` using sklearn LogisticRegression
    - Implement `predict(features)` returning DataFrame with home_win_prob and home_loss_prob
    - Validate minimum 10 training samples, raise `InsufficientDataError` if fewer
    - Validate both classes present in labels, raise `SingleClassError` if single class
    - Validate no NaN/inf in features, raise `ValueError` if invalid
    - Raise `NotFittedError` if predict called before train
    - Use binary labels: 1 = home win, 0 = home loss or draw
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.5_

  - [x] 7.2 Write property test for prediction probabilities (Property 8)
    - **Property 8: Prediction probabilities form a valid distribution**
    - Use Hypothesis to generate valid training data and prediction features
    - Assert: home_win_prob in [0.0, 1.0]
    - Assert: home_loss_prob in [0.0, 1.0]
    - Assert: home_win_prob + home_loss_prob == 1.0 (within floating point tolerance)
    - **Validates: Requirements 5.3, 6.1**

  - [x] 7.3 Write property test for training validation (Property 12)
    - **Property 12: Training validation rejects invalid data**
    - Use Hypothesis to generate datasets with <10 records, single-class labels, and NaN/inf features
    - Assert: InsufficientDataError raised for <10 records
    - Assert: SingleClassError raised for single-class labels
    - Assert: ValueError raised for NaN/inf features
    - **Validates: Requirements 5.4, 5.5, 5.6**

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement Predictor Orchestrator
  - [x] 9.1 Implement Predictor class (orchestrator)
    - Create `src/predictor.py` with `Predictor` class
    - Implement `__init__(api_key)` initializing all pipeline components
    - Implement `run(competition_id)` executing the full pipeline:
      1. Fetch matches via API_Client
      2. Parse finished matches via Data_Pipeline
      3. Extract scheduled matches via Data_Pipeline
      4. Compute features via Feature_Engine
      5. Build training feature matrix and binary labels
      6. Scale training features via Scaler
      7. Train model
      8. For each scheduled match: build feature vector, scale, predict
      9. Return sorted DataFrame of predictions
    - Raise `NoTrainingDataError` if no finished matches
    - Return empty DataFrame if no scheduled matches (log info)
    - Propagate errors from any pipeline step
    - Sort output by match_date ascending
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 6.2, 6.3, 6.4_

  - [x] 9.2 Write property test for prediction output shape (Property 9)
    - **Property 9: Prediction output has correct shape**
    - Use Hypothesis to generate varying numbers of scheduled matches
    - Assert: output DataFrame has exactly N rows for N scheduled matches
    - Assert: columns include home_team_id, away_team_id, home_win_prob, home_loss_prob
    - **Validates: Requirements 6.2, 6.3**

  - [x] 9.3 Write property test for prediction sorting (Property 10)
    - **Property 10: Predictions are sorted by match date**
    - Use Hypothesis to generate scheduled matches with varying dates
    - Assert: output DataFrame is sorted by match_date ascending
    - **Validates: Requirements 6.4**

- [x] 10. Create Hypothesis strategies and shared test fixtures
  - [x] 10.1 Create custom Hypothesis strategies module
    - Create `tests/strategies.py` with reusable strategies:
      - `match_record`: generates valid match dicts with team IDs, scores, dates
      - `match_list`: generates lists of match records (1–50)
      - `training_data`: generates ≥10 records with both classes present
      - `api_response`: generates full API response JSON with mixed statuses
      - `feature_dataframe`: generates numeric DataFrames with bounded values
    - Update `tests/conftest.py` with shared pytest fixtures for mocked API responses and sample DataFrames
    - _Requirements: All (testing infrastructure)_

- [x] 11. Wire entry point and final integration
  - [x] 11.1 Create main entry point script
    - Create `src/main.py` (or `main.py` at project root) with CLI interface
    - Accept competition_id and api_key as arguments (via argparse or environment variables)
    - Instantiate `Predictor` and call `run(competition_id)`
    - Print prediction results to stdout in a readable format
    - Handle and display errors gracefully
    - _Requirements: 7.1_

  - [x] 11.2 Write integration tests for full pipeline
    - Mock API_Client responses with realistic fixture data
    - Test complete pipeline from fetch to prediction output
    - Assert output DataFrame structure and sorting
    - Test error propagation from each pipeline step
    - Test empty scheduled matches returns empty DataFrame
    - Test no finished matches raises NoTrainingDataError
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All HTTP calls are mocked in tests — no real API calls during testing
- The system uses Python 3.10+ features (type hints with `|` syntax)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["2.1", "3.1", "4.1", "6.1", "10.1"] },
    { "id": 3, "tasks": ["2.2", "3.2", "3.3", "4.2", "4.3", "6.2", "6.3", "6.4", "6.5", "6.6"] },
    { "id": 4, "tasks": ["7.1"] },
    { "id": 5, "tasks": ["7.2", "7.3"] },
    { "id": 6, "tasks": ["9.1"] },
    { "id": 7, "tasks": ["9.2", "9.3", "11.1"] },
    { "id": 8, "tasks": ["11.2"] }
  ]
}
```
