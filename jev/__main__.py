"""Command-line entry point for Jev classification."""

import argparse
import csv
import json
from pathlib import Path

from taxaid import BM25, load_cases, load_resources

from .evaluation import evaluate_cases
from .retriever import JevConfigurationError, JevResponseError, JevRetriever

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    query = commands.add_parser("query", help="Classify one student scenario with Jev")
    query.add_argument("scenario", help="Student's tax situation")
    query.add_argument("--image", help="Reserved image path for a future image-enabled request")
    evaluate = commands.add_parser("evaluate", help="Compare Jev's labels with the BM25 baseline")
    evaluate.add_argument(
        "--details",
        action="store_true",
        help="Include item-by-item rankings and metrics in the output",
    )
    args = parser.parse_args(argv)
    try:
        retriever = JevRetriever(
            ROOT / "jev" / "jev_questions.json",
            ROOT / "data" / "irs_resources.json",
        )
        if args.command == "query":
            result = retriever.classify(args.scenario, args.image)
        else:
            resources = load_resources(ROOT / "data" / "irs_resources.json")
            result = evaluate_cases(
                load_cases(ROOT / "test_cases.csv"),
                resources,
                BM25(resources),
                retriever.classify,
                include_cases=args.details,
            )
    except (JevConfigurationError, JevResponseError, ValueError, OSError, csv.Error) as error:
        parser.exit(2, f"jev: {error}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
