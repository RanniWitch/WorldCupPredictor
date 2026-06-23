"""Track prediction accuracy against actual World Cup results.

Two modes:
  1. `python track_results.py save` — Save predictions for all upcoming matches
  2. `python track_results.py check` — Compare saved predictions against actual results

Run `save` before matches start, then `check` after they finish.
Running with no arguments does both: checks results, then saves new predictions.
"""

import os
import csv
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.api_client import APIClient
from src.predictor import Predictor

PREDICTIONS_FILE = Path("data/saved_predictions.csv")
RESULTS_FILE = Path("data/prediction_results.csv")

PREDICTION_HEADERS = [
    "match_date",
    "home_team",
    "away_team",
    "predicted_outcome",
    "predicted_confidence",
    "predicted_home_score",
    "predicted_away_score",
    "home_win_prob",
    "draw_prob",
    "away_win_prob",
    "saved_at",
]

RESULTS_HEADERS = [
    "match_date",
    "home_team",
    "away_team",
    "actual_home_score",
    "actual_away_score",
    "actual_outcome",
    "predicted_outcome",
    "predicted_confidence",
    "predicted_home_score",
    "predicted_away_score",
    "outcome_correct",
    "exact_score_correct",
    "home_win_prob",
    "draw_prob",
    "away_win_prob",
    "checked_at",
]


def get_actual_outcome(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home_win"
    elif home_score == away_score:
        return "draw"
    else:
        return "away_win"


def save_predictions():
    """Save predictions for all upcoming scheduled matches."""
    print("Generating predictions for upcoming matches...")

    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    predictor = Predictor(api_key=api_key)
    df = predictor.run(2000, training_competition_ids=[2018, 2152])

    if df.empty:
        print("No upcoming matches to predict.")
        return

    # Load existing saved predictions to avoid duplicates
    existing_keys = set()
    if PREDICTIONS_FILE.exists():
        with open(PREDICTIONS_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['match_date']}_{row['home_team']}_{row['away_team']}"
                existing_keys.add(key)

    PREDICTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_exists = PREDICTIONS_FILE.exists()

    new_count = 0
    with open(PREDICTIONS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PREDICTION_HEADERS)
        if not file_exists:
            writer.writeheader()

        for _, row in df.iterrows():
            date_str = row["match_date"].strftime("%Y-%m-%d")
            key = f"{date_str}_{row['home_team_name']}_{row['away_team_name']}"

            if key in existing_keys:
                continue

            home_prob = row["home_win_prob"]
            draw_prob = row["draw_prob"]
            away_prob = row["away_win_prob"]

            if home_prob >= draw_prob and home_prob >= away_prob:
                predicted_outcome = "home_win"
                confidence = home_prob
            elif draw_prob >= home_prob and draw_prob >= away_prob:
                predicted_outcome = "draw"
                confidence = draw_prob
            else:
                predicted_outcome = "away_win"
                confidence = away_prob

            writer.writerow({
                "match_date": date_str,
                "home_team": row["home_team_name"],
                "away_team": row["away_team_name"],
                "predicted_outcome": predicted_outcome,
                "predicted_confidence": round(confidence, 4),
                "predicted_home_score": row.get("predicted_home_score", ""),
                "predicted_away_score": row.get("predicted_away_score", ""),
                "home_win_prob": round(home_prob, 4),
                "draw_prob": round(draw_prob, 4),
                "away_win_prob": round(away_prob, 4),
                "saved_at": datetime.now().isoformat(),
            })
            new_count += 1

    print(f"Saved {new_count} new predictions to {PREDICTIONS_FILE}")
    print(f"Total predictions on file: {len(existing_keys) + new_count}")


def check_results():
    """Compare saved predictions against actual finished results."""
    if not PREDICTIONS_FILE.exists():
        print("No saved predictions found. Run `python track_results.py save` first.")
        return

    # Load saved predictions
    saved_predictions = {}
    with open(PREDICTIONS_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = f"{row['match_date']}_{row['home_team']}_{row['away_team']}"
            saved_predictions[key] = row

    # Load already checked results to avoid duplicates
    already_checked = set()
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['match_date']}_{row['home_team']}_{row['away_team']}"
                already_checked.add(key)

    # Fetch finished matches from API
    print("Fetching finished matches...")
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    client = APIClient(api_key)
    data = client.get_matches(2000)

    new_results = []
    for match in data.get("matches", []):
        if match.get("status") != "FINISHED":
            continue

        score = match.get("score", {})
        full_time = score.get("fullTime", {}) if score else {}
        home_score = full_time.get("home")
        away_score = full_time.get("away")

        if home_score is None or away_score is None:
            continue

        home_team = match.get("homeTeam", {}).get("name", "Unknown")
        away_team = match.get("awayTeam", {}).get("name", "Unknown")
        match_date = match.get("utcDate", "")[:10]

        key = f"{match_date}_{home_team}_{away_team}"

        # Only process if we have a prediction and haven't already checked
        if key in saved_predictions and key not in already_checked:
            pred = saved_predictions[key]
            actual_outcome = get_actual_outcome(int(home_score), int(away_score))
            outcome_correct = actual_outcome == pred["predicted_outcome"]
            exact_correct = (
                str(pred.get("predicted_home_score", "")) == str(home_score)
                and str(pred.get("predicted_away_score", "")) == str(away_score)
            )

            new_results.append({
                "match_date": match_date,
                "home_team": home_team,
                "away_team": away_team,
                "actual_home_score": home_score,
                "actual_away_score": away_score,
                "actual_outcome": actual_outcome,
                "predicted_outcome": pred["predicted_outcome"],
                "predicted_confidence": pred["predicted_confidence"],
                "predicted_home_score": pred.get("predicted_home_score", ""),
                "predicted_away_score": pred.get("predicted_away_score", ""),
                "outcome_correct": outcome_correct,
                "exact_score_correct": exact_correct,
                "home_win_prob": pred["home_win_prob"],
                "draw_prob": pred["draw_prob"],
                "away_win_prob": pred["away_win_prob"],
                "checked_at": datetime.now().isoformat(),
            })

    if not new_results:
        print("No new results to check (no finished matches with saved predictions).")
        print_summary()
        return

    # Write new results
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_exists = RESULTS_FILE.exists()

    correct_outcomes = 0
    with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESULTS_HEADERS)
        if not file_exists:
            writer.writeheader()

        for result in new_results:
            writer.writerow(result)
            status = "CORRECT" if result["outcome_correct"] else "WRONG"
            print(f"  [{status}] {result['home_team']} {result['actual_home_score']}-"
                  f"{result['actual_away_score']} {result['away_team']} "
                  f"(predicted: {result['predicted_outcome']}, "
                  f"{float(result['predicted_confidence']):.1%})")
            if result["outcome_correct"]:
                correct_outcomes += 1

    print(f"\nNew: {correct_outcomes}/{len(new_results)} correct "
          f"({correct_outcomes/len(new_results)*100:.1f}%)")
    print()
    print_summary()


def print_summary():
    """Print cumulative accuracy from the results CSV."""
    if not RESULTS_FILE.exists():
        return

    total = 0
    correct = 0
    exact = 0

    with open(RESULTS_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row["outcome_correct"] == "True":
                correct += 1
            if row["exact_score_correct"] == "True":
                exact += 1

    if total > 0:
        print("=" * 60)
        print(f"  CUMULATIVE ACCURACY ({total} matches tracked)")
        print(f"  Outcome accuracy:    {correct}/{total} ({correct/total*100:.1f}%)")
        print(f"  Exact score accuracy: {exact}/{total} ({exact/total*100:.1f}%)")
        print("=" * 60)


def main():
    print()
    print("=" * 60)
    print("  WORLD CUP PREDICTION TRACKER")
    print("=" * 60)
    print()

    args = sys.argv[1:] if len(sys.argv) > 1 else ["check", "save"]

    if "check" in args:
        check_results()
        print()

    if "save" in args:
        save_predictions()


if __name__ == "__main__":
    main()
