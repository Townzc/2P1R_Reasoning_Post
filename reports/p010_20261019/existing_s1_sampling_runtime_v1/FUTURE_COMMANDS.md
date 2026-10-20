# Future once-only commands after exact A2

Do not execute before a real full fixed report binds this exactSPEC, sources, original parent proofs and numeric limits. No additional code-only gate.

For each original run s1_s17_n400 / s1_s17_n3200, first save exactreview inr/EXISTING_S1_SAMPLES_A2_ACCEPTED.json and a fresh T budget inr/existing_s1_sample_budgets/RUN.json; preserve every prior attempted reservation. Existing original endpoint/base/state remain onVolume.

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/modal run --detach -m experiments.p010.modal_existing_student_samples::main --run RUN --receipt-dir .local/p010_20261019/r1/existing_s1_sample_runs/RUN --review-json .local/p010_20261019/r1/EXISTING_S1_SAMPLES_A2_ACCEPTED.json --budget-json .local/p010_20261019/r1/existing_s1_sample_budgets/RUN.json
```

Save original CLI/app/call; wait submitted before next. Only completed originalresult+actualSTOPPED0 permits onecollect, onerecords, oneraworacle, onescore. Inspect actualargs before use:

```sh
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p010_existing_samples_io.py collect --receipt RECEIPT --out NEW_EXPORT
PYTHONPATH=. .local/midpoint_20261011/venv/bin/python scripts/p010_existing_samples_io.py records --receipt RECEIPT --export EXPORT --spec reports/p010_20261019/existing_s1_sampling_runtime_v1/SPEC.json --out NEW_RECORDS
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/audit_p010_existing_samples.py --spec reports/p010_20261019/existing_s1_sampling_runtime_v1/SPEC.json --run RUN --receipt RECEIPT --export EXPORT --records RECORDS --endpoint .local/p010_20261019/r1/student_inputs_r2/MATH_ENDPOINT.json --gold .local/p009_20261014/r1/stage0_inputs_r1/math500.jsonl --tokenizer .local/midpoint_20261011/data_pipeline/reconstruction_r1/tokenizer --runtime-review .local/p010_20261019/r1/EXISTING_S1_SAMPLES_A2_ACCEPTED.json --out NEW_ORACLE
PYTHONPATH=. .local/p009_20261014/r1/math_verify_env/bin/python scripts/score_p010_existing_samples.py --generation-oracle ORACLE --receipt RECEIPT --spec reports/p010_20261019/existing_s1_sampling_runtime_v1/SPEC.json --run RUN --runtime-review .local/p010_20261019/r1/EXISTING_S1_SAMPLES_A2_ACCEPTED.json --out NEW_SCORE
```

Gold path is an explicit future locator to verify against GOLD_SHA256 beforeuse, never substitute a different dataset. Complete scored evidence and originalgreedy provenance then go to actualA3. Failures preserve validparts and require bounded reconciliation; no wholehelper or model replay.
