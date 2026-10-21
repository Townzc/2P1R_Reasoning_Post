# Commands only after real exact acceptance

Do not recopy inputs or upload. `prepare_p011_c1_inputs.py` and original upload remain consumed.

After the fixed complete CR/input-A1/numeric A2 report, fresh admitted D1 evidence, published acceptance and one independent remote verification, run exactly once:

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run -m experiments.p011.c1_r2.modal_entry --review-json .local/p011_20261020/r1/C1_R2_PATH_A1_A2_ACCEPTED.json --budget-json .local/p011_20261020/r1/C1_R2_BUDGET_CHECK.json
```

Persist original CLI/app/call IDs and actual worker start. Unknown or partial permanently prevents resend. Failed parent r1 stays failed; its reservation stays. Do not poll consumed r1 or reupload original inputs.

Only after the actual original r2 result is complete and app STOPPED/owned0, each once in order:

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_c1_r2_io.py collect --review .local/p011_20261020/r1/C1_R2_PATH_A1_A2_ACCEPTED.json
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_c1_r2_io.py audit --review .local/p011_20261020/r1/C1_R2_PATH_A1_A2_ACCEPTED.json
```

These share the original worker start +1500+7200 absolute deadline, capped by Oct22 05UTC, each local call at most3600. No new forward/statistics in closure. On failure preserve original evidence; completed-only collector is forbidden. A real actual-result review remains later.
