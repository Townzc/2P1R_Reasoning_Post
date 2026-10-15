# S1 complete exact runtime and numerical review

Request `p009-stage1-S1-full-runtime-and-numeric-r1`; scope `p009-stage1-S1-exact-runtime-input-and-numeric`.
Fixed target follows in INDEX after this candidate commit. Created 2026-10-15T08:19:46.825317+00:00.

Review [the complete81-source candidate](stage1_s1_runtime_preflight_v1/README.md).
`SOURCE_BINDING.json` supplies exact source/spec/timing/actualbudgetproxy/input
and NC packet hashes, six655c slots, prior2620c, zero paid exceptions, and each
required true acceptance flag. Exact spec SHA256 `e3267d0981e854862026c665f4f840cef9024e2c3a9e7cb158d1d2ff16b95a7f`.
The total independent local scoring budget is6000 seconds plus explicitly
separate5-second cleanup; serial500*8+300 with20% is5160, not a time guarantee.

Return scope, target_commit, real report_commit/report_sha256, decision
PASS/PASS-WITH-NOTES or HOLD, exact source_files/spec_sha256/timing_sha256,
budget_proxy_comment_sha256, NC_packet_manifest_sha256, input_basis_file_sha256,
input_archive_file_sha256, all six required true flags in SOURCE_BINDING,
prior_stage1_reserved_cents2620/new_reserved_cents3930 and
first_paid_measurement_exceptions0. Full code/runtime review does not fabricate
the still separate actual NC A4 or first-pair futility A4; the implementation
requires their original full reports and immutable bindings before each call.
Budget approval is real [comment6187149432](https://github.com/Townzc/2P1R_Reasoning_Post/issues/13#issuecomment-6187149432),
with [bounded acceptance and wording correction](stage1_s1_budget_proxy_accepted_v1/README.md).
No new arm, decision rule, scientific dose or repeated output is proposed.
