# Future only, after direct owner failure exception and exact Claude CR

Both new admission files and continuation output/fence are presently ABSENT.
Owner file scope p011-OT3-confirmed-encoding-NFC-continuation-owner, authority
 direct_human_reply_in_current_chat, decision APPROVE_ONE_INDEPENDENT_CONTINUATION,
requires_exact_CR=true, actual verbatim_reply/recorded_utc, and binding exactly
OWNER_EXPECTED_BINDING.json. No template is an approval.

New CR scope p011-OT3-confirmed-encoding-NFC-continuation-CR, decision PASS or
PASS-WITH-NOTES, exact target_commit/report_sha256/local_report_path, every
SOURCE_BINDING field and actual owner_continuation_sha256. All flags true:
confirmed_965_encodings_reused_byte_for_byte; same_10080_identities_and_cells;
pinned_NFC_only_roundtrip; original_raw_text_retained;
both_failed_parents_retained; new_global_attempt_fence;
no_refilter_or_new_generation; operational_details_accepted.

```sh
PYTHONPATH=. .local/midpoint_20261011/data_pipeline/venv/bin/python scripts/prepare_p011_ot3_nfc_continuation.py --source-lock reports/p011_20261020/long_data_preflight_v1/SOURCE_LOCK.json --original-code-review .local/p011_20261020/r1/LONG_DATA_CR_ACCEPTED.json --prior-owner-amendment .local/p011_20261020/r1/OWNER_LONG_DATA_AMENDMENT.json --prior-proposal reports/p011_20261020/LONG_DATA_REVIEW_AMENDMENT_PROPOSAL.md --owner-amendment .local/p011_20261020/r1/OWNER_OT3_4032_AMENDMENT.json --proposal reports/p011_20261020/OT3_INSUFFICIENT_PARENT_OPTIONS.md --preservation .local/p011_20261020/r1/OT3_FAILURE_PRESERVATION_R1.json --code-review .local/p011_20261020/r1/LONG_DATA_4032_REUSE_CR_ACCEPTED.json --tokenizer .local/exploratory_20261014/r1/inputs/instruct_model --failure-preservation .local/p011_20261020/r1/OT3_4032_ENCODING_FAILURE_PRESERVATION.json --continuation-proposal reports/p011_20261020/OT3_NFC_CONTINUATION_PROPOSAL.md --owner-continuation .local/p011_20261020/r1/OWNER_OT3_NFC_CONTINUATION.json --continuation-review .local/p011_20261020/r1/OT3_NFC_CONTINUATION_CR_ACCEPTED.json
```

Use a new log and record original CLI exactly once. Keep both old partials and
all previous attempts. No full rerun/clear fence/automatic failure retry. This is
not training or actualA1 admission. No old model/scoring/test/collector repeats.
