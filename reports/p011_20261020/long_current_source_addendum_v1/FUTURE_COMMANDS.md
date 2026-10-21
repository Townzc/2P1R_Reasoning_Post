# Future commands only after exact full admission

No actual formal SPEC exists. Do not invoke these commands now. Retain original logical job IDs and all once-only markers. Do not rerun either input constructor or preflight subset constructor.

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_long_current_io.py upload --job JOB --review .local/p011_20261020/r1/LONG_CURRENT_PATH_A1_A2_ACCEPTED.json
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run -m experiments.p011.modal_long_current --job-id JOB --review-json .local/p011_20261020/r1/LONG_CURRENT_PATH_A1_A2_ACCEPTED.json --budget-json EXACT_FRESH_BUDGET --selection-json ACTUAL_SELECTION_IF_REQUIRED
```

For a truly completed original call and actual STOPPED/owned0, use the same p011_long_current_io.py collect, then audit, then score, once per original job. All share the original absolute result window. Analysis uses scripts/analyze_p011_long_current_pair.py, original allowed pair only, after both full results. Unknown or failed calls cannot use completed-only collection or retry.
