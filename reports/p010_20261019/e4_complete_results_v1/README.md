# E4 complete local results — independent A3 pending

| OLMo-2-1B condition | Correct /1,319 | Accuracy | Logical caps |
|---|---:|---:|---:|
| Existing base zero-shot, reused |166|12.59%|546|
| Existing base four-shot, reused |487|36.92%|43|
| n400 student |509|38.59%|89|
| n3200 student |654|49.58%|76|

Both students completed the original seed17,1,024 updates and2,097,148 supervised targets. Their original training calls failed before endpoint generation because the endpoint wrapper was sliced as a list. After direct owner approval and exact Claude A2, one independent endpoint-only child per saved final model generated the original1,319 questions once. No retraining or repeated endpoint outputs. Both children and original parents are STOPPED with zero owned containers; all full-state and token/source proofs are complete locally. The original parents remain failed and their evidence/costs are retained.

The descriptive n3200−n400 difference is145/1319 (+10.99 percentage points). Each technical-unknown count is0. Original native-EOS/length-cap and marked_answer_v1 semantics are unchanged; caps remain wrong. This single-seed comparison has no new CI/bootstrap or independent actual A3 yet. It does not establish a stable cross-seed effect, a mechanism or a model-family ceiling. The existing four-shot baseline is reused rather than generated again; the old P009 G0 failure remains a diagnostic and is not rewritten.

Original sources: [n400 complete child](../e4_endpoint_results_v1/e4_s17_n400/README.md), [n3200 complete child](../e4_endpoint_results_v1/e4_s17_n3200/README.md), [failed parents and completed training](../e4_failed_endpoint_complete_training_v1/README.md), [direct owner exception](../owner_selection_and_e4_endpoint_20261020_v1/README.md), [exact A2](../review_c542484d_T72_E4_accepted_v1/DISPOSITION.md), [reused OLMo baselines](https://github.com/Townzc/2P1R_Reasoning_Post/tree/192f9156c9235d1bcc3433ac5eade608ef5bbec9/reports/p009_20261014/stage0_generation_results_v1/olmo_p3).

Public state hashes bind previously completed local proofs; they do not assert that the external reviewer read private binaries. Provider projections omit actor identity and retain full private file hashes. Each child reserved2.52USD; each original failed parent retains6.55USD. Reservations are not actual fees or refunds. The latest workspace meter remains the explicit04:43pre-child snapshot in COST_LEDGER, not a final P010 cost. These are operational audit records, not course-report prose.
