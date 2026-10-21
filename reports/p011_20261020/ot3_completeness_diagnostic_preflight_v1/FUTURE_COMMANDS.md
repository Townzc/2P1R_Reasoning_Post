# After the exact short CR only

Save .local/p011_20261020/r1/OT3_COMPLETENESS_DIAGNOSTIC_CR_ACCEPTED.json
with scope p011-OT3-readonly-completeness-diagnostic-CR, PASS or PASS-WITH-NOTES,
actual target_commit/report_sha256/local_report_path and all SOURCE_BINDING fields.
Require all seven flags true: original_complete_function_called;
readonly_immutable_database; all_cardinality16_responses_included;
original_length_unknown_retained; no_tokenizer_selection_generation_or_scoring;
deterministic_samples_and_quantiles_accepted; reporting_threshold_semantics_accepted.

Use one new log/CLI. Never retry partial output or delete the permanent fence.

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/diagnose_p011_ot3_completeness.py --request .local/p011_20261020/r1/review_poll_20261021T020254Z/REQUEST_OT3_COMPLETENESS_DIAGNOSTIC.md --owner-record .local/p011_20261020/r1/OWNER_OT3_DIAGNOSTIC_REPORTED_DECISION.json --preservation .local/p011_20261020/r1/OT3_FAILURE_PRESERVATION_R1.json --review .local/p011_20261020/r1/OT3_COMPLETENESS_DIAGNOSTIC_CR_ACCEPTED.json
```

After a genuine complete diagnosis, copy original output evidence once to
reports/p011_20261020/ot3_completeness_diagnostic_v1 and submit actual result review.
No source input write, new selection or science is authorized by this command.
