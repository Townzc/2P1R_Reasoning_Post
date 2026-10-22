# Future commands: no execution before exact source CR

`R=.local/p011_20261020/r1`; all commands from repository root with PYTHONPATH=.

1. Data environment: `scripts/prepare_p011_forced_answer_inputs.py --spec reports/p011_20261020/forced_answer_preflight_v2/SPEC.json --review $R/FORCED_ANSWER_SOURCE_CR_ACCEPTED.json`. Exactly once; publish actual manifest/roster/prefill/context/weight bindings for real A2-lite before paid work.
2. Modal environment: `scripts/record_p011_forced_answer_budget.py --review $R/FORCED_ANSWER_SOURCE_CR_ACCEPTED.json --runtime-review $R/FORCED_ANSWER_ACTUAL_A2_ACCEPTED.json --directory $R/forced_answer_r1/budget_DATED`. Necessary fresh once; abort if insufficient.
3. Modal environment: `scripts/p011_forced_answer_io.py upload --review $R/FORCED_ANSWER_SOURCE_CR_ACCEPTED.json`. New requests only; no labels/weights.
4. Verify ordinary execution HEAD published; then `.local/midpoint_20261011/venv/bin/modal run experiments/p011/modal_forced_answer.py --source-review $R/FORCED_ANSWER_SOURCE_CR_ACCEPTED.json --runtime-review $R/FORCED_ANSWER_ACTUAL_A2_ACCEPTED.json --budget-json $R/forced_answer_r1/budget_DATED/BUDGET.json`. One attempt. No commit/push between entry and SUBMITTED.
5. After original CLI terminal and app stopped: same IO `collect` once inModalenv. Per complete cell, `audit --cell CELL` once indata_pipelineenv, `score --cell CELL` once inmath_verify_env, with the same source review. Never score partial cells.
6. Analysis environment: `scripts/analyze_p011_forced_answer.py --review $R/FORCED_ANSWER_SOURCE_CR_ACCEPTED.json` once. Publish all available cells/contrasts, unavailable statuses and original references, then real actualA3.

Environment python paths: `.local/midpoint_20261011/venv/bin/python`, `.local/midpoint_20261011/data_pipeline/venv/bin/python`, `.local/p009_20261014/r1/math_verify_env/bin/python`, `.local/p009_20261014/r1/analysis_env/bin/python`.
