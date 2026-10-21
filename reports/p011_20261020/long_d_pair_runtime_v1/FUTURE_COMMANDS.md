These commands are future-only. Do not execute this known-budget-rejecting candidate. First resolve the explicit numeric disposition, accept exact reviewed bytes, then obtain necessary fresh entry evidence. No D command has run.

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_long_d_pair_io.py upload --job long_D1_S-F15_s17_r1 --review .local/p011_20261020/r1/D_F15_PAIR_A1_A2_ACCEPTED.json
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run -m experiments.p011.modal_long_d_pair --job-id long_D1_S-F15_s17_r1 --review-json .local/p011_20261020/r1/D_F15_PAIR_A1_A2_ACCEPTED.json --budget-json .local/p011_20261020/r1/D_F15_PAIR_D1_FRESH_BUDGET.json
```

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_long_d_pair_io.py upload --job long_D2_S-F15_s17_r1 --review .local/p011_20261020/r1/D_F15_PAIR_A1_A2_ACCEPTED.json
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run -m experiments.p011.modal_long_d_pair --job-id long_D2_S-F15_s17_r1 --review-json .local/p011_20261020/r1/D_F15_PAIR_A1_A2_ACCEPTED.json --budget-json .local/p011_20261020/r1/D_F15_PAIR_D2_FRESH_BUDGET.json
```

After each original successful call, use this same IO entry collect/audit/score once with its exact --job and --review. All share the original worker-start absolute closeout; partial/failed work cannot invoke the completed collector. Reuse original weight-upload evidence; never reupload old model weights. Analysis is one original D1-D2 contrast using scripts/analyze_p011_long_d_pair.py with --left long_D1_S-F15_s17_r1 --right long_D2_S-F15_s17_r1 and the same --review. No A job is available.
