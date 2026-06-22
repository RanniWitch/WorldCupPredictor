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

    print("=" * 60)
    print(f"PREDICTED WINNERS - Next {showing} World Cup 2026 Matches")
    print("=" * 60)
    print()

    for i, (_, row) in enumerate(df.head(showing).iterrows()):
        home = row["home_team_name"]
        away = row["away_team_name"]
        home_prob = row["home_win_prob"]
        draw_prob = row["draw_prob"]
        away_prob = row["away_win_prob"]
        date = row["match_date"].strftime("%b %d, %Y")

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

        print(f"  {i+1}. {home} vs {away}")
        print(f"     Date: {date}")
        if outcome == "Draw":
            print(f"     Predicted Outcome: DRAW ({confidence:.1%} confidence)")
        else:
            print(f"     Predicted Winner: {winner} ({confidence:.1%} confidence)")
        print(f"     Probabilities: {home} {home_prob:.1%} | Draw {draw_prob:.1%} | {away} {away_prob:.1%}")
        print()

    print("=" * 60)

    if num_games > total_available:
        print(f"\n(Only {total_available} scheduled matches available)")


if __name__ == "__main__":
    main()
