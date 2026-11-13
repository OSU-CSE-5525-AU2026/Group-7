"""Side-by-side Jev and BM25 evaluation for the TaxAid prototype."""

from collections import defaultdict
from collections.abc import Callable, Mapping
from typing import Any

from taxaid import BM25, metrics


def evaluate_cases(
    cases: list[dict[str, Any]],
    resources: list[dict[str, Any]],
    bm25: BM25,
    classify: Callable[[str], Mapping[str, Any]],
    include_cases: bool = False,
) -> dict[str, Any]:
    """Compare Jev's selected label with BM25 and optionally include each case."""
    goals: defaultdict[str, set[str]] = defaultdict(set)
    for resource in resources:
        for goal in resource.get("csv_goals", []):
            goals[goal].add(resource["id"])

    records = []
    for case in cases:
        expected = sorted(goals.get(case["goal"], set()))
        bm25_ranking = bm25.rank(case["text"])
        jev_result = dict(classify(case["text"]))
        jev_ranking = (
            [{"resource_id": jev_result["resource_id"]}]
            if jev_result.get("resource_id") is not None
            else []
        )
        records.append(
            {
                **case,
                "expected_resources": expected,
                "bm25_ranking": bm25_ranking,
                "bm25_metrics": metrics(bm25_ranking, expected) if expected else None,
                "jev": jev_result,
                "jev_metrics": metrics(jev_ranking, expected) if expected else None,
            }
        )

    scored = [record for record in records if record["expected_resources"]]
    report = {
        "total_cases": len(records),
        "evaluated_cases": len(scored),
        "unscored_cases": len(records) - len(scored),
        "metrics": {
            "bm25": _average_metrics(scored, "bm25_metrics"),
            "jev": _average_metrics(scored, "jev_metrics"),
        },
    }
    if include_cases:
        report["cases"] = records
    return report


def _average_metrics(records: list[dict[str, Any]], key: str) -> dict[str, float] | None:
    if not records:
        return None
    metric_names = ("hit_rate", "precision", "recall", "f1")
    return {
        name: sum(record[key][name] for record in records) / len(records)
        for name in metric_names
    }
