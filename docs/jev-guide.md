# TaxAid-Jev Experiment

This guide explains how to run the Jev experiment from the `Group-7` project
root. Jev is used as a structured classifier; it does not replace the
deterministic BM25 baseline in `taxaid.py`.

## What the Jev module does

The module sends a student's scenario to TypeSafe's Jev model with the vetted
questions in `jev/jev_questions.json`:

- `TaxAid` selects one tax-form label from the full criteria list.
- `Taxability` returns the probability that the scenario may have a federal tax
  reporting, deduction, or credit implication.

The integration returns the selected label, its probability distribution,
confidence, taxability probability, and an exact IRS catalog resource ID when
one exists. Conditional or non-resource labels are returned with
`"unmapped_choice": true`; they are not silently converted into IRS resources.

**Jev output is not legal tax advice or an eligibility determination.**

## Prerequisites

- Python 3.10 or later
- A TypeSafe API key
- A terminal opened in the `Group-7` directory

From PowerShell:

```powershell
Set-Location "path\to\Group-7"
python -m pip install -r requirements.txt
$env:TYPESAFE_API_KEY = "your-key"
```

From Command Prompt:

```bat
cd /d "path\to\Group-7"
python -m pip install -r requirements.txt
set TYPESAFE_API_KEY=your-key
```

Keep the key in the environment only. Do not commit it or place it in a source
file.

## Classify one scenario

Run the `query` subcommand with the student's description:

```bash
python -m jev query "I earned some interest from my bank account."
```

The command prints JSON similar to:

```json
{
  "choice": "Form 1099-INT",
  "resource_id": "1099-int",
  "probabilities": {
    "Form 1099-INT": 0.9
  },
  "confidence": 0.9,
  "taxability": 0.95,
  "unmapped_choice": false
}
```

The exact probabilities depend on the Jev response. The command requires a
live API key *and* network access.

## Compare Jev with BM25

Run the evaluation command:

```bash
python -m jev evaluate
```

By default, this sends every scenario in `test_cases.csv` to Jev and prints a
compact comparison of BM25 and Jev performance. The summary includes Hit@3,
precision, recall, and F1 for each system.

To include the item-by-item rankings, Jev response, and metrics, add
`--details`:

```bash
python -m jev evaluate --details
```

The CSV's `goal` values are provisional evaluation labels, not proof of tax
correctness. The evaluation requires a live API key and can make one Jev
request per scenario.

## Project files

- `jev/jev_questions.json`: vetted Jev question definitions.
- `jev/jev_state.json`: initial scenario/image input shape.
- `jev/retriever.py`: question validation, SDK calls, and response normalization.
- `jev/evaluation.py`: side-by-side Jev and BM25 evaluation.
- `jev/__main__.py`: `query` and `evaluate` CLI commands.
- `data/irs_resources.json`: curated IRS resource catalog and goal mappings.
- `test_cases.csv`: evaluation scenarios.

## Current limitations

- The initial integration is text-only.
- The `--image` option is reserved for a future multimodal implementation and
  currently fails explicitly rather than sending a file path as text.
- Jev's selected label is a classification result, not a filing instruction.
- The current comparison uses the full Jev criteria list; it does not yet
  implement BM25 candidate reranking or a hybrid score.
