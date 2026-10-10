"""Text-only TaxAid prototype: BM25 search and evaluation. Python 3.10+."""

# Author: Group 7 NLP CSE 5525

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
TOP_K = 3
STOPWORDS = set("a an and are as at be been before by for from had has have i in is it me my of on or that the them this to was with year".split())
DISCLAIMER = "Prototype retrieval demo, not tax advice or an eligibility determination. Labels are provisional."


def tokenize(text):
    return [word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOPWORDS]


def load_resources(path):
    resources = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(resources, list) or not resources:
        raise ValueError("Resource index must be a nonempty JSON array")
    ids = set()
    for resource in resources:
        if not isinstance(resource, dict):
            raise ValueError("Every resource must be an object")
        for key in ("id", "title", "url", "summary", "search_terms"):
            if not isinstance(resource.get(key), str) or not resource[key].strip():
                raise ValueError(f"Resource requires a nonempty string: {key}")
        if resource["id"] in ids:
            raise ValueError(f"Duplicate resource ID: {resource['id']}")
        ids.add(resource["id"])
        url = urlparse(resource["url"])
        if url.scheme != "https" or url.netloc != "www.irs.gov":
            raise ValueError("Resource URL must use https://www.irs.gov")
        goals = resource.get("csv_goals")
        if not isinstance(goals, list) or any(not isinstance(g, str) or not g.strip() for g in goals):
            raise ValueError("csv_goals must be a list of nonempty strings")
    return resources


def load_cases(path):
    cases = []
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        fields = reader.fieldnames or []
        if len(set(fields)) != len(fields):
            raise ValueError("CSV contains duplicate column names")
        if not {"scenario", "goal"}.issubset(fields):
            raise ValueError("CSV requires scenario and goal columns")
        for number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed CSV row {number}")
            text = row["scenario"].strip()
            if not text:
                raise ValueError(f"Scenario is required at CSV row {number}")
            cases.append({"row": number, "text": text, "goal": row["goal"].strip()})
    if not cases:
        raise ValueError("CSV contains no scenarios")
    return cases


class BM25:
    """Search titles, summaries, and keywords; never scenario labels."""

    def __init__(self, resources):
        self.resources = resources
        self.documents = [Counter(tokenize(" ".join(r[key] for key in ("title", "summary", "search_terms")))) for r in resources]
        self.lengths = [sum(document.values()) for document in self.documents]
        self.average_length = sum(self.lengths) / len(self.lengths)
        frequencies = Counter(term for document in self.documents for term in document)
        self.idf = {term: math.log(1 + (len(resources) - count + 0.5) / (count + 0.5)) for term, count in frequencies.items()}

    def rank(self, text):
        if not text.strip():
            raise ValueError("Query must not be blank")
        terms = set(tokenize(text))
        ranked = []
        for resource, document, length in zip(self.resources, self.documents, self.lengths):
            matches = sorted(terms & document.keys())
            score = sum(self.idf[term] * document[term] * 2.5 / (document[term] + 1.5 * (0.25 + 0.75 * length / self.average_length)) for term in matches)
            # shortcut: lexical overlap only, upgrade to embeddings for semantic retrieval.
            if score == 0:
                continue
            ranked.append({
                "resource_id": resource["id"], "title": resource["title"],
                "url": resource["url"], "score": score, "matched_terms": matches,
                "explanation": f"Matching query terms: {', '.join(matches)}. Resource summary: {resource['summary']} This match does not establish applicability.",
            })
        ranked.sort(key=lambda result: (-result["score"], result["resource_id"]))
        return [{"rank": rank, **result} for rank, result in enumerate(ranked[:TOP_K], start=1)]


def metrics(ranking, expected):
    if not expected:
        raise ValueError("Metrics require nonempty relevance labels")
    retrieved = {result["resource_id"] for result in ranking[:TOP_K]}
    expected = set(expected)
    hits = len(retrieved & expected)
    precision = hits / len(retrieved) if retrieved else 0.0
    recall = hits / len(expected)
    return {
        "hit_rate": float(hits > 0), "precision": precision, "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def evaluate(cases, index):
    goals = defaultdict(set)
    for resource in index.resources:
        for goal in resource["csv_goals"]:
            goals[goal].add(resource["id"])
    records = []
    for case in cases:
        ranking = index.rank(case["text"])
        expected = sorted(goals.get(case["goal"], set()))
        records.append({**case, "expected_resources": expected, "ranking": ranking,
                        "metrics": metrics(ranking, expected) if expected else None})
    scored = [record["metrics"] for record in records if record["metrics"] is not None]
    return {
        "top_k": TOP_K, "total_cases": len(records), "evaluated_cases": len(scored),
        "unscored_cases": len(records) - len(scored),
        "metrics": {key: sum(item[key] for item in scored) / len(scored) for key in scored[0]} if scored else None,
        "cases": records,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    query = commands.add_parser("query", help="Search a custom student description")
    query.add_argument("text")
    commands.add_parser("evaluate", help="Search the CSV scenarios and check draft goals")
    args = parser.parse_args(argv)
    try:
        index = BM25(load_resources(ROOT / "data/irs_resources.json"))
        if args.command == "query":
            report = {"query": args.text, "top_k": TOP_K, "ranking": index.rank(args.text)}
        else:
            report = evaluate(load_cases(ROOT / "test_cases.csv"), index)
        print(json.dumps({"disclaimer": DISCLAIMER, **report}, indent=2))
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(2, f"taxaid: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
