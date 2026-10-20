# Only after true exact A1/A2 and issued original A4

Upload once with `scripts/p010_seed29_input_io.py --root .local/p010_20261019/r1 --spec reports/p010_20261019/seed29_runtime_v1/SPEC.json` using the Modal environment; partial output forbids whole-helper retry.

Single entry per original run: `modal run --detach -m experiments.p010.modal_students_seed29::main --run RUN --receipt-dir .local/p010_20261019/r1/student_runs/RUN --data-review-json ACTUAL_A1 --runtime-review-json ACTUAL_A2 --a4-report-json ISSUED_A4 --actual-results-review-json ACTUAL_C9_A3 --budget-json FRESH_BUDGET`. Require first SUBMITTED before next, shared max4 and actual fullwindow. Read actual args and existing directories before use.

After original result and actual STOPPED0: existing `scripts/p010_transfer.py collect` once into a new export. Then `scripts/audit_p010_seed29.py records` and `audit`, the latter with exact spec/input/run/tokenizer/gold/A1/A2/actual-results-review/A4-report and new output. Then `scripts/score_p010_seed29.py` once using the frozen math_verify_env. All actual argument schemas are snapshotted. No completed old operation is repeated. Actual new result A3 follows full evidence.
