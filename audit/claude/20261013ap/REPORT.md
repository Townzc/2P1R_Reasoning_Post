# Claude audit 20261013ap — three pending requests

| request_id | target | verdict |
|---|---|---|
| p008-post-freeze-results-interpretation-r1 | 3e878403 | **PASS** |
| p008-midpoint-freeze-integrity-r1 | e0025e0e | **PASS** |
| p008-final-cpu-local-finalizer-code-r1 | 3eaee7c7 | **PASS-WITH-NOTES (code only)** |

## 1. Post-freeze interpretation @ 3e878403 — PASS
- `post_freeze_results_review_v1/FACTS_ADDENDUM.md`: the six copied estimates and intervals (D2 B8/p4 Δ +4.17 [+1.82, +6.52]; D1 −0.45 [−2.88, +1.90]; D2 C_p4 +4.78 [+1.52, +8.11]; draw means 1.86 [0.15, 3.56] and 2.50 [0.15, 4.85]; 27/31 intervals include 0) equal my independent `reg_check.py` recompute from 20261013an.
- `registered_primary_results_v1` is unchanged between b212b6a8 and 3e878403 (empty diff).
- Wording: "D2 only, not replicated", draw means "not independent evidence", no familywise claim, pointwise conditional intervals only. This satisfies my R1 note from 20261013an. No overclaim found.

## 2. Midpoint freeze integrity @ e0025e0e — PASS
- The 9 copied files (FACTS_AND_LIMITS.md, RESULTS.json, ALL_CELLS.csv, ALL_CONTRASTS.csv, ACCOUNTING.json, BILLING_SNAPSHOT.json, 3 PNGs) have **git blob ids identical** to `registered_primary_results_v1` at b212b6a8, and each `original_file_sha256` in FREEZE.json equals the sha256 of the original bytes. Nothing was regenerated.
- MANIFEST.json: all 11 sha256/byte entries match, including FREEZE.json (d3a3a498…) and READINESS.md (5fcdc135…).
- All 7 `other_fixed_sources` hashes match their bytes at both e0025e0e and 72e15f74; READINESS links pin 72e15f74.
- Cutoff honesty: recorded 04:01:18 UTC vs cutoff 04:00:00 UTC, `cutoff_extension: false`. The pending status is true: my 20261013an (final T8 G3 + complete registered results) landed on `claude/audit` at 04:01:54 UTC, 36 s after the freeze was written, and the last observed review (3c15e24c, 03:59:17 UTC) is correct. T8 G3 "7/8" at cutoff is accurate.
- f26f814b changes only `reports/p007_audit/INDEX.json`; the freeze directory tree (9e455186…) is identical at e0025e0e, f26f814b and current HEAD.
- READINESS.md scope text (no stable winner, pointwise intervals, B and T confounded on the main path, N2 FAIL + post-hoc 9600 s disclosed, $266.44 is reservation not invoice) is accurate.
- Later results (my an/ao PASSes, CPU admission) must go in a dated addendum, as `future_updates_rule` says. Do not edit this directory.

## 3. Final CPU local finalizer code @ 3eaee7c7 — PASS-WITH-NOTES (code only)
This does not review any actual CPU result. Final external result review stays separate.

What I checked:
- **No host recomputation.** No `lrs(`, `cos` or schedule recomputation in the script. LR/plan identity is inherited through `validate_all_labels`, which uses the frozen-plan path I accepted in ag pt3/ai.
- **Imports are covered by bound bytes.** All 12 transitively imported project modules (common, guard, checkpoint, audit_cap_binding, audit_replacement_binding, audit_t8_cap_records, audit_frozen_bundle, audit_bundle, evidence_bundle, contract, completion_queue, provider_release) are in the 19-file runtime roster, and the script requires `sha(ROOT/path)` equality for all 19. I checked those 19 hashes at 3eaee7c7: all match. The code acceptance itself binds only the script sha (b14c1dd9…), which is correct given the roster check.
- **Roster.** `validate()` + `len==24 and == physical_roster()`; 19 runtime sources incl. `modal_audit_t8_cap.py`; admission/input manifest/labels re-verified.
- **Ledger.** Plan, handoff, cap records, every physical claim/terminal, CPU intent = digest(binding)/digest(sources)/digest(inputs), claim→intent/plan, exactly one attempt key, 500¢, terminal = receipt, `completed`, claim_sha.
- **Timing.** claim duration 3300, hard stop = min(started+3300, deadline−30), ordering started ≤ claimed ≤ finished ≤ min(hard stop, claim deadline), result wall ≤ finished−started. On float exactness: `deadline − claimed == 3300.0` is exact for epochs in [2^30, 2^31), since the ulp there is 2^−22 and 3300 is an integer (200k random trials: 0 mismatches). This is not the libm class.
- **Proof per label.** Failed archives keep `failed`, zero dose for the 2 students, file roster and digest; D2 child keeps the bound oracle, no rescoring; students: T1 256-state, T8 1024+2048 states equal oracle `state_sha256`/forensic sha, copied bytes and per-file timings complete and finite, raw rescoring scope must say "not repeated", T8 amendment fields (9600/9560/1253/5/1258, N2 false, post-hoc true, CAP_SPEC, operational evidence digest).
- **Journal.** On-disk intents/proofs/completed and remote unit/done each equal the roster; proof bytes sha bound in `done`; aggregate result equals saved proofs.
- **Provider.** Run log must contain exactly one `ap-` id equal to `--app-id`; app stopped, 0 owned containers, no container in the global snapshot.
- **Output** is create-only; no model calls, no retries.
- **Tests:** `tests.test_p008_final_cpu_local` at 3eaee7c7: **15/15 OK** locally (no torch needed).

Notes:
- **N1 (LOW, tests).** The 15 tests exercise `check_proof`, `check_journal` and `check_provider`. The top-level `audit()` (acceptance binding, ledger, clocks, artifact set, aggregate scope) has no fixture, so its first execution will be on the real export. A crash there is fail-closed (no output written), but a fix would change the script sha and need a new scoped review. Optional: one end-to-end synthetic fixture through `audit()`.
- **N2 (LOW, output).** `state_binaries_bound=26`, `completed_physical_sources=21`, `original_failed_sources=3` are literals. They are correct (10 T1 states + 8×2 T8 states = 26; 21 completed; 3 failed), but deriving them from the checked proofs (e.g. `sum(len(p['checkpoint_sha256']))`) would make the output self-proving.
- **N3 (INFO, scope).** As the request says: this verifier binds the CPU's own load results to prior oracle hashes; it does not reload 26 binaries locally or rescore raw answers. Any slide/paper text must keep that wording.
