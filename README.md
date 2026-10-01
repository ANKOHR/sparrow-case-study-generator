# Sparrow Case Study Generator

Turn completed work into publishable evidence using a deterministic, local Python CLI.
For small business owners and Sparrow, this produces case studies with explicit source
references, permission checks, measured comparisons, and named exclusions.

Hypothesis: a tested deterministic workflow can reliably turn explicit completed-work
records into evidence people can inspect. Synthetic acceptance tests validate computation
and eligibility, not customer demand, source authenticity, or real time returned.

## Quickstart

Python 3.10 or newer and setuptools 68 or newer are required. No runtime dependencies,
network calls, language models, databases, GPU workloads, or random generation are used.
Install using already available local tools:

```powershell
python -m venv --system-site-packages .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --no-index --no-deps --no-build-isolation -e .
scsg fixtures --out demo
scsg run --input demo
scsg report --format md
python -m pytest -q
```

The exact demo sequence on shells that support chaining:

```text
scsg fixtures --out demo && scsg run --input demo && scsg report --format md
```

Use a fresh output directory for fixtures. The generated expectations file is a test
oracle, never a computational input. State is stored in .scsg/results.json relative to
the working directory. It contains the validated original input; report recomputes it.
Use --state to keep different projects separate. The module entrypoint
python -m sparrow_case_study_generator.cli also works if scsg is not on PATH.

## Input format

Use one UTF-8 records.json in an input directory. JSON is the supported input format;
CSV, YAML, JSONL, and unknown files are explicitly rejected. Only expectations.json
may coexist with records.json and is ignored by the engine. An empty directory renders
zero results with an explicit reference date of 2026-09-30, not today's date.

examples/tiny/records.json is the hand-written five-scenario synthetic input.
Henry can copy it, replace the records with his own work, and set synthetic to false
on both the document and each real record. Trial results should stay local.

```json
{
  "schema_version": 1,
  "synthetic": false,
  "as_of": "2026-09-30",
  "records": [{
    "id": "work-001",
    "title": "Replace with Henry's own completed work",
    "status": "completed",
    "completed_on": "2026-09-29",
    "permission": true,
    "synthetic": false,
    "source": "Replace with Henry's own work log reference",
    "evidence": ["Replace with an authorised completion evidence reference"]
  }]
}
```

This template makes no savings claim. It is a schema illustration, not a real work
record or evidence of use. Do not treat it as real data until Henry replaces it.

Required document fields: schema_version (integer 1), synthetic (boolean), as_of
(YYYY-MM-DD), records (array). Optional _comment holds a JSON header comment.
JSON does not allow literal comment lines; fixtures use _comment at the top instead.

Required record fields: id, title, status (completed or draft), completed_on,
permission (boolean publication permission), synthetic (boolean), source (work log
reference), evidence (array of nonempty source references). A record qualifies only
if completed, permitted, and carrying at least one evidence reference.

Optional measurements maps minutes and/or gbp to objects containing baseline,
outcome, and source. Both numbers must be supplied as nonnegative decimal strings,
finite, at most two decimal places and at most 1000000000. Floats are rejected.
Source describes the paired measurement, for example a stopwatch log or ledger.
Comparisons must cover the same work scope and units; the tool cannot verify this.
Only GBP is supported and currency conversion is never inferred.

Optional hypothetical maps minutes and/or gbp to decimal strings. These numbers are
explicitly hypothetical, never included in measured totals, and may coexist with a
paired measurement if Henry wants to compare a hypothesis to supplied outcomes.

Rules: unknown fields, missing fields, duplicate IDs, duplicate JSON keys, invalid
dates, and dates after the explicit as_of cutoff reject the whole input. The reference
date is caller supplied so historical runs are repeatable without consulting a clock.
No records are silently dropped. Drafts, withheld permission, and missing evidence
produce exclusions with reasons. Negative savings are valid regressions; negative
baseline, outcome, or hypothetical values are rejected. IDs allow up to 128 characters;
other text up to 10000. Unicode and Windows reference paths are supported. Em dash
characters and unexpected control characters are rejected. References are text only:
no files, URLs, or source claims are fetched or independently checked.

## Subcommands

| Command | Purpose | Example |
| --- | --- | --- |
| fixtures | Write 200 synthetic records and hand arithmetic expectations | scsg fixtures --out demo |
| run | Validate, compute and save the original input atomically | scsg run --input demo --state .scsg/results.json |
| report | Recompute and render Markdown or JSON with provenance | scsg report --format json --out report.json |
| audit | Show eligibility, exclusion reasons and measurements without saving | scsg audit --input demo |
| case | Render one eligible case as a standalone publishable artifact | scsg case --input demo --id 000-A --format md |

Every subcommand includes --help and an example. Redirect case output to a local
Markdown file for editorial review. A report is permission-gated evidence, not an
automatically approved client testimonial or a narrative invented by a model.
No results are uploaded or published.

## Architecture

```text
fixtures.py -> labelled records.json + expectations.json (test oracle only)
records.json -> cli.py (local parse) -> core.py (validate + compute)
                                       |
                                       v
                            report.py (Markdown / JSON)
run -> atomic state input -> report recomputes -> stdout or atomic output
```

Core functions have no I/O. CLI handles parsing, errors and local atomic writes.
Output keys and records have stable ordering, UTF-8 encoding, and fixed newlines.
There is no random seed because there is no randomness. Outputs do not include
clock timestamps, timings, machine paths, or any inferred figures.

## Honesty boundary and fixture policy

Nothing is discovered, predicted, or estimated. Counts and savings are computed
solely from supplied fields. Measured savings require both baseline and outcome.
Missing measurements produce no measured savings claim. Source truth, ownership,
permission, and measurement quality remain caller declarations. Every report lists
which IDs are synthetic and which are caller-labelled Henry inputs.

Synthetic measurement pairs are illustrative, even when arithmetic is exact.
Aggregated totals include eligible synthetic inputs and must never be presented
as real customer savings. Each synthetic case and every report banner labels this.
Real and synthetic input counts and ID lists remain separate. A mixed document
uses synthetic=false and explicitly labels every record. A synthetic=true document
cannot contain a record labelled real.

All generated fixture files have a first _comment header and synthetic=true.
The fixture has 40 groups of five planted scenarios: A measured completed work,
B measured regression, C draft, D withheld permission, E completed with hypothetical
figures only. Hand arithmetic: 3 eligible per group gives 120 eligible, 80 excluded;
40 * (40 - 5) gives 1400.00 illustrative minutes saved; 40 * 25 gives 1000.00
illustrative GBP saved. E contributes nothing to measured totals. Changing a supplied
measurement or permission changes computed results, even if expectations.json disagrees.

## Failure modes and verification

Malformed JSON produces ParseError with file, line and column. Missing inputs produce
MissingInput with a usage hint. Schema drift produces SchemaError naming the offending
field and input file. Unsupported formats fail explicitly. Read/write failures produce
WriteOrReadError with the filesystem reason. Commands exit 2 on handled errors and 0
on success. Reports are written using a temporary file followed by atomic replacement;
failure preserves the old destination and removes the temporary file. Fixture files
are individually atomic, not a directory transaction; an interrupted generation can
be removed and retried in a fresh directory.

pytest covers planted ground truth, zero false positives, malformed input, duplicates,
schema drift, corrupt fixture values, missing evidence, empty input, exact decimals,
regressions, hypothetical labels, mixed provenance, Unicode, long strings, Windows
references, Markdown escaping, deterministic bytes, all command help, and write failure.
EVIDENCE.md records the local measured test/demo result. These timings describe the
build machine run only, not a guarantee about other machines.

## Evidence-based improvement hook

Start the two-week window on Henry's first real use, not this synthetic build.
Log each run's date, whether used for a real task, number of hand-checked records,
and number of incorrect eligibility decisions or computed measurements. Primary metric:
error rate = incorrect checked records / checked records. Record zero checked records
as unmeasured, never zero percent. Track real usage days alongside accuracy.

After 14 days, if error rate exceeds 10 percent, identify the top failure cause,
fix it and recheck the sample, or kill with a recorded reason. If unused, record
that finding and kill. Use REVIEW.md to record actual counts and the final verdict.
Do not ship Henry's real trial data or claim real savings without paired measurements.

Verdict after the evidence window: expand for daily use or revenue; integrate if heavily
overlapping a sibling project; commercialise if a buyer would pay as-is; maintain as
portfolio evidence otherwise; kill if unused or acceptance criteria cannot be met.
The current two-week verdict is pending: synthetic tests cannot establish those facts.
