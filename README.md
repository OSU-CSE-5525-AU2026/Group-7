# TaxAid prototype

**This is just a prototype.** It takes a student's description and returns up to
three matching IRS resources. It's text-only, doesn't use images, and isn't tax
advice or tax-preparation software.

For the longer explanation, see [the prototype guide](docs/prototype-guide.md).

## Try it

```bash
python taxaid.py query "I make money creating digital art online."
python taxaid.py evaluate
```

## How it works

```text
Description → split into words → BM25 keyword search → ranked IRS resources
```

The script searches resource titles, summaries, and manually added keywords.
BM25 scores matching words using their frequency, rarity, and document length.
Results include scores, official links, matching words, and short summary-based
explanations. No matching words means an empty list.

- **`query`** searches your custom description.
- **`evaluate`** runs the CSV scenarios through the same search, then compares
  results with their draft `goal` labels. Goals never enter search scoring.

There is no model training. Search is literal: `delivery` and `delivering`, for
example, are different words to this version.

## Where the data came from

- **`data/irs_resources.json`:** 14 resources selected from the project handoff
  and initial scenarios. Summaries come from official IRS overview pages;
  student-friendly keywords were added manually. Full documents aren't indexed,
  and IRS links aren't fetched while the script runs.
- **`test_cases.csv`:** 60 scenarios written by six teammates, 10 each. Only
  `scenario` and `goal` are used. Other columns, including images, are ignored.

The first 40 cases helped shape the catalog and keywords, so they aren't an
independent test. The later 20 were evaluated without changing the catalog.

## Current results and limits

**52 cases are scored; eight goals are unmapped and excluded from metrics.**
Those eight contain non-resource answers or conditional wording that the exact
label mapping doesn't recognize. They remain visible in the output.

An expected resource appears in the first three results for **44 of 52 scored
cases (84.6%)**. Metrics are averaged across scored cases.

These scores measure agreement with draft answers, not tax correctness. Labels
still need independent review, and the explanations don't establish that a
resource applies. We haven't tested images, semantic models, or whether the
explanations help users. Neither project research claim has been demonstrated.

For now, this gives us a simple input-to-output pipeline to run and improve.
