# Only after the original child completes and provider exits

Use the original per-run receipt in `e4_endpoint_only_runs/RUN`. Choose new output directories for each step; inspect existing intents and processes first.

1. `scripts/p010_e4_endpoint_io.py collect --receipt RECEIPT --out NEW_EXPORT` (Modal environment;1200 local seconds).
2. `scripts/p010_e4_endpoint_io.py records --receipt RECEIPT --export EXPORT --out NEW_RECORDS` (Modal environment;600 local seconds,two readers,29 named records).
3. `scripts/audit_p010_e4_endpoint.py --spec reports/p010_20261019/e4_endpoint_repair_preflight_v1/SPEC.json --receipt RECEIPT --export EXPORT --records RECORDS --run RUN --training-proof ORIGINAL_COMPLETED_TRAINING_PROOF --endpoint ORIGINAL_OLMO_GSM_ZERO_JSON --gold ORIGINAL_GSM1319_JSONL --tokenizer ORIGINAL_OLMO_TOKENIZER --owner OWNER_E4_ENDPOINT_ONLY_ACCEPTED_JSON --runtime-review REAL_A2_ACCEPTANCE_JSON --out NEW_ORACLE` (original data environment).

These commands are prepared only. Actual full results still require independent A3 before report use. No local or cloud training-state replay is authorized by this addendum.
