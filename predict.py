"""Print the predicted winners of upcoming World Cup matches."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from src.predictor import Predictor


def main():
    num_games = input("How many upcoming games would you like predictions for? ")
    try:
        num_games = int(num_games)
    except ValueError:
        print("Please enter a valid number.")
        sys.exit(1)

    if num_games < 1:
        print("Please enter a number greater than 0.")
        sys.exit(1)

    print("\nFetching predictions... (this may take a moment)\n")

    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    predictor = Predictor(api_key=api_key)
    df = predictor.run(2000, training_competition_ids=[2018, 2152])

    if df.empty:
        print("No scheduled matches found.")
        return

    total_available = len(df)
    showing = min(num_games, total_available)

    print("=" * 70)
    print(f"  WORLD CUP 2026 PREDICTIONS - Next {showing} Matches")
    print("=" * 70)
    print()

    for i, (_, row) in enumerate(df.head(showing).iterrows()):
        home = row["home_team_name"]
        away = row["away_team_name"]
        home_prob = row["home_win_prob"]
        draw_prob = row["draw_prob"]
        away_prob = row["away_win_prob"]
        date = row["match_date"].strftime("%b %d, %Y")

        # Win/Draw/Loss prediction
        if home_prob >= draw_prob and home_prob >= away_prob:
            winner = home
            confidence = home_prob
            outcome = "Win"
        elif draw_prob >= home_prob and draw_prob >= away_prob:
            winner = "Draw"
            confidence = draw_prob
            outcome = "Draw"
        else:
            winner = away
            confidence = away_prob
            outcome = "Win"

        # Goals predictions
        pred_home_goals = int(row["predicted_home_goals"])
        pred_away_goals = int(row["predicted_away_goals"])
        pred_score_prob = row["predicted_score_prob"]
        exp_home = row["expected_home_goals"]
        exp_away = row["expected_away_goals"]
        over_2_5 = row["over_2_5_prob"]
        over_3_5 = row["over_3_5_prob"]
        top_scorelines = row["top_scorelines"]

        print(f"  {i+1}. {home} vs {away}")
        print(f"     Date: {date}")
        print()

        # Result prediction
        if outcome == "Draw":
            print(f"     🏆 Predicted Outcome: DRAW ({confidence:.1%} confidence)")
        else:
            print(f"     🏆 Predicted Winner: {winner} ({confidence:.1%} confidence)")
        print(f"     Win Probabilities: {home} {home_prob:.1%} | Draw {draw_prob:.1%} | {away} {away_prob:.1%}")
        print()

        # Scoreline prediction
        print(f"     ⚽ Predicted Score: {home} {pred_home_goals} - {pred_away_goals} {away} ({pred_score_prob:.1%} probability)")
        print(f"     Expected Goals: {home} {exp_home:.1f} | {away} {exp_away:.1f} | Total {exp_home + exp_away:.1f}")
        print()

        # Over/Under
        print(f"     📊 Over/Under:")
        print(f"        Over 2.5 goals: {over_2_5:.1%}")
        print(f"        Over 3.5 goals: {over_3_5:.1%}")
        print()

        # Top scorelines
        print(f"     📋 Most Likely Scorelines:")
        for home_g, away_g, prob in top_scorelines[:3]:
            print(f"        {home} {home_g} - {away_g} {away} ({prob:.1%})")
        print()
        print("-" * 70)
        print()

    print("=" * 70)

    if num_games > total_available:
        print(f"\n(Only {total_available} scheduled matches available)")


if __name__ == "__main__":
    main()
