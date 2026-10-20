# Future original actions — all NOT RUN

After exact full A2, published source and fresh I budget:

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p010_cue_search_io.py upload --root .local/p010_20261019/r1 --spec reports/p010_20261019/c6_search_runtime_v1/SPEC.json
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run --detach -m experiments.p010.modal_cue_search::main --receipt-dir .local/p010_20261019/r1/cue_search_runs/search_r1 --review-json .local/p010_20261019/r1/C6_SEARCH_A2_ACCEPTED.json --budget-json .local/p010_20261019/r1/C6_SEARCH_BUDGET.json
```

Only originalcompleted RESULT and actualSTOPPED0 allow one collect then records:

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p010_cue_search_io.py collect --receipt .local/p010_20261019/r1/cue_search_runs/search_r1 --out .local/p010_20261019/r1/cue_search_export_r1
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p010_cue_search_io.py records --receipt .local/p010_20261019/r1/cue_search_runs/search_r1 --export .local/p010_20261019/r1/cue_search_export_r1 --out .local/p010_20261019/r1/cue_search_records_r1
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/audit_p010_cue_search.py audit --spec reports/p010_20261019/c6_search_runtime_v1/SPEC.json --receipt .local/p010_20261019/r1/cue_search_runs/search_r1 --export .local/p010_20261019/r1/cue_search_export_r1 --records .local/p010_20261019/r1/cue_search_records_r1 --dev .local/p010_20261019/r1/cue_inputs_r1/DEV_PROMPTS.json --tokenizer .local/midpoint_20261011/data_pipeline/reconstruction_r1/tokenizer --runtime-review .local/p010_20261019/r1/C6_SEARCH_A2_ACCEPTED.json --out .local/p010_20261019/r1/cue_search_oracle_r1
PYTHONPATH=. .local/p009_20261014/r1/math_verify_env/bin/python scripts/audit_p010_cue_search.py select --spec reports/p010_20261019/c6_search_runtime_v1/SPEC.json --oracle .local/p010_20261019/r1/cue_search_oracle_r1 --proposal .local/p010_20261019/r1/cue_search_export_r1/evidence/PROPOSAL.json --dev .local/p010_20261019/r1/cue_inputs_r1/DEV_PROMPTS.json --out .local/p010_20261019/r1/cue_selection_r1
```

Every receipt/intent is create-only; inspect actual process/file state first. No whole-helper retry, model replay or unknown-to-zero conversion. A failed call needs bounded read-only preservation before any exception request; never use completed-only collection on failure. Inputs/source/publications are not overwritten. Actual A3 and selected-cue-bound benchmark entry are still future work.
