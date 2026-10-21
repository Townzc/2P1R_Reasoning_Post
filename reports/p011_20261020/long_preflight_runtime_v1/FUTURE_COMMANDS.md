# Conditional GPU commands — CPU subset DONE; GPU NOT RUN

The CPU command below is historical DONE, MUST NOT RUN AGAIN:

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_long_preflight_inputs.py --review .local/p011_20261020/r1/LONG_PREFLIGHT_SOURCE_CR_ACCEPTED.json
```

The input consumer is permanent once-only; it selects saved tokens/requests without
encoding or loading a model. Its actual outputs and the concrete three-job SPEC
must then be attached to the SAME request for actual A1 and numeric A2-lite.
Fresh full resource rates and D1 accounting are required before entry. For each
original job preflight_S-L15_s17_r1, preflight_S-F15_s17_r1, preflight_S-L3_s17_r1,
only after final exact admission and sufficient original full window:

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_long_preflight_io.py upload --job JOB --review REVIEW
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run -m experiments.p011.long_preflight.modal_entry --job-id JOB --review-json REVIEW --budget-json BUDGET
```

Use actual argparse names from the fixed IO file; no production CLI was invoked
to print help. After that job's original completed result and actual STOPPED0,
collect once, then audit once with data_pipeline Python in the original shared
worker-start+900+7200 absolute closeout window. The IO commands accept `collect`
and `audit`; no scoring command exists. Preserve unknown/partial/failed jobs,
never use a completed-only collector on a failure, and never whole-job retry.
