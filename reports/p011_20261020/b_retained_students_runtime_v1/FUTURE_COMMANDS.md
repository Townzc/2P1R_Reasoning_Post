Only after exact complete A1/A2 acceptance and fresh budget, once per original B1/B3 job:

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p011_b_students_io.py upload --job B_B1_s17_r1 --review .local/p011_20261020/r1/B_RETAINED_STUDENTS_A1_A2_ACCEPTED.json
P011_B_PHASE=student PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run -m experiments.p011.modal_b_students --job-id B_B1_s17_r1 --review-json .local/p011_20261020/r1/B_RETAINED_STUDENTS_A1_A2_ACCEPTED.json --budget-json .local/p011_20261020/r1/B_B1_FRESH_BUDGET.json
```

Use the actual CLI parser for collect/audit/score after original completion, preserving the same original absolute window. B3 has its distinct original ID and fresh remaining-category admission; never replay B1. No command above has executed.
