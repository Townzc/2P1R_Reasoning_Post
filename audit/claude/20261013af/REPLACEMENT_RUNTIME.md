# Claude audit 20261013af — p008-two-zero-update-replacement-runtime-r1 @ ed037c1c: **PASS** (2 LOW notes, 1 question)

The two replacements may be dispatched once the entry's own preconditions hold. The entry enforces each of these itself:
- two original T1 calls have completed and been released;
- each of those T1 walls is under 5,400 s;
- shared capacity is below 8;
- there is no prior replacement claim, unit or directory.

## Two corrections to my 20261013ae notes, stated first
- **R2 was wrong.** The owner's rule is $450 of $500, which already protects $50. My "≤ $400" subtracted the protection twice. Codex is right.
- **The basis of R4 was wrong.** P007B's eight token students each evaluated **1,319** questions (`P007B_ENDPOINT_COUNTS.json`). The 431-question endpoint belongs to the older P007 bank experiment. The 5,400 s check that Codex added is still fine as an engineering guard.

## Q1. Authority and provenance: YES
- **Owner record.** `OWNER.json` holds the direct owner reply "批准两项补跑及 $266.04 阶段上限" (20:57:59 UTC). `validate_owner` requires every field exactly, including type: 2 calls, 1 call each, no retry, 6,001 s, max 8 workers, the freeze time, and 24,968 + 1,636 = 26,604.
- **Exactly two slots.** `PLAN.json` equals `make_plan(original_execution_plan, owner, created_epoch)`. Its digest equals `spec.plan_sha256` (538911d4…). The campaign is new and the two slots are 818¢ each. I ran the validators on the real ADMISSION data, not only on test fixtures.
- **Failed parents.** `validate_parent` passes for both. The claim, intent and terminal records match the preserved ledger (attempts 12848af1… and e2ead828…). Both terminals are failed. Both provider apps are stopped with 0 containers.
- **Zero-update proof.** The embedded `zero_update_reconciliation` equals `RECONCILED.json` byte for byte (sha 5e5667a0…). All five zero fields are 0 for both failed attempts.
- **No replay path.** At dispatch, all of the following raise:
  - an existing local destination;
  - an existing replacement claim, intent or terminal;
  - an existing unit or attempt key;
  - an existing volume directory.
  
  The worker's `require_parent_records` re-reads the parent records as read-only. No parent record is written.

## Q2. Science preserved: YES
- **Configs.** Each physical config equals `physical_config(original)`. The only differences are the `run_id` suffix and the added `logical_run_id`. The logical canonical digests are b8217806… and f04e7f28…, matching the ledger intents; `CANONICAL_CONFIG_DIGESTS.json` now labels both encodings, so **R1 is closed**.
- **What the runtime uses.** `identity.config` is the original logical config. The runtime uses `config['run_id']` to look up the plan hash in the input gate (`block_student_runtime.py:30`), so the logical identity is required, and that is what is passed. The physical id is used only for claims, journal keys and evidence paths.
- **Inputs.** The original upload is reused read-only. The worker checks the manifest sha dae1bd27… and every file.
- **Sources.** The bundle has 34 files. 31 of them are byte-identical to the 32-source frozen-LR bundle reviewed in 20261013ad (c5053814). The only changes are:
  - removed: `modal_students_completion_lr.py`;
  - added: `modal_student_replacements.py`, `student_replacement_binding.py`, `provider_release.py`. The last is unchanged since 32777f41, which I reviewed in 20261013y.
  
  So the frozen-LR validation, optimizer, loop and evaluation are the reviewed bytes. Every SOURCE_BUNDLE hash equals the blob at ed037c1c.
- **Oracle.** `audit_p008_student_replacement.py` mirrors the reviewed student oracle and adds the lineage checks:
  - the lineage file, physical/logical mapping and `replacement_of_failed_parent`;
  - `recipe.identity` checks for both physical and logical identity;
  - plan validation uses `frozen_student_plan.validate_plan`, so the oracle host never recomputes LRs.

## Q3. Concurrency, provider, timer, disconnects: YES
- **Locking.** The same `dispatch_lock(shared)` covers both queues. Pending calls without a terminal in either queue count toward capacity, and `occupied_capacity` also counts every unmatched provider container.
- **Ordering.** Every original T1 must already have `submitted.json`, and no T8 `dispatch_intent` may exist.
- **Worker timer.** The timer starts at worker entry: stop = min(start + 6,001, deadline − 30). Platform limits are 6,061 s and startup 600 s. `retries=0`, single-use containers, and the failure path records `failed` against the full reservation.
- **Reservation.** The minimum reserve is ceil((6,001 + 700) × 4.393584 / 3600 × 100) = **818** (exact, no slack), so the reservation is complete.
- **Local disconnects.** If the CLI dies after `dispatch_intent`, the existing destination blocks any replay, and `submitted.json` or the provider list resolves the state. This covers the 21:22 UTC laptop-sleep case.

## Q4. Project budget: YES, with one question
- **Report lines.** The 50 raw report rows sum to **$139.99537961**, and the P008 lines to **$53.07196064**, which matches. The workspace summary is $141.09183740; the $1.10 gap is storage and timing, and it is assigned conservatively to the non-P008 residual.
- **Projections.**
  - Double-counted: 14,110 + 26,604 = 40,714¢, ≤ 45,000.
  - Overlap-adjusted: $88.02 + $266.04 = **$354.06**.
- **Labels.** Usage, reservations and invoices are kept distinct. No reservation is reclaimed, and credits are not treated as income.
- **Question.** Every report row starts on Oct 12 or Oct 13. Please state that **no project spend exists before Oct 12** in this workspace, any other workspace or any other provider; if it does, add it to the residual. Headroom is $42.87 on the double-counted projection and $95.94 on the overlap-adjusted one.

## Q5. Timing and final-audit lineage: YES
- **Timing.** The original roster (10 T1 + base) and both failed attempts are kept, and exactly two replacements fill the missing logical timings. This rule does not close N2 or waive T8.
- **Final CPU audit.** It must cover 21 logical outcomes from 24 physical sources:
  - both failed T1 attempts and their two replacements;
  - the failed D2 parent.
  
  The old 22-source code must not be reused. I agree.

## Notes
- **L1 (LOW, ops). Collection after the sleep disconnect.**
  - I read the local worktree at 21:56 UTC; nothing there is published yet. All 8 original T1 directories have `return_error.json` (DNSConnectionError).
  - 5 of the 8 now also have a collected `result.json`. Each has the keys {artifact_manifest, receipt, result} and receipt status `completed`.
  - Their walls are **2,757 / 2,793 / 3,111 / 3,526 / 3,664 s**, all well under the 5,400 s flag and the 6,001 s cap. I looked at walls and status only, not scores.
  - The replacement preflight reads only `runs/<name>/result.json`, and checks it against the ledger terminal and manifest digest. So a faithfully collected envelope passes, and a missing one fails closed.
  - The collected envelopes carry **no provenance marker**. Please add one, for example `collected_after_local_disconnect: true` with the volume paths, or a sibling `COLLECTION.json`. Otherwise the final CPU audit cannot tell them from a live `call.get()` return, even though `return_error.json` sits in the same directory.
- **L2 (LOW, future T8 entry).** The original-queue entry does not read the replacement queue's pending, uncontainered calls. Ordering prevents overlap today: N2 needs the replacements' timings before any T8. If a future T8 dispatch path is written, it should use the same two-queue `occupied` union.
- **Ops reminder.** Launch the replacement CLIs detached, as the originals were, and keep the laptop awake (`caffeinate`). Both prevent a repeat of the 21:22 UTC disconnect.

## Tests
`PYTHONPATH=.:tests python3 -m unittest tests.test_p008_student_replacements` at ed037c1c: **20/20 OK**, run locally.
