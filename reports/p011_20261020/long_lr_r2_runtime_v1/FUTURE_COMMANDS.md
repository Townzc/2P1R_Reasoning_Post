Only after exact complete review, necessary fresh budget, unused original r2 fences and full windows. No command has run.

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_long_lr_r2_io.py upload --job long_A7_S-F15_s17_r2 --review .local/p011_20261020/r1/LONG_LR_R2_A1_A2_ACCEPTED.json
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run -m experiments.p011.modal_long_lr_r2 --job-id long_A7_S-F15_s17_r2 --review-json .local/p011_20261020/r1/LONG_LR_R2_A1_A2_ACCEPTED.json --budget-json .local/p011_20261020/r1/LONG_LR_R2_F15_FRESH_BUDGET.json
```

The first command registers the exact original upload receipt under a new fence; it performs no old transfer/readback. Baseline uses long_baseline_S-L15_s17_r2 and its own fresh budget/fence. After each original call completes once, use this same IO entry collect/audit/score with --job and --review. Their windows derive from that original worker start; never reset. Exact fresh entry may refuse before launch if any rate, reserve, window, source or evidence no longer matches. No later A/D jobs are allowed.
