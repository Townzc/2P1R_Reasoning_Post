# Public math pilot: final results

The complete fixed pilot is closed: 31,203 logical outputs, 54 scored runs,
512 committed updates, 544 physical completed training records, and 31,331
physical generation attempts. The original128 lost attempts and32 lost updates
remain counted. Provider shutdown is confirmed; no further run is queued.

QDW-v0 underperforms DFT and TrimSFT on the predeclared primary MATH average@8
outcome. QDW versus SFT remains inconclusive. Better secondary GSM and Numina-dev
results do not override the primary negative result. This is one training seed,
one small model and a fixed128-update recipe, not a paper-level or SOTA claim.

See [the final Chinese report](FINAL_EXECUTION_SUMMARY_ZH.md) for the full table,
paired uncertainty, development trends, retained failures, cost accounting and
proposed decisions; [FINAL_RESULTS.json](FINAL_RESULTS.json) preserves every
raw-bound per-output score and full-precision aggregate. Unknown judgments stay
in the full denominators;47 MATH judgments remain unresolved after frozen scoring.

The earlier BENCHMARK_COMPLETE_DEV_PENDING files are historical snapshots; all
development evaluation and final reconciliation have now completed.
