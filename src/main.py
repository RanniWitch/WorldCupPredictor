"""Main entry point for the World Cup Predictor CLI."""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv(override=True)

from src.exceptions import (
    APIError,
    AuthenticationError,
    InsufficientDataError,
    NoTrainingDataError,
    RateLimitError,
    WorldCupPredictorError,
)
from src.predictor import Predictor


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list to parse (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with competition_id and api_key.
    """
    parser = argparse.ArgumentParser(
        description="Predict FIFA World Cup match outcomes using Logistic Regression.",
        prog="world-cup-predictor",
    )
    parser.add_argument(
        "--competition-id",
        type=int,
        required=True,
        help="Football-data.org competition ID (e.g., 2000 for FIFA World Cup).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help=(
            "Football-data.org API key. "
            "Can also be set via the FOOTBALL_DATA_API_KEY environment variable."
        ),
    )
    parser.add_argument(
        "--training-competitions",
        type=int,
        nargs="*",
        default=None,
        help=(
            "Additional competition IDs to use for training data. "
            "Useful when the target competition has few finished matches. "
            "Example: --training-competitions 2018 (Euro Championship)."
        ),
    )
    return parser.parse_args(argv)


def resolve_api_key(args: argparse.Namespace) -> str:
    """Resolve the API key from arguments or environment variable.

    Args:
        args: Parsed arguments namespace.

    Returns:
        The resolved API key string.

    Raises:
        SystemExit: If no API key is provided via argument or environment.
    """
    api_key = args.api_key or os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        print(
            "Error: API key is required. Provide --api-key or set "
            "the FOOTBALL_DATA_API_KEY environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)
    return api_key


def main(argv: list[str] | None = None) -> int:
    """Run the World Cup Predictor pipeline.

    Args:
        argv: Optional argument list for testing (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 for errors.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    args = parse_args(argv)
    api_key = resolve_api_key(args)

    try:
        predictor = Predictor(api_key)
        results = predictor.run(
            args.competition_id,
            training_competition_ids=args.training_competitions,
        )

        if results.empty:
            print("No upcoming matches found for prediction.")
            return 0

        print(f"\nPredictions for competition {args.competition_id}:")
        print("=" * 70)
        display_cols = ["home_team_name", "away_team_name", "home_win_prob", "home_loss_prob", "match_date"]
        print(
            results[display_cols].to_string(
                index=False,
                float_format=lambda x: f"{x:.2%}",
            )
        )
        print("=" * 70)
        print(f"\n{len(results)} match prediction(s) generated.")
        return 0

    except AuthenticationError as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        return 1

    except RateLimitError as e:
        print(f"Rate limit exceeded: {e}", file=sys.stderr)
        return 1

    except APIError as e:
        print(f"API error: {e}", file=sys.stderr)
        return 1

    except NoTrainingDataError as e:
        print(f"No training data available: {e}", file=sys.stderr)
        return 1

    except InsufficientDataError as e:
        print(f"Insufficient data for training: {e}", file=sys.stderr)
        return 1

    except WorldCupPredictorError as e:
        print(f"Prediction error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
