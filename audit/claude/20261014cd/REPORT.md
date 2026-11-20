# Audit 20261014cd: NC parent A4 + NC3200 replacement runtime (two scopes)

This one report covers two requests. Each scope has its own decision and bindings.

---

## Part A: `p009-stage1-NC-preemption-and-n400-A4-r1`

- **Scope:** `p009-stage1-NC-preemption-and-complete-n400-A4-disposition`
- **Target:** `ab271a94749570308690b3eda2ee6a5c68c3618c`
- **Manifest:** `74c4590c8b112ba1b2623824c0bc2bb82facc3c7a590fe59a0ba1bb9eecec609`. All 31 members match.
- **Parent preservation (`PRESERVED.json`):** `75f29c7560e963f8e28777906158762b30c449de688fc2d2e7726a1eb4fa9b8b`
- **NC400 state SHA (public, binary not loaded):** `f9aca4bf01e944528e723d252b16d7229b3057d18ee1544d81c7e0d25815e209`

### Decision: PASS
- actual_n400_integrity = **PASS**
- failed_n3200_preservation = **PASS**
- paired_NC_gate_available = **false**
- S1_admitted = **false**

### actual_n400_integrity (independent; `nc400_rescore.py`)
- **Coverage.** All 6 raw batches from the original-byte archive cover 1319 unique IDs in frozen `NC_ENDPOINT` order. Every `prompt_token_ids` equals the frozen `input_ids`, and every `candidate_id` matches. No token is out of vocabulary.
- **Scoring.** My own BPE decoder ran the frozen `first_stop` (EOS 151643, cap 512) and `completion_score` against the gold in `gsm8k_test1319.jsonl` (`ea61d5f1…`).
  - Result: **954/1319 correct**; 1263 native EOS and 56 length caps, all counted wrong; 0 unknown.
  - Compared with the copied full oracle: **0 event mismatches, 0 score mismatches, 0 disagreements** in `question_correct`. Every row's `raw_file_sha256` matches.
- **Dose.** For all 1024 updates, each intent and ack equals the update recomputed from `nc17_n400_plan` and `nc17_n400_encoded` (indices, LR, per-update supervised and processed tokens, cumulative sums). That gives **2,097,148 targets** and 2,558,460 processed, matching the oracle.
- **Units.** There are 1095 completed units: 1024 updates + 64 blocks + `terminal_merge` + 6 endpoint batches. None are missing or extra.
- **Merge and exit.** The merge ran in fp32 and saved in bf16, with 0 updates after the terminal save. The training process exited with code 0, joined before the endpoint started.

### failed_n3200_preservation
- **Terminal status.** Both copies (`RECORDS_BEFORE` and `RECORDS_AFTER`) are identical. The terminal reads `status=failed` with `actual_cost_cents=655` (a placeholder for the reservation, not a bill).
- **Saved prefix.** The archive holds 952 completed units (**896 updates** + 56 blocks), with 0 endpoint units and **0 `.pt`/`.safetensors` files**.
- **Partial dose.** For steps 1–896, the dose recomputes exactly from the n3200 plan: **1,834,908 targets** and 2,232,929 processed. That leaves 262,240 targets never trained.
- **Timing records.** There are 56 forecasts and 55 timings. The last block's timing was interrupted.
- **CLI excerpts.**
  - Line 221 is Modal's message: *"Container terminated due to preemption. Your Function will be restarted with the same input."*
  - The automatic restart then raised `GuardError: run is already terminal; missing claims cannot authorize replay` before any claim was made.
  - The failure projection is `KeyboardInterrupt` inside `receive()`, which is what a container kill looks like.
- **Limit.** I saw the excerpts and the SHA of the private log (`b0a784c1…`), not the full private log.
- **Lineage.** No missing-to-zero substitution, no fake completion, no operator retry.

### 科学信号检查 (science-signal check, single arm only)
- **NC400 = 954/1319 = 72.33%.** This sits inside the range of the 18 P008 students (about 70.9–75.1%) and matches the earlier plateau.
- Taken alone, this arm says nothing about whether the NC curve is flat. The paired gate stays **unavailable** until a complete NC3200 exists.

---

## Part B: `p009-stage1-NC3200-independent-replacement-r1`

- **Scope:** `p009-stage1-NC3200-independent-replacement-runtime-and-numeric`
- **Target:** `3938689cb3156d9a67773f49d8d7cd7f4390bc9c`
- **Manifest:** `9a6a0509327da49f35aeb6116581a2afd3bfa1b5e49dc12e5d12270cf80585e9`
- **spec_sha256:** `35b1755261290f97c4da03c1121b73ad1cb47e0abf52f657790464bfc381dcaf`. Recomputed.
- **timing_sha256:** `e3dc389f7cd5f1a6c180d948504870248b0b0d717ee309a43a73a484ad4fa817`. Recomputed.
- **owner_authority_file_sha256:** `108c82f933990473119f48b186223057f1ab3a0f92769e666bbe2b34be8e0ae3`
- **Parent bindings:**
  - parent_packet_target `ab271a94…`
  - parent_packet_manifest_sha256 `74c4590c…`
  - parent_preservation_file_sha256 `75f29c75…`
- **Input bindings:** input_basis_file_sha256 `af7149bd…`, input_archive_file_sha256 `266fde7c…`
- **source_files:** the exact 49-entry map in `SOURCE_BINDING.json`. All 42 cb-accepted entries are byte-identical. The 7 new files are:
  - `modal_stage1_nc_replacement.py`
  - `stage1_nc_replacement_{binding,contract,runtime,training_process}.py`
  - `scripts/{audit_p009_stage1_nc_replacement,p009_stage1_nc_replacement_io}.py`

### Decision: PASS-WITH-NOTES
- all_20_training_hosts_included = true
- failed_parent_interval_retained_as_proxy = true
- uncalibrated_timing_proxy_scope_accepted = true
- training_process_exit_before_vllm = true
- new_reserved_cents = 655
- prior_stage1_reserved_cents = 1310
- first_paid_measurement_exceptions = 0
- independent_failed_parent_replacement_accepted = **true**

### What I checked
**The science is unchanged.**
- `stage1_nc_replacement_runtime.py` and `_training_process.py` differ from the accepted originals only in their contract/child import and a header comment.
- The contract reuses the original `forecast`, `transport_checked` and `cents`, and returns `original_slot('nc_s17_n3200')`. That is the same seed 17, n3200, 1024 updates / 2,097,148 targets, 4500/4560/600/5200 s windows and 655¢.
- The binding requires every original source byte, input, base model, gold, engine kwargs and G0/input/internal-only report to equal the parent spec. It also runs the original `validate` on the parent release.

**The failed run cannot be overwritten or reused.**
- The binding runs under a new campaign and a new logical key, `midpoint/p009-stage1-logical/nc_s17_n3200/independent_replacement_r1`.
- `parent_records` requires the complete original lineage: claim, intent, terminal, dispatch and attempt for both runs. NC400 must stay `completed`, NC3200 must stay `failed`, and the failure evidence digest must equal `bcf84754…`.
- `require_unused` blocks dispatch if any replacement record exists, or any logical record other than the two originals.
- All 9 original apps must be stopped.
- The plan deadline is the original absolute deadline, 2026-10-21 03:06 UTC.

**Timing (reproduced independently).**
- From the archives I rebuilt the training vector: the original 1184 + NC400's 64 full blocks + the 55 forecast deltas of the failed run + the 29.55 s closure proxy, **1304 total, identical** to the packet.
- The endpoint vector is 12 + NC400's 6 = 18.
- The maximum block (43.31 s) and maximum endpoint batch (20.41 s) are still from the old hosts. NC400's own maxima were 27.31 s and 8.25 s.
- Forecast: **4,193 s**, **618¢** (≤ 655¢). Against the 3,690¢ remaining in Stage 1, it is admitted.
- Stage 1 after this reservation: 1,965 of 5,000¢. No release and no borrowing.

**Tests.** I set up the fixture exactly as `TEST_FIXTURE_README.md` says, and **all 16 new tests pass**. Without that layout, 12 of them error on a missing path, as the README warns.

### Notes
- **N1. Not blind to NC400 (disclosed by Codex).** The NC400 score (954) was read at 04:58 UTC. My 05:11 comment, which recommended deciding before the score was seen, was already out of date when I posted it. The owner's answer was recorded at 05:20.
  - I still judge the bias risk as low. The recipe is identical. The only other option was "NC unavailable, so Stage 1 stops." The NC400 score alone does not reveal the paired Δ.
  - The paper must disclose this.
  - The owner authority already allows one call and no retry. If the replacement also fails, NC is reported as incomplete, with no second exception decided after seeing results.
- **N2. Preemption can happen again.** The parent was preempted after about 23 minutes (896 updates). There is still no checkpoint, so another preemption costs another $6.55 and ends NC under N1.
- **N3. Owner authority.** It is recorded from Codex's chat, which I cannot see. I am asking the owner to confirm it directly to me as well. This does not block, because the file SHA is bound.
- **N4.** The cc N1 publisher partial-write note is unchanged. The replacement pair will need its own pair publisher binding (NC400 + replacement) before the registered NC decision runs. The cc publisher hard-codes `RUNS` and the original campaign.

## 科学信号检查 (science-signal check)
Still no paired NC result. NC400 alone is 72.33%. S1 stays blocked until the replacement finishes and passes A4.
