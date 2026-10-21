# C2 finite batched-window engineering, prepared only

2026-10-21T05:55:57.819725+00:00. Two new modules implement the reviewer's batch-driver suggestion from
`review_d3f66ec3_B_rule_and_prereview_v1/PREREVIEW_C1_B_C2_LEAF.md` without
changing the original E1d ordering, common-support first400 selection or S1
intersection. The review was a suggestion, not CR or a paid admission.

A candidate bounded window contains at most700 unresolved T72-usable parents,
only missing T1.5 attempts1..4 at originalT.8/seed. Known usable/exhausted T15
parents need no generation. Missing original T72 or unknown Boolean verdicts
block; no new T72 requests. Every generated extra beyond the final400 is retained
and counted. Complete saved new verdicts feed the unchanged c2_prefix; original
basis mutation, missing results or overwriting old rows fail closed.

The prepared generation body preserves raw output before verification, uses
permanent window/batch/ack markers, measures all3commits plus remoteack, and
retains partials on errors without retry. No scoring inside the GPU body; whole
local scoring and potential later windows still need exact source/receipt/cost
integration.12new synthetic checks passed once0.040s, including tailbatch, reuse,
oldunknown, first400/S1overlap, overgeneration retention, changedbasis, budget
beforegeneration and failedcall replay rejection. No old tests or realdata repeated.

Not a complete C2 entry or admission. Remaining: original E1d/raw/savedscore
lossless consumer and provenance, native loader, frozen-new-score driver, full
source closure/Modal/ledger/deadlines/transport, actualtiming/spec/Cbudget,
original C2a/C2b student/state/eval path and Δ_T^CS analysis. Review the whole
shared C2 path once ready; no separate leaf-only gate created. Candidate700 is
not an approved requestcount/window/cost. C1failed3.74 reservation remains; its
selfcalibration exception cannot be reused forC2. No actualinputconsumer, model,
score, tokenization, upload or reserve. Old P010/P011 science remains immutable.
