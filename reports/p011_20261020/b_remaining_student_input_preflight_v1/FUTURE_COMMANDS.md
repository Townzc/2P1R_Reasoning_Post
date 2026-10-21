# Future one-time CPU input command

Only after full actual6400 A3 plus the exact92-source input preparation CR:

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_b_remaining_student_inputs.py --review .local/p011_20261020/r1/B_REMAINING_STUDENT_INPUT_CR_ACCEPTED.json --generation-review .local/p011_20261020/r1/B_COMPLETE6400_ACTUAL_A3_ACCEPTED.json
```

No generation mode, new model, new score, old input encoding or original-output
retry is available. Absent actual result/A3 is a hard stop; no fabricated empty
outputs or early constructor invocation. Exact student input A1/numeric follows.
