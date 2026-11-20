# TaxAid prototype

This project contains three small retrieval experiments for matching student
descriptions with IRS resources. All are prototypes, not tax advice or
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

## MiniLM Semantic Baseline

MiniLM ranks the same resource titles, summaries, and search terms by meaning
rather than exact word overlap. It uses `sentence-transformers/all-MiniLM-L6-v2`
on CPU, with a pinned model revision and normalized embeddings. Resource
embeddings are computed once per process; cosine similarity determines the top
three resources, with ties sorted by resource ID. Scores are not probabilities
or proof of tax applicability. Unlike BM25, MiniLM returns three results even
when their similarities are low or negative.

Install dependencies in a virtual environment, then select MiniLM explicitly:

```bash
python -m pip install -r requirements.txt
python taxaid.py query "I make money creating digital art online." --method minilm
python taxaid.py evaluate --method minilm
python taxaid.py evaluate --method bm25
```

BM25 remains the default and needs no MiniLM dependencies. The first MiniLM run
downloads model files from Hugging Face; subsequent runs reuse the local cache.
Inference is local: no Jev key or hosted inference requests are needed. To force
offline loading after the download, set `HF_HUB_OFFLINE=1`. MiniLM embeds only
the scenario text, never its goal, image filename, or justification. Inputs
longer than the model's 256-token limit are truncated; the current resource
texts fit within that limit. JSON reports include the model ID/revision,
Sentence Transformers version, and maximum sequence length.

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

The local BM25/MiniLM comparison scored **52/60 cases; 8 remain unscored**.
Jev's row is retained from the earlier live run; Jev was not called again.

| Pipeline | Hit rate | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| BM25 | 0.8077 | 0.4006 | 0.7981 | 0.5115 |
| MiniLM | 0.9808 | 0.3526 | 0.9712 | 0.5115 |
| Jev (previous run) | 0.8077 | 0.8077 | 0.7692 | 0.7821 |

These metrics measure agreement with provisional CSV goals, not tax
correctness or performance on a fresh held-out test. MiniLM improves top-three
hit rate, but precision decreases and F1 is unchanged. Jev returns at most one
mapped resource, so its precision/F1 are not an equal-depth ranking comparison.

## More information

- [BM25 prototype guide](docs/prototype-guide.md)
- [Jev guide](docs/jev-guide.md)
