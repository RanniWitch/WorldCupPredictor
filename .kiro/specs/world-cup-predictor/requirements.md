# Requirements Document

## Introduction

A World Cup match prediction system that uses machine learning to predict the outcome of each game in the FIFA World Cup. The system fetches real-time match and team data from the football-data.org API, computes key performance statistics (win rate, goals defended, etc.), and uses a Logistic Regression model with StandardScaler preprocessing to output prediction probabilities for binary outcomes (win/loss) for each match.

## Glossary

- **Predictor**: The main prediction system that orchestrates data fetching, feature engineering, model training, and prediction output
- **API_Client**: The component responsible for communicating with the football-data.org REST API to retrieve match and team data
- **Feature_Engine**: The component that computes statistical features (win rate, goals defended, etc.) from raw match data
- **Data_Pipeline**: The component that transforms raw API responses into structured pandas DataFrames suitable for model input
- **Model**: The Logistic Regression classifier that predicts binary match outcomes (win/loss)
- **Scaler**: The StandardScaler component that normalizes feature values before model training and prediction
- **Match_Record**: A single row of data representing one historical match with computed features for both teams
- **Prediction_Output**: The result object containing prediction probabilities for a given match

## Requirements

### Requirement 1: Fetch Team and Match Data from API

**User Story:** As a user, I want the system to fetch real-time team and match data from the football-data.org API, so that predictions are based on current tournament information.

#### Acceptance Criteria

1. WHEN the Predictor is initialized with a valid API key, THE API_Client SHALL send an authenticated request to the football-data.org API and confirm a successful response within 30 seconds
2. WHEN a competition ID is provided, THE API_Client SHALL retrieve all scheduled and completed matches for that competition within 60 seconds
3. WHEN match data is retrieved, THE API_Client SHALL return team IDs, match scores, match status, and match date for each match
4. IF the API returns an error response, THEN THE API_Client SHALL raise an exception including the HTTP status code and error message from the response
5. IF the API rate limit is exceeded, THEN THE API_Client SHALL wait until the rate limit window resets and retry the request, up to a maximum of 3 retry attempts
6. IF the API key is invalid or expired, THEN THE API_Client SHALL raise an exception indicating authentication failure without retrying the request
7. IF the maximum retry attempts are exhausted, THEN THE API_Client SHALL raise an exception indicating the API is unavailable due to rate limiting

### Requirement 2: Parse Match Data into DataFrames

**User Story:** As a user, I want match data parsed into a structured DataFrame, so that it can be used for feature computation and model training.

#### Acceptance Criteria

1. WHEN raw match JSON is received from the API_Client, THE Data_Pipeline SHALL parse each match into a Match_Record containing columns: home_team_id (int), away_team_id (int), home_score (int), away_score (int), and match_date (datetime)
2. WHEN all matches are parsed, THE Data_Pipeline SHALL return a pandas DataFrame with one row per Match_Record
3. IF a match has a status other than "FINISHED", THEN THE Data_Pipeline SHALL exclude that match from the parsed DataFrame
4. IF a match record contains missing or null score fields, THEN THE Data_Pipeline SHALL exclude that record from the DataFrame and log a warning containing the match identifier
5. IF no finished matches are present in the input, THEN THE Data_Pipeline SHALL return an empty DataFrame with the correct column schema (home_team_id, away_team_id, home_score, away_score, match_date)

### Requirement 3: Compute Team Performance Features

**User Story:** As a user, I want key team statistics computed from historical match data, so that the model has meaningful features for prediction.

#### Acceptance Criteria

1. WHEN historical match data is available, THE Feature_Engine SHALL compute the win rate for each team as the ratio of wins to total matches played, counting both home and away appearances, where a win is defined as the team's score being strictly greater than the opponent's score
2. WHEN historical match data is available, THE Feature_Engine SHALL compute the average goals conceded per match for each team by dividing the total goals scored against the team across all home and away appearances by the team's total number of matches
3. WHEN historical match data is available, THE Feature_Engine SHALL compute the average goals scored per match for each team by dividing the total goals scored by the team across all home and away appearances by the team's total number of matches
4. IF a team has zero historical matches, THEN THE Feature_Engine SHALL assign a default value of 0.5 for win rate and 0.0 for average goals scored and average goals conceded
5. THE Feature_Engine SHALL return a DataFrame indexed by team ID containing exactly three feature columns: win rate, average goals scored per match, and average goals conceded per match

### Requirement 4: Scale Features Using StandardScaler

**User Story:** As a user, I want features normalized before model training, so that no single feature dominates due to scale differences.

#### Acceptance Criteria

1. WHEN training features are provided as a numeric DataFrame, THE Scaler SHALL fit a StandardScaler to the training data and transform the features, returning a DataFrame with the same column names where each column has a mean within ±1e-7 of zero and a standard deviation within ±1e-7 of 1.0
2. WHEN prediction features are provided, THE Scaler SHALL transform the features using the previously fitted parameters and return a DataFrame with the same column names and row count as the input
3. IF the Scaler is used for prediction before being fitted on training data, THEN THE Scaler SHALL raise an error indicating the scaler has not been fitted
4. IF prediction features contain a different number of columns than the training features used during fitting, THEN THE Scaler SHALL raise an error indicating a feature shape mismatch
5. IF any training feature column has zero variance, THEN THE Scaler SHALL scale that column to zero without raising an error
6. IF training or prediction features contain NaN values, THEN THE Scaler SHALL raise an error indicating that input contains missing values

### Requirement 5: Train Logistic Regression Model

**User Story:** As a user, I want a Logistic Regression model trained on historical match outcomes, so that it can predict future match results.

#### Acceptance Criteria

1. WHEN scaled training features and binary outcome labels are provided, THE Model SHALL train a Logistic Regression classifier on the data
2. THE Model SHALL use binary labels where 1 represents a home team win and 0 represents a home team loss or draw
3. WHEN training is complete, THE Model SHALL return a prediction probability between 0.0 and 1.0 when provided a new feature vector of the same dimensionality as the training features
4. IF the training dataset contains fewer than 10 Match_Records, THEN THE Model SHALL raise an error indicating insufficient training data
5. IF the training labels contain only a single class, THEN THE Model SHALL raise an error indicating insufficient class variety for training
6. IF the training features contain NaN or infinite values, THEN THE Model SHALL raise an error indicating invalid feature values

### Requirement 6: Output Prediction Probabilities

**User Story:** As a user, I want prediction probabilities for each upcoming match, so that I can see the likelihood of each team winning.

#### Acceptance Criteria

1. WHEN an upcoming match is provided with both teams' scaled features, THE Model SHALL output a Prediction_Output containing the probability of each binary outcome, where each probability is a value between 0.0 and 1.0 inclusive and the two probabilities sum to 1.0
2. THE Prediction_Output SHALL include the home team ID, away team ID, probability of home win, and probability of home loss
3. WHEN multiple upcoming matches are provided, THE Predictor SHALL output a DataFrame with one Prediction_Output row per match
4. THE Predictor SHALL sort prediction results by match date in ascending order
5. IF the Model is used for prediction before being trained on historical data, THEN THE Model SHALL raise an error indicating the model has not been fitted
6. IF an upcoming match references a team with no computed features available, THEN THE Predictor SHALL use the default feature values defined by the Feature_Engine and include that match in the prediction output

### Requirement 7: End-to-End Prediction Pipeline

**User Story:** As a user, I want a single entry point that runs the full prediction pipeline, so that I can get predictions with minimal manual steps.

#### Acceptance Criteria

1. WHEN the Predictor is invoked with a competition ID and API key, THE Predictor SHALL execute the full pipeline (fetch data, parse matches, compute features, scale features, train model, and output predictions) and return a DataFrame of Prediction_Output rows sorted by match date in ascending order
2. THE Predictor SHALL classify matches with status "FINISHED" as completed matches for training and matches with status "SCHEDULED" as upcoming matches for prediction
3. IF no upcoming matches with status "SCHEDULED" are found for prediction, THEN THE Predictor SHALL return an empty DataFrame and log an informational message
4. IF no completed matches are available for training, THEN THE Predictor SHALL raise an error indicating no training data is available
5. IF any pipeline step (API fetch, parsing, feature computation, scaling, or training) raises an error, THEN THE Predictor SHALL propagate that error to the caller without proceeding to subsequent steps
