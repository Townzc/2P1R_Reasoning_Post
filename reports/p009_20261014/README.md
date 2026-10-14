# P009 — owner-authorized internal-only scope, actual reviews pending

The owner has explicitly designated both complete P0 endpoints internal-only.
All P009 comparisons will use the reviewed common vLLM configuration. This is
a post-result scope amendment, with both original gate decisions preserved.

|Endpoint|vLLM /1319|Historical HF /1319|Discordance|Original decision|
|---|---:|---:|---:|---|
|Base|650|638|126/1319 (9.55%)|blocked_unspecified_discordance_case|
|Correct reference|950|969|77/1319 (5.84%)|pass_internal_only|

[Owner scope amendment](p0_internal_only_amendment_v1/README.md),
[complete original evidence](p0_entry_repair_complete_v1/README.md), and
[actual runtime gate projection](p0_entry_repair_actual_gate_v1/README.md).
Actual A2 raw/lineage/accounting has PASS at45b4163a, with the original scientific
block retained. The exact owner-amendment review is pending. HF scores are historical
diagnostics, excluded from P009 treatment effects and G0/G1 inputs. Existing
vLLM endpoints are reused only for their identical definitions after A2; no
original generation or scoring is repeated. This amendment adds$0.

All2638 outputs are locally verified;2,382 were new and256 inherited unchanged.
All four providers stopped. All failures and costs remain. G0/G1, negative
control, futility, data/dose and exact runtime/budget gates are unchanged.
Current allocation:$110 total, Stage0$20/Stage1$50/Stage2$35/unallocated$5;
project$450/protected$50. Stage2 remains five groups × seeds17/29, teachercontext
2048 with seven unsupported MATH rows. No Stage1 outcome is available yet.
Automatic progression is authorized after real gates; no routine permission is
needed. p009 stays active, p007/automation-4 paused.
