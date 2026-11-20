# CR: ext-3B pre-entry schema repair v3 and unchanged actual carry (63523da9, request 61fffe29) — **PASS**

Reviewer: Claude, 2026-10-22 ~08:30 UTC.
- **Failure.** Both original entries failed on the same `State`/`Tasks` KeyError inside the local `submit`, about 325 s after starting. They failed before the upload lookup, before INTENT and store dispatch, and before `worker.spawn`, and made 0 model calls. The CLI exit and log are bound by sha.
- **Fix.** `provider_slots.shared_slots` is the same fail-closed normalizer I accepted in 133090f1. It also rejects a missing or duplicate app identity and an unknown task count. The old inline expression is replaced and nothing else in the slot rule changes. The next attempt goes into a new CLI subdirectory under a new one-time fence bound to the failed parent.
- **Cost of the failed entries.** Each failed entry is still charged: max(reported, (entry s + 60) × the higher of the two rates). That is about $0.52 per cell, recorded as the job's prior compute upper bound for attempt 1. The worker window shrinks by about 385 s to about 7.86 h. My 6.4–7.9 h projection still fits, with an even thinner margin in the worst case.
- **Carried inputs.** `actual_origin` pins the A2-accepted inputs. I re-hashed both from the published NEW_PREFIX_METADATA: ACTUAL_JOB_MANIFEST is bf556ba4… and inputs MANIFEST is afd5fe1b…, both matching. The completed upload is reused and new uploads are forbidden.
- **Unchanged.** Training, evaluation, scoring, caps, checkpoints, the single-resume rule, the MATH-only scope and the A2 numbers are all unchanged.

All 16 source flags and all 4 carry flags are **true**. Launch both cells. The owner has asked that nothing be stopped early. Only the pre-agreed $45/cell money timer may end a cell, and completed MATH endpoints must then be preserved and scored as specified.
