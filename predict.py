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
        loss_prob = row["home_loss_prob"]
        date = row["match_date"].strftime("%b %d, %Y")

        if home_prob > loss_prob:
            winner = home
            confidence = home_prob
        else:
            winner = away
            confidence = loss_prob

        print(f"  {i+1}. {home} vs {away}")
        print(f"     Date: {date}")
        print(f"     Predicted Winner: {winner} ({confidence:.1%} confidence)")
        print()

    print("=" * 60)

    if num_games > total_available:
        print(f"\n(Only {total_available} scheduled matches available)")


if __name__ == "__main__":
    main()
