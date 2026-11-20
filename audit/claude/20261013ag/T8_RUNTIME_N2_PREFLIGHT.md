# Claude audit 20261013ag pt2 — p008-t8-runtime-n2-preflight-r1 @ 860aa4cb: **PASS (code only)**, 1 note for the numerical N2

This review covers T8 source admission only. The numerical N2 still needs its own review: all 10 T1 plus base, the two replacements, and an immutable all-host proposal. No T8 may run before that review passes.

## Source bundle
The bundle has 34 files. 31 of them are byte-identical to the 32-source frozen-LR bundle that I reviewed at c5053814.
- Removed: `modal_students_completion_lr.py`.
- Added: `modal_students_t8.py`, `student_t8_binding.py`, and `provider_release.py`. The last one equals 32777f41, which I reviewed in 20261013y.

Every SOURCE_BUNDLE hash equals its blob at 860aa4cb. The entry diff against the reviewed frozen-LR entry contains only these changes:
- the app name;
- the import of the T8 binding;
- the exclusion `training_multiple != 8`;
- the timer moved to the start of `work()`;
- the platform `timeout` changed from 10,900 to 9,620;
- `require_timing_terminals` called in both the entry and the worker;
- the both-queue occupancy check, the unit/attempt/volume-dir rejection, and a check that all 13 dependency provider apps are stopped.

The science path is unchanged. It still uses `frozen_lr_block_student_runtime.run`, the same identity with no physical id, block-16, `checkpoint_1024` forensics, and one 1,319-question HF greedy endpoint.

## Q1. Capacity and replay: YES
- `pending_across_queues` reads both canonical queues under the shared original lock. It checks that each dispatch identity matches its queue plan, and raises on any unknown terminal status.
- Every call without a terminal occupies a slot. `occupied_capacity` also counts unmatched provider containers. **This closes my L2 from 20261013af.**
- The entry rejects any existing local destination, claim, intent, terminal, unit or attempt key, and any existing volume directory.
- Each invocation dispatches one slot, with `retries=0` and single-use containers.

## Q2. N2 enforcement: YES
- `accepted(gates['t8_numeric_review'], 't8-numeric', source_files, digest(spec))` requires a separate numerical acceptance. It must have `N2_closed` true, cover **exactly all 8** T8 runs (`accepted_runs == large`, so no favourable subset), use worker caps of 9,560 for all 8, and use the matching `proposal_digest` and `common_plan_gate`.
- The proposal itself must stay `N2_closed: false` and `runtime_admission: false`, with `failed_host_dropped: false` and policy schema `p008_t1_first_timing_gate_v2`.
- Its logical→physical mapping must be the 11 members, with replacements under their physical names.
- Provenance must contain a completed physical terminal plus oracle, intent and provider hashes for every member.
- Every prediction must be ≤ 9,530 s.
- The gate needs **all 13 physical terminals**: 11 completed and the 2 original failed attempts. Each of these must equal the proposal provenance, and the failed attempts must keep zero dose.
- Both the worker and the entry re-read these terminals from the claims store. A code PASS alone cannot open T8.

## Q3. Caps and reservation: YES
- The worker sets stop = min(entry + 9,560, deadline − 30). There is a soft `deadline()` at stop − 30, which records failure, and a hard timer at stop. The platform limit is 9,620 and startup is 600.
- Moving the timer before imports **strengthens** the bound. With the old placement, the clock started only after imports, validation and admit.
- The reservation is ceil((9,560 + 700) × 4.393584 / 3600 × 100) = **1,253¢**, which equals each original T8 slot.
- All 8 configs are main, 2,048 updates, 4,194,296 targets and 9,560 s.

## Q4. Oracle and tests: YES
- `audit_p008_student_t8.py` mirrors the reviewed student oracle and adds `require_timing_terminals`. It uses `frozen_student_plan.validate_plan`, which compares LRs by digest and never recomputes them on the host.
- Locally at 860aa4cb, `tests.test_p008_t8_admission` + `tests.test_p008_student_replacements` gave **31/31 OK**.
- The NaN-fixture error in the first test log is retained and explained. The production logic was not relaxed.

## Note N1 (for the numerical N2 review, not a code defect)
For the T1s, `result.wall_seconds` is measured from after admit until just before `result.json` is written. It excludes:
- the container-start→claim segment, **2–7 s** in the 8 published T1s;
- pack, manifest and `guard.finish`. Claim→`finished_epoch` exceeds `wall_seconds` by **6–42 s**.

The T8 cap now covers entry to exit. The N2 proposal should therefore estimate F from **claim→finished_epoch**, or add these segments explicitly, rather than from `wall_seconds`. The effect is small: at most about 50 s against the 1.2× margin. It still needs to be explicit so that the rule is exact.
