# One future construction, only after exact real CR

NOTRUN. Write LONG_DATA_4032_REUSE_CR_ACCEPTED.json only from a complete fixed
real PASS or PASS-WITH-NOTES report for
p011-OT3-4032-confirmed-parent-reuse-construction-CR. Bind every field in
SOURCE_BINDING.json, report_sha256/local_report_path/target_commit and all five
flags below as true:

- confirmed_eligible_parents_reused_without_refiltering
- original_failed_attempt_retained
- new_global_attempt_fence
- first_full_encoding_only
- operational_details_accepted

The direct owner count decision is already approved. Old code acceptance alone
cannot admit this new consumer. Check the fixed output/fence and original saved
receipts before invoking once. Any partial or failure is retained, never retry.

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_ot3_4032_inputs.py --source-lock reports/p011_20261020/long_data_preflight_v1/SOURCE_LOCK.json --original-code-review .local/p011_20261020/r1/LONG_DATA_CR_ACCEPTED.json --prior-owner-amendment .local/p011_20261020/r1/OWNER_LONG_DATA_AMENDMENT.json --prior-proposal reports/p011_20261020/LONG_DATA_REVIEW_AMENDMENT_PROPOSAL.md --owner-amendment .local/p011_20261020/r1/OWNER_OT3_4032_AMENDMENT.json --proposal reports/p011_20261020/OT3_INSUFFICIENT_PARENT_OPTIONS.md --preservation .local/p011_20261020/r1/OT3_FAILURE_PRESERVATION_R1.json --code-review .local/p011_20261020/r1/LONG_DATA_4032_REUSE_CR_ACCEPTED.json --tokenizer .local/exploratory_20261014/r1/inputs/instruct_model
```

Use a new original local CLI/log, record the real session, no paid calls.
Completion still requires actual A1. Do not run old OT3 or AM constructors.
