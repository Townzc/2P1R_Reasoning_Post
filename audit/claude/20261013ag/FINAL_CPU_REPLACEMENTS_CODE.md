# Claude audit 20261013ag pt3 — p008-final-cpu-replacements-code-r1 @ 63fee8e6: **PASS-WITH-NOTES (code only)**

This verdict covers the code only. The future actual-byte I/O numerical review (`p008_cpu_replacement_integrity_numeric`) is still separate and still required.

## My miss, stated first (second instance of the same class)
The final CPU code I accepted in 20261013ac pt2 (eb398fb1) contains `audit_bundle.verify_packed_run` line 93:

```python
state['lrs'] != lrs(cfg['updates'])
```

This **recomputes the cosine LRs on the CPU host and requires exact equality**. It is the same host-libm trap that failed the two D1 B1/p0 students, and I did not flag it a second time. On the Linux CPU image it would most likely have failed every T1/T8 state check.

The new bundle replaces it with `audit_frozen_bundle` + `audit_frozen_plan.check_state_trajectory`, which compare `state.lrs` against the exact frozen plan bytes. **The old `modal_audit_lineage` entry and `audit_bundle.verify_packed_run` must not be used for P008 final CPU.** In this bundle, `audit_bundle.py` is imported only for `CONTAINERS`. To catch this class in future reviews, I now grep every reviewed bundle for `lrs(` and for any other host recomputation that is compared with exact equality.

## Bundle
The bundle has 17 files. 12 are byte-identical to the 13-file lineage bundle I reviewed at eb398fb1. The changes:
- Removed: `modal_audit_lineage.py`.
- Added: `audit_failed_student.py`, `audit_frozen_bundle.py`, `audit_frozen_plan.py`, `audit_replacement_binding.py`, `modal_audit_replacements.py`.

The entry diff from the reviewed entry contains only:
- the source list, spec path and app name;
- the imports switched to the replacement binding, frozen bundle and failed-student verifier;
- a `FAILED_STUDENTS` branch;
- `physical_sources=24`;
- an `attempt/audit/` key check.

The CPU limits are unchanged: 4 CPU, 16 GiB, 2 readers, a hard limit of 3,300 s from `started`, platform 3,500, startup 600, `retries=0`, `max_containers=1`, a 4,000 s dispatch window, and the original 500¢ slot.

## Q1. Roster and identities: YES
- **`physical_roster()`** = 18 students from `run_roster(8, False, 2)`, including the two failed original names, plus base, pool_d1, pool_d2_parent, the D2 child and the 2 replacements. That is **24 physical sources for 21 logical outcomes**.
- **Per-label checks.** Each label requires:
  - the exact campaign: student completion, replacement, original parent or child;
  - status `failed` for the 3 archived failures and `completed` for everything else;
  - `claim_sha256 = digest(claim)`;
  - a stopped provider with 0 owned containers;
  - the correct plan binding: the original plan for the parent campaign, the successor plan for students, and the replacement plan for replacements.
- **App ids.** The code requires 24 distinct app_ids. I checked the pools: D1 `ap-VJgV…`, D2 parent `ap-5m40…` and child `ap-r5L7…` are distinct, and every student ran in its own app.
- **Failed students.** They must equal the replacement admission's parent records, i.e. claim, terminal and app. `replacement_spec` must have digest 3e1c7924…, the original spec ab49b0a6…, the owner cap 26,604 and a passing reconciliation.
- **Two digest encodings, labelled.** The reconciliation is checked through **file-byte SHA** (`evidence_file_hash`, 5e5667a0…). The preserved manifest is checked against the reconciliation's stored **canonical digest**. The r1 test log records this exact mix-up as the first failure, and the fix leaves the original evidence untouched.

## Q2. Frozen LR/plan bytes and identity: YES
- **Frozen bytes.** `checked_plan` binds the raw `manifest_json` to `input_sha256` (file-byte SHA), the raw `plan_json` to the manifest's byte length and sha, and `plan.run` to the logical science config. It requires 256, 1,024 or 2,048 finite positive LRs and checks that `targets_are_frozen_before_student_scores` is true.
- **Identity.** `recipe.identity.config` must equal the science config, and the schedule and LRs must equal the frozen plan. A replacement must carry `physical_run_id`; an original must not. The archived `replacement_lineage.json` must match exactly, and the oracle must record `logical_run_id` and `outcome_blind_zero_update_replacement`.
- **No host recomputation.** Neither `cos` nor `lrs()` is recomputed anywhere in the new path. I grepped the five new files to confirm.

## Q3. Full-state integrity: YES (code)
For each checkpoint (256, and 1,024/2,048 for T8), the code checks:
- the frozen trajectory: step, cursor, schedule and LRs;
- the prefix dose matches the `update_XXXX` cumulative records;
- adapter keys equal `trainable_names`;
- the optimizer state is present;
- RNG covers {python, numpy, torch, cuda};
- **finite adapter and optimizer tensors**;
- the terminal dose equals the targets;
- every state.pt sha equals the independent local oracle's `state_sha256` and forensic sha.

Endpoint identity is bound to the oracle: 1,319 outputs, the same correct count, and the same updates and targets. Raw outputs are **bound, not re-scored**; their G3 is separate, see pt1 of this report.

The failed students are checked against the archived `failure_manifest.json`. That manifest must equal the terminal evidence and must contain no `intents/`, `completed/`, `endpoint1319/` or `checkpoint_` units. The block journal must show 0 blocks and 0 updates, and the intent must equal the original config, release and plan.

## Q4. Code PASS is not a numeric PASS: YES
`validate()` requires a separate `numeric_review` with scope `…_numeric`, bound to `digest(io_gate)`. The `io_gate` must:
- cover the labels digest;
- forecast at most 3,180 s (3,300 minus the 120 s persistence margin);
- use a dispatch window of 4,000;
- count actual transfer, state and compact bytes, which `validate_all_labels` recomputes from every `state.pt`, including T8 `checkpoint_1024`.

**That closes my FC-N1 from 20261013ac.**

## Q5. Failure retention and once-only dispatch: YES
The changes inherited from the reviewed entry keep three properties:
- the existing CPU claim, intent and terminal, and any `audit/` or `attempt/audit/` keys, are rejected before dispatch;
- all source terminals are re-read at the entry;
- the failure path records `failed` with the full reservation.

There are no writes to the original Volume evidence; unpacking goes to a temp destination.

## Tests
- At 63fee8e6, locally, `test_p008_cpu_replacements` passes **17/23**. The other 6 `FullState` tests error with `ModuleNotFoundError: torch`. I could not install torch here: the PyPI and pytorch.org wheels are unavailable from this sandbox, and the Python is 3.13.
- `test_p008_audit_frozen_plan` and `test_p008_audit_lineage` pass, apart from the same torch-dependent tests.
- Codex's r3 log shows 23/23 OK.
- **I have not executed the 6 full-state fixtures myself.** My Q3 verdict on them rests on reading the code.

## Notes
- **N1 (MEDIUM, process).** At 63fee8e6, two superseded entries still import the host-recomputing `audit_bundle.verify_packed_run`:
  - `modal_audit.py:37`;
  - `modal_audit_lineage.py:66`.

  Neither may be dispatched for P008. Please add a guard. One option is a `raise` at the top of both entries' `main`. Another is a test that fails if any P008 CPU entry other than `modal_audit_replacements` is admitted. Do not edit or delete the old evidence.
- **N2 (LOW).** The 6 full-state fixtures need a torch-capable reviewer environment for independent execution. Either note this in the numeric review, or have the real CPU run's state checks act as the execution evidence.
