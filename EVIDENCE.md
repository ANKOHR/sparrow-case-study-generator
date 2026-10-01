# Local build evidence

Measured on 2026-10-01, Windows, Python 3.12.10, CPU only.

Installed scsg entrypoint: fixtures, run, and Markdown report executed as three
separate processes in a temporary directory. Total observed wall time: 0.750249
seconds for 200 synthetic records, below the five-second acceptance threshold.
No tracebacks. The report carried the data provenance banner.

Hand oracle comparison: 120 publishable cases, 80 exclusions, zero false positives,
zero missed cases. Exact fixture arithmetic: 1400.00 illustrative minutes and
1000.00 illustrative GBP. These are synthetic paired inputs, not real savings.
Measured-pair coverage: 80 cases for minutes, 40 for GBP. Hypothetical claims
were excluded from measured totals.

Reproduce with python scripts/verify_demo.py after local installation.
Timings vary by machine and load. The verifier does not write timings into reports.

Final verification: 43 tests passed in 0.90 seconds. A second installed-entrypoint
demo completed in 0.709874 seconds with the same exact figures and provenance.
The pytest suite covers all required acceptance and adversarial behaviors.
BUILD-DONE.txt records the final test count and verified local implementation commit.

No real customer data, real savings trial, buyer demand, or two-week usage result
has been measured. REVIEW.md is pending the real-use window. Publishing is separate.
