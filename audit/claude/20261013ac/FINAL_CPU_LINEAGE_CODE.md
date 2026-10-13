# Claude audit 20261013ac (part 2) — p008-final-cpu-lineage-code-r1 @ eb398fb1: **PASS-WITH-NOTES (code only)**

This is a code review only. It does not admit the CPU audit, and it does not cover the I/O numerical gate.

## Q1. Physical vs logical identity — YES
- `physical_roster` is the 18 students, the base, `pool_d1`, `pool_d2_parent` (the original `pool_d2`) and `pool_d2_remaining`: 22 physical sources for 21 logical results.
- `validate` requires each label's campaign, run and status, plus the claim-SHA chain, a stopped provider and zero containers:
  - the D1 pool and the D2 parent belong to the original campaign;
  - the child belongs to the child campaign;
  - students and base belong to the completion campaign.
- Original-campaign claims must carry the original plan SHA, and successor claims the successor plan SHA.
- Pool sources must be members of the reviewed `validate_pool_lineages` records.
- The parent is pinned to `failed` everywhere, and it is never relabelled.

## Q2. Slot and budget — YES
- `require_handoff(..., 'audit')` requires the immutable transfer record and the absence of any original audit claim, intent or terminal.
- The CPU audit uses one 500¢ slot. `CONFIG` is 3,300 s with 2 readers. The dispatch window is the full 4,000 s, and the I/O forecast is at most 3,180 s.
- A separate numeric review must bind the actual bytes (`io_gate` / `numeric_review`).
- The timer starts **before** imports and validation. The soft stop is 120 s before the hard stop.
- An `aborted` event stops the second reader after the first failure. Unit and done keys are written `skip_if_exists`, so there is no replay.

## Q3. Integrity scope — YES
**Failed parent (`verify_failed_parent`).** The function requires:
- the reconciliation to have passed, with 3,992 outputs, 0 unknown, every raw output redecoded and every prefix replayed;
- the archive's `failure_manifest` digest to equal the terminal `evidence_sha256`;
- the preserved contents to be exactly the original failure files plus `failure_manifest.json`, with no replaced file;
- the intent's plan, config and source commit to equal the claim and reconciliation records.

**Completed child (`verify_completed_child`).**
- The function requires: the envelope and manifest digest to equal the terminal, a merged oracle with parent=failed, child=completed and 3,992 parent outputs, and no `.pt` files.
- Both the cumulative result and the child-only result must match the oracle, with `physical_outputs == 3992 + child_outputs` and `child_outputs > 0`. Parent outputs therefore cannot be counted as child returns.

**Students and base.** These reuse the reviewed `verify_packed_run`, which loads the full states at 256 / 1024 / 2048 and checks dose, optimizer and RNG.

**Raw rescoring.** It is correctly scoped as *bound*, not repeated.

23/23 tests pass locally (`PYTHONPATH=.:tests`).

## Notes
- **FC-N1.** The 3,300 s cap has to cover copying, hashing and loading all 22 sources. That includes 8 T8 students with two forensic states each. The I/O numeric review must use the **actual** byte totals and the measured copy rates from the earlier CPU timings fields. It must not use the T1 averages.
- **FC-N2.** `main()` requires `UPLOAD_VERIFIED.json` and runs the exact-provider checks before spawn. Both helpers are already reviewed patterns.
