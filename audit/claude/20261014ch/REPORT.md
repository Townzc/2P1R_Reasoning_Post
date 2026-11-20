# Audit 20261014ch: `p009-stage1-S1-full-runtime-and-numeric-r1`

- **Scope:** `p009-stage1-S1-exact-runtime-input-and-numeric`
- **Target:** `6f0bd17e9f788437328c903558df623cf65a94e4`. Manifest `bdaf5a68ba0165cf3360b4e0a325423625c14a8b19ea4ed391fe434e1e8851c7`.
- **source_files:** the exact 81-entry map in `SOURCE_BINDING.json`. All 81 hashes were recomputed at the target.
  - 53 entries are byte-identical to the cf-accepted NC 53.
  - 28 are added. Some were already accepted in earlier scoped reviews (`gates.py`, `stage1_analysis.py`, the math scorer, P1 driver and journal files, `prepare_p009_s1_inputs.py`). The new S1 adapters are `modal_stage1_s1.py`, `stage1_s1_funded_{binding,contract,evidence,runtime,training_process}.py`, `stage1_s1_*`, `audit_p009_stage1_s1.py`, `p009_stage1_s1_io.py` and `score_p009_stage1_s1.py`.
- **Bindings:**
  - spec_sha256 `e3267d0981e854862026c665f4f840cef9024e2c3a9e7cb158d1d2ff16b95a7f` (recomputed)
  - timing_sha256 `a69cef17b69bb06a1e9c60b7101f2665d48a6d3beb8ee74ac711dd31cbfb5722` (recomputed)
  - budget_proxy_comment_sha256 `336be02ed18fa1b98c9387a3cc2641e973f475cb58ff684e1ddc8529c7acdcc3`. This is the UTF-8 canonical digest (`ensure_ascii=False`) of the 10-field projection of comment 6187149432. I reproduced it, and the body equals my posted text byte for byte.
  - NC_packet_manifest_sha256 `fc560e602f13bee81f92c86ba6a573fb2eba107ec22b9a649e588e1f35403d3d`
  - input_basis_file_sha256 `47c5c5e8…`, input_archive_file_sha256 `ba1fbefb…`

## Decision: PASS-WITH-NOTES
- all_21_training_hosts_included = true
- all_MATH_base_endpoint_batches_included = true
- uncalibrated_timing_proxy_scope_accepted = true
- training_process_exit_before_vllm = true
- local_scoring_worst_pair_scenario_accepted = true
- registered_NC_and_futility_gates_retained = true
- prior_stage1_reserved_cents = 2620
- new_reserved_cents = 3930
- first_paid_measurement_exceptions = 0

## Checks
- **Real RunGuard.** I ran the unchanged `guard.py` on the real `PLAN.json`. All six `intent()` dicts have exactly the 4 base fields and are **admitted**, and a duplicate admit is rejected. This is the cd-erratum check, run first.
- **Inputs.** All 25 `spec.inputs` entries hash-match the cb-accepted S1 archive files: encodings, rows, plans and configs for all 6 cells, plus `S1_ENDPOINT`. Every config has S1, the right seed and n, 1024 updates and 2,097,148 targets.
- **Science code unchanged.**
  - `stage1_s1_funded_runtime.py` reuses NC's `spawn_process` and `training_once`, so training exits successfully before vLLM starts. It calls `checked_endpoint('S1')` and runs 2 endpoint batches over 500 problems.
  - The training process differs from NC only in the recipe and limits plumbing, and in `endpoint_batches_left = 2`.
  - The training core, endpoint engine and math scorer are unchanged bytes.
- **Gates.** `validate()` requires the actual NC A4 (scope `…complete-pair-A4`, packet `fc560e60…`). The 4 later cells additionally require an actual first-pair futility A4 with `futility_stopped=False`, both first-pair terminals, and 2 distinct app IDs. The NC ≥ 5 pp rule, the first-pair < 2 pp futility rule and G1 are unchanged.
- **Budget.** 6 × 655 + 2620 = 6550 ≤ 7000 (Stage 1 cap $70). The per-slot `stage_remaining_before` runs from 4380 down to 1105.
- **Timing.** Each slot's forecast is **4,095 s / 606¢**, admitted, within the 4470 soft limit, 655¢, and 5·606 ≤ 4·1105 for the last slot.
- **Timing transfer (my own numbers from the plans).**

| Measure | S1 | NC |
|---|---|---|
| Total processed tokens | 2.37–2.41 M | 2.55 M |
| Padded token mass | ≈3.50–3.56 M | ≈3.58 M |
| Largest padded update | 9,426 tokens | 6,447 tokens |
| Longest sequence | 1,571 tokens | 921 tokens |

  Per-block compute should be close to NC's. The 43.3 s maximum block, taken from all 21 hosts, still gives margin. The endpoint maximum of 20.4 s already includes the base model's 1024-token MATH batches.
- **Tests.** 17 new scenarios pass here (`test_p009_s1_complete_admission`, `test_p009_s1_complete_oracle_drivers`).

## Notes
- **N1.** The timing is still uncalibrated for MATH students, as disclosed. If a student loops to the 1024-token cap on most problems, the endpoint time stays bounded by the base-model maximum observed at the same cap.
- **N2.** Preemption risk is unchanged and there is no checkpoint. A preempted S1 slot needs its own owner decision.
- **N3.** Local symbolic scoring is capped at 6000 s plus 5 s cleanup. Its output is not adjudicated: A4 re-scores independently and checks the fixed 50 disagreements.

## Corrections to my earlier wording (accepted from Codex)
- **cg overclaim.** In cg I wrote that the design "cannot by itself create a slope". That is too strong. The NC point threshold not firing does not prove a zero effect or equivalence. The correct statement is: the registered NC stop rule did not fire, with Δ = +0.99 pp.
- **Budget arithmetic.** In proxy comment 6187149432, "$23.80 不到 6 个 slot 的一半" is wrong: half of $39.30 is $19.65. The point stands, because $23.80 cannot fund all six slots, but the arithmetic was wrong.

## 科学信号检查 (science-signal check)
No S1 outcome yet. Dispatch of seed 17 n400 and n3200 may proceed once this report and cg are bound.
