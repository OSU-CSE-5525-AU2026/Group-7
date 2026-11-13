import json
from pathlib import Path

import pytest

from jev.evaluation import evaluate_cases
from jev.retriever import (
    JevConfigurationError,
    JevResponseError,
    JevRetriever,
    build_state,
    load_question_spec,
    _build_sdk_questions,
)

ROOT = Path(__file__).resolve().parents[1]


def test_loads_vetted_questions_without_rewriting_criteria():
    path = ROOT / "jev" / "jev_questions.json"
    specification = load_question_spec(path)
    assert specification["TaxAid"]["criteria"]["Schedule C (Form 1040)"].startswith("Reports income")
    assert specification["Taxability"]["criteria"]["true"].startswith("The activity may involve")


def test_build_state_rejects_blank_scenario_and_preserves_optional_image():
    assert build_state("  earned bank interest  ", "receipt.png") == {
        "scenario": "earned bank interest",
        "image": "receipt.png",
    }
    with pytest.raises(ValueError, match="Scenario"):
        build_state(" ")


def test_build_sdk_questions_preserves_question_shapes():
    class Question:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    built = _build_sdk_questions(
        {
            "choice": {"type": "choice", "instructions": "Pick", "criteria": {"a": "A"}},
            "noul": {
                "type": "noul",
                "instructions": "Check",
                "criteria": {"true": "yes", "false": "no"},
            },
        },
        choice_factory=Question,
        noul_factory=Question,
        noul_criteria_factory=lambda **kwargs: kwargs,
    )
    assert built["choice"].kwargs["criteria"] == {"a": "A"}
    assert built["noul"].kwargs["criteria"] == {"true": "yes", "false": "no"}


def test_normalizes_new_and_legacy_response_shapes(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")

    class Client:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def system_one(self, **kwargs):
            return {
                "choices": {
                    "TaxAid": {
                        "choice": "Form W-2",
                        "probabilities": {"Form W-2": 0.9},
                        "confidence": 0.9,
                    }
                },
                "nouls": {"Taxability": {"noul": 0.8}},
            }

    retriever = JevRetriever(
        ROOT / "jev" / "jev_questions.json",
        ROOT / "data" / "irs_resources.json",
        client_factory=Client,
    )
    monkeypatch.setattr("jev.retriever._build_sdk_questions", lambda specification: {})
    result = retriever.classify("I worked a paid internship")
    assert result["choice"] == "Form W-2"
    assert result["resource_id"] == "w2"
    assert result["taxability"] == 0.8
    assert result["unmapped_choice"] is False


def test_missing_api_key_is_explicit(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    retriever = JevRetriever(
        ROOT / "jev" / "jev_questions.json",
        ROOT / "data" / "irs_resources.json",
        client_factory=lambda **kwargs: None,
    )
    monkeypatch.setattr("jev.retriever._build_sdk_questions", lambda specification: {})
    with pytest.raises(JevConfigurationError, match="TYPESAFE_API_KEY"):
        retriever.classify("I earned interest")


def test_image_input_is_explicitly_reserved(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    retriever = JevRetriever(
        ROOT / "jev" / "jev_questions.json",
        ROOT / "data" / "irs_resources.json",
        client_factory=lambda **kwargs: None,
    )
    with pytest.raises(JevConfigurationError, match="Image input"):
        retriever.classify("I earned interest", "receipt.png")


def test_invalid_probability_is_rejected():
    retriever = JevRetriever(
        ROOT / "jev" / "jev_questions.json",
        ROOT / "data" / "irs_resources.json",
    )
    with pytest.raises(JevResponseError, match="between 0 and 1"):
        retriever._normalize(
            {
                "answers": {
                    "TaxAid": {
                        "choice": "Form W-2",
                        "probabilities": {"Form W-2": 1.2},
                        "confidence": 0.9,
                    },
                    "Taxability": {"noul": 0.8},
                }
            }
        )


def test_evaluation_keeps_unscored_cases_out_of_hit_rates():
    class FakeBM25:
        def rank(self, text):
            return [{"resource_id": "w2"}]

    resources = [{"id": "w2", "csv_goals": ["Form W-2"]}]
    cases = [
        {"row": 2, "text": "paid internship", "goal": "Form W-2"},
        {"row": 3, "text": "loan proceeds", "goal": "No form required for loan proceeds"},
    ]
    report = evaluate_cases(
        cases,
        resources,
        FakeBM25(),
        lambda text: {"resource_id": "w2"},
    )
    assert report["evaluated_cases"] == 1
    assert report["unscored_cases"] == 1
    assert report["metrics"]["jev"]["hit_rate"] == 1.0
    assert "cases" not in report

    detailed = evaluate_cases(
        cases,
        resources,
        FakeBM25(),
        lambda text: {"resource_id": "w2"},
        include_cases=True,
    )
    assert len(detailed["cases"]) == 2
    assert detailed["cases"][0]["jev_metrics"]["f1"] == 1.0
