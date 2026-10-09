# TaxAid prototype guide

**This is just a prototype.** It takes a student's description, searches a small
catalog of IRS resources, and returns the **top three matches** to show a simple
input-to-output pipeline.

## Try it

```bash
# Search your own description
python taxaid.py query "I make money creating digital art online."

# Search the CSV scenarios and compare results with their draft goals
python taxaid.py evaluate
```

The art example puts Schedule C first. A description about interest from a
savings account puts Form 1099-INT first.

## The basic pipeline

```text
Student description → split into words → BM25 search → top three IRS resources
```

1. **Build the word index.** Combine each resource's title, summary, and added
   keywords. Lowercase the text, split it into words/numbers, remove some common
   words, and count what's left.
2. **Search the description.** BM25 is a standard keyword-search algorithm.
   Matching words that are rare across the catalog generally count more than
   common ones. Word frequency and description length also affect the score. Its
   settings stay fixed at `k1=1.5` and `b=0.75`.
3. **Return the matches.** Results include ranks, scores, resource IDs, titles,
   official links, matching words, and summary-based explanations. Ties are
   sorted by resource ID. No matching words means an empty result list.

For `I make money creating digital art online.`, Schedule C matches words like
`digital`, `art`, and `online`. That explains the search result—it doesn't prove
that Schedule C applies to the person. The scores aren't probabilities.

**There was no model training.** BM25 calculates word statistics from the
catalog; it doesn't learn from the CSV's answers. This version doesn't use a
trained or pretrained neural model. It's fairly literal: `delivery` and
`delivering` are different words to it.

### `query` versus `evaluate`

Both use the same search:

- **`query`** searches your custom description. It doesn't read the scenario CSV
  or measure accuracy because there's no expected answer.
- **`evaluate`** searches each CSV description, then compares its top three
  results with that row's `goal`.

```text
CSV scenario → search → ranked results → compare with CSV goal → metrics
```

The search never uses the goals as hints. It also ignores the author, image,
justification, guess, reasoning, and category fields.

Evaluation checks the input format and keeps each case's CSV row number, text,
goal, expected resource IDs, ranking, and metrics. Unmapped goals get
`metrics: null` and are counted separately rather than silently scored as
failures. There's no image audit, category breakdown, or file hashing now.

## Where the data came from

### Our scenarios

Six teammates contributed 10 cases each.

The script needs only the **`scenario` and `goal` columns**:

- `scenario` is the description we search with and can't be blank.
- `goal` is the draft expected IRS resource or resources. A blank or
  unrecognized goal leaves the case unscored.

### The resource catalog

`data/irs_resources.json` was put together manually for this prototype:

1. Use the handoff and initial CSV goals to pick student-relevant IRS resources.
2. Read official IRS overview pages and write short summaries.
3. Keep the official IRS links alongside those summaries.
4. Add everyday keywords such as `internship`, `art`, and `savings`.
5. Map the CSV's goal wording to resource IDs so evaluation can check results.

This isn't a downloaded IRS database or a search of the whole IRS website. We
only search the **title, summary, and `search_terms`** in these 14 entries—not
full forms or instructions. The program doesn't open the IRS links while
running.

| Resource      | Example added keywords                          |
| ------------- | ----------------------------------------------- |
| Schedule C    | freelance, art, digital, tutoring, delivery     |
| Form W-2      | internship, wages, campus, job, paycheck        |
| Form 1098-T   | university, tuition, financial aid, scholarship |
| Form 1099-INT | bank, savings, account, interest                |
| Form 8949     | sold, investments, stocks, proceeds             |
| Schedule D    | stocks, gains, losses, capital assets           |
| Form 8863     | tuition, classes, textbooks, education credit   |
| Schedule 1    | student loans, payments, prize, research study  |
| Form 1040     | taxable scholarship, housing, meals, dorm       |
| Form 8233     | international, nonresident, treaty, withholding |
| Schedule A    | itemized, medical, health insurance, expenses   |
| Schedule SE   | self employment, net earnings, social security  |
| Form 1098-E   | student loan, lender, interest, repayment       |
| Form 1099-B   | broker, stocks, investments, proceeds           |

The keywords are manually added search vocabulary.

Each entry's `id` identifies the resource, `url` links to the IRS, and
`csv_goals` maps exact goal strings to its ID. `category` and the optional
`source_url` are kept in the catalog as background information but aren't used
by this script.

**The first 40 cases helped shape the catalog and keywords.** Their results
aren't an independent test, even though no model was trained. The later 20 were
run without changing the catalog. A final evaluation needs a fixed catalog and
new, independently reviewed cases.

## What we mean by draft labels

The `goal` column is our current expected answer, not a confirmed requirement to
file a form. The labels haven't been independently checked against official IRS
materials yet or domain experts.

So the scores measure **agreement with our draft answers**, not tax correctness.
These eight goals currently need review:

| CSV row | Goal                                                   |
| ------- | ------------------------------------------------------ |
| 24      | No form required if sold at a loss                     |
| 30      | No federal employee expense deduction generally        |
| 42      | No form required for loan proceeds                     |
| 53      | No form required solely for purchase                   |
| 54      | Schedule C (Form 1040) if sole proprietor              |
| 55      | Form 4562 and Schedule C (Form 1040) if self-employed  |
| 56      | Form 8949 and Schedule D (Form 1040) if sold at a gain |
| 57      | Form 8863 if eligible                                  |

The first four need a policy for non-resource answers. The last four include
conditions that the exact-string mapping doesn't recognize.

## Current results

Of 60 cases, **52 are scored and eight are unscored**. An expected resource
appears in the first three results for **44 of the 52 scored cases**.

| Hit rate @3 | Precision | Recall | F1     |
| ----------- | --------- | ------ | ------ |
| 0.8462      | 0.4167    | 0.8365 | 0.5340 |

- **Hit rate:** did any expected resource appear in the first three results?
- **Precision:** what fraction of returned resources were labeled relevant?
- **Recall:** what fraction of expected resources were returned?
- **F1:** the harmonic mean of precision and recall.

These are calculated per scored case and then averaged equally across cases.
Precision uses the actual returned count if there are fewer than three results.
Empty results score 0; unmapped goals are excluded and counted separately.

The primary top-three scores are unchanged by simplifying the script. Earlier
saved reports used a different format and included image checks, category
scores, and other top-k values. They're historical snapshots, not the current
output.

## What's still missing?

- Reviewed labels, complete resource coverage, and clear tax-year assumptions.
- A final test set that wasn't used to choose keywords.
- Semantic model that handles more than literal words.
- Actual multimodal image processing
- A user study to see whether the explanations actually help people.

The next useful step is to have two teammates independently review each case
using official IRS materials, record all relevant resources and assumptions, and
have a third teammate settle disagreements. Then freeze the data and catalog
before comparing more advanced approaches.

For now, this is just a small, text-only search prototype.
