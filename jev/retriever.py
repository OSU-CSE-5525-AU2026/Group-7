"""Structured Jev classification for the TaxAid prototype."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


class JevConfigurationError(RuntimeError):
    """Raised when Jev cannot be configured or its question file is invalid."""


class JevResponseError(RuntimeError):
    """Raised when Jev returns a response that cannot be normalized."""


def load_question_spec(path: Path) -> dict[str, dict[str, Any]]:
    """Load the vetted question definitions without changing their wording."""
    try:
        specification = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise JevConfigurationError(f"Unable to load Jev questions: {error}") from error

    if not isinstance(specification, dict) or not specification:
        raise JevConfigurationError("Jev questions must be a nonempty JSON object")
    for question_id, question in specification.items():
        if not isinstance(question_id, str) or not question_id.strip():
            raise JevConfigurationError("Jev question IDs must be nonempty strings")
        if not isinstance(question, dict):
            raise JevConfigurationError(f"Jev question {question_id!r} must be an object")
        if question.get("type") not in {"choice", "noul"}:
            raise JevConfigurationError(f"Unsupported Jev question type for {question_id!r}")
        if not isinstance(question.get("instructions"), str) or not question["instructions"].strip():
            raise JevConfigurationError(f"Jev question {question_id!r} needs instructions")
        criteria = question.get("criteria")
        if question["type"] == "choice" and (
            not isinstance(criteria, dict)
            or not criteria
            or any(not isinstance(key, str) or not isinstance(value, str) for key, value in criteria.items())
        ):
            raise JevConfigurationError(f"Choice question {question_id!r} needs string criteria")
        if question["type"] == "noul" and criteria is not None and (
            not isinstance(criteria, dict)
            or set(criteria) != {"true", "false"}
            or any(not isinstance(value, str) for value in criteria.values())
        ):
            raise JevConfigurationError(f"Noul question {question_id!r} needs true/false criteria")
    return specification


def build_state(scenario: str, image_path: str | None = None) -> dict[str, str]:
    """Build the stable state shape used for Jev requests."""
    scenario = scenario.strip()
    if not scenario:
        raise ValueError("Scenario must not be blank")
    state = {"scenario": scenario}
    if image_path is not None:
        image_path = image_path.strip()
        if not image_path:
            raise ValueError("Image path must not be blank when supplied")
        state["image"] = image_path
    return state


def _value(source: Any, key: str, context: str) -> Any:
    if isinstance(source, Mapping):
        if key in source:
            return source[key]
    else:
        value = getattr(source, key, None)
        if value is not None:
            return value
    raise JevResponseError(f"Jev response is missing {context}.{key}")


def _answer(response: Any, question_id: str, collection: str) -> Any:
    answers = response.get("answers") if isinstance(response, Mapping) else getattr(response, "answers", None)
    if answers is not None:
        try:
            return answers[question_id]
        except (KeyError, TypeError):
            pass
    values = response.get(collection) if isinstance(response, Mapping) else getattr(response, collection, None)
    if values is not None:
        try:
            return values[question_id]
        except (KeyError, TypeError):
            pass
    raise JevResponseError(f"Jev response is missing answer {question_id!r}")


def _number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JevResponseError(f"Jev response field {context} must be numeric")
    if not 0 <= float(value) <= 1:
        raise JevResponseError(f"Jev response field {context} must be between 0 and 1")
    return float(value)


def _build_sdk_questions(
    specification: Mapping[str, Mapping[str, Any]],
    choice_factory: Callable[..., Any] | None = None,
    noul_factory: Callable[..., Any] | None = None,
    noul_criteria_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    if choice_factory is None or noul_factory is None:
        try:
            from typesafe_sdk import Choice, Noul, NoulCriteria
        except ImportError as error:
            raise JevConfigurationError(
                "typesafe-sdk is required for Jev requests; install it with pip install typesafe-sdk"
            ) from error
        choice_factory = Choice
        noul_factory = Noul
        noul_criteria_factory = NoulCriteria

    questions: dict[str, Any] = {}
    for question_id, question in specification.items():
        if question["type"] == "choice":
            questions[question_id] = choice_factory(
                instructions=question["instructions"], criteria=question["criteria"]
            )
        else:
            criteria = question.get("criteria")
            if criteria is None:
                questions[question_id] = noul_factory(instructions=question["instructions"])
            else:
                if noul_criteria_factory is None:
                    raise JevConfigurationError("Noul criteria support is unavailable in the installed SDK")
                questions[question_id] = noul_factory(
                    instructions=question["instructions"],
                    criteria=noul_criteria_factory(**criteria),
                )
    return questions


class JevRetriever:
    """Call Jev and normalize its full-catalog classification response."""

    def __init__(
        self,
        question_path: Path,
        resource_path: Path,
        model: str = "jev-latest",
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.specification = load_question_spec(question_path)
        try:
            resources = json.loads(resource_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise JevConfigurationError(f"Unable to load IRS resources: {error}") from error
        if not isinstance(resources, list) or not resources:
            raise JevConfigurationError("IRS resources must be a nonempty JSON array")
        self._goal_to_resource_ids = {
            goal: resource["id"]
            for resource in resources
            if isinstance(resource, dict)
            for goal in resource.get("csv_goals", [])
        }
        self.model = model
        self._client_factory = client_factory

    def classify(self, scenario: str, image_path: str | None = None) -> dict[str, Any]:
        """Classify a scenario and return Jev's structured probabilities."""
        if image_path is not None:
            raise JevConfigurationError(
                "Image input is reserved for a future multimodal Jev integration"
            )
        state = build_state(scenario, image_path)
        questions = _build_sdk_questions(self.specification)
        if self._client_factory is None:
            try:
                from typesafe_sdk import TypeSafeClient
            except ImportError as error:
                raise JevConfigurationError(
                    "typesafe-sdk is required for Jev requests; install it with pip install typesafe-sdk"
                ) from error
            client_factory = TypeSafeClient
        else:
            client_factory = self._client_factory

        if not os.environ.get("TYPESAFE_API_KEY"):
            raise JevConfigurationError("TYPESAFE_API_KEY is not set")
        with client_factory(model=self.model) as client:
            response = client.system_one(state=state, questions=questions)
        return self._normalize(response)

    def _normalize(self, response: Any) -> dict[str, Any]:
        tax_form = _answer(response, "TaxAid", "choices")
        taxability = _answer(response, "Taxability", "nouls")
        label = _value(tax_form, "choice", "TaxAid")
        probabilities = _value(tax_form, "probabilities", "TaxAid")
        if not isinstance(label, str) or not label.strip() or not isinstance(probabilities, Mapping):
            raise JevResponseError("Jev TaxAid answer has an invalid choice or probability map")
        normalized_probabilities = {str(key): _number(value, f"TaxAid.probabilities[{key!r}]") for key, value in probabilities.items()}
        selected_resource_id = self._goal_to_resource_ids.get(label)
        return {
            "choice": label,
            "resource_id": selected_resource_id,
            "probabilities": normalized_probabilities,
            "confidence": _number(_value(tax_form, "confidence", "TaxAid"), "TaxAid.confidence"),
            "taxability": _number(_value(taxability, "noul", "Taxability"), "Taxability.noul"),
            "unmapped_choice": selected_resource_id is None,
        }


__all__ = [
    "JevConfigurationError",
    "JevResponseError",
    "JevRetriever",
    "build_state",
    "load_question_spec",
]
