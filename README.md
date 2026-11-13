# TaxAid prototype

This project contains two small retrieval experiments for matching student
descriptions with IRS resources. Both are prototypes, not tax advice or
eligibility determinations.

Run these commands from the `Group-7` directory.

## BM25 Baseline

The original text-only baseline uses keyword search and returns up to three
ranked IRS resources. It tokenizes each description, searches resource titles,
summaries, and manually added search terms, then ranks lexical matches with
BM25.

```bash
python taxaid.py query "I make money creating digital art online."
python taxaid.py evaluate
```

## Jev Experiment

The Jev path uses TypeSafe's structured model with the vetted questions in
`jev/jev_questions.json`. It sends the scenario as state, asks a `Choice`
question for the tax-form label and a `Noul` question for taxability, then
normalizes Jev's probabilities and confidence. It evaluates the full question
criteria and does not replace the BM25 baseline.

```bash
python -m pip install -r requirements.txt
set TYPESAFE_API_KEY=your-key

python -m jev query "I worked a paid internship during the school year."
python -m jev evaluate
python -m jev evaluate --details
```

The default Jev evaluation prints summary performance metrics alongside BM25;
`--details` adds item-by-item results. Jev currently accepts text only.

## Data

Both pipelines use the curated catalog in `data/irs_resources.json`: 14 IRS
resources with official links, short summaries, categories, and manually added
search terms. Evaluation uses the 60 scenarios in `test_cases.csv`; the
`scenario` and draft `goal` columns are used for scoring. BM25 ignores the
image column, and Jev is currently text-only. The Jev questions are maintained
separately in `jev/jev_questions.json`.

## Latest Results

The latest terminal run was:

**Cases:** 52/60 scored; 8 unscored.

| Pipeline | Hit rate | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| BM25 | 0.8077 | 0.4006 | **0.7981** | 0.5115 |
| Jev | 0.8077 | **0.8077** | 0.7692 | **0.7821** |

These metrics measure agreement with provisional CSV goals, not tax
correctness. Jev's current run matches BM25 on hit rate while producing higher
precision and F1.

## More information

- [BM25 prototype guide](docs/prototype-guide.md)
- [Jev guide](docs/jev-guide.md)
