# Claude audit 20261013ag — p008-eight-original-t1-outcomes-r1 @ 860aa4cb: **PASS**

## Scope
The scope is the 8 original T1 packets in `student_t1_eight_v1`. The 2 D1 B1/p0 cells are missing from this packet, and their replacements are not included or imputed.

To confirm the device copies are the published files, I compared git blob ids for the 2,682 endpoint, result, summary, oracle and eval files in the packet. The device worktree list and the commit 860aa4cb list have the same digest (67c53968…), so the device copies equal the published bytes.

## Q1. Raw endpoints: independent decode and rescore of all 10,552 outputs — PASS
I used the same script as for base (`g3_endpoint.py`, published in 20261013ae). It does its own byte-level BPE decoding, its own line-scan boundary and minimal-prefix stop logic, and its own marked-answer parser.

Results:
- Every run has 1,319 rows across 83 raw files, in eval-set order. Each prompt decodes to the frozen template.
- **0 event disagreements** across 10,552 rows on stop reason, retained tokens, EOS flag, answer segment, boundary offset and trigger.
- The students have **0 new-problem-boundary stops**. The base model had 302. Every non-cap row ended at native EOS.
- Generated-token totals and `padded_tokens` match exactly for every run.
- The frozen primary totals and the length caps reproduce exactly, and `summary.question_correct` agrees row by row.

| run | frozen primary | acc. [Wilson 95%] | caps (incorrect) | my parser | my last-claim | caps with marked answer correct (sensitivity) | wall s |
|---|---|---|---|---|---|---|---|
| `d1_b1_p4_breadth_t1` | **954** | 72.33% [69.9, 74.7] | 39 | 957 | 959 | +1 | 3,664 |
| `d1_b1_p4_depth_t1` | **945** | 71.65% [69.2, 74.0] | 36 | 946 | 948 | +3 | 3,111 |
| `d1_b8_p0_breadth_t1` (bridge) | **942** | 71.42% [68.9, 73.8] | 43 | 943 | 944 | +1 | 3,530 |
| `d1_b8_p0_depth_t1` (bridge) | **949** | 71.95% [69.5, 74.3] | 49 | 950 | 950 | +0 | 2,793 |
| `d2_b1_p0_breadth_t1` | **968** | 73.39% [70.9, 75.7] | 41 | 968 | 968 | +3 | 2,757 |
| `d2_b1_p0_depth_t1` | **970** | 73.54% [71.1, 75.9] | 35 | 970 | 971 | +1 | 4,000 |
| `d2_b1_p4_breadth_t1` | **951** | 72.10% [69.6, 74.5] | 40 | 951 | 951 | +4 | 3,534 |
| `d2_b1_p4_depth_t1` | **943** | 71.49% [69.0, 73.9] | 39 | 943 | 943 | +3 | 3,526 |

For comparison, base (20261013ae) scored 638 (48.37%).

### Parser disagreements, classified honestly
There are 6 rows where my parser says correct and the frozen parser says incorrect:
- **3 rows are E1 (`\boxed{25\%}` ×2, `\boxed{10\%}`).** This is the known class where the frozen parser is stricter.
- **3 rows are errors in MY parser, and the frozen parser is right.** The answers are `\boxed{240000C}`, `\boxed{30C}` and `\boxed{240000 \times \text{cost per piece}}`. The student left an unknown variable in the boxed answer. My number regex has no trailing word-character guard, so it extracted 240000 or 30. These should be scored incorrect, and the frozen parser does so.

So my "my parser" column overstates by up to 3 in `d1_b1_p4_*`. **Lesson for my checklist:** a numeric-extraction parser needs a guard against trailing variables and units. I am not changing the script after the fact; this note is the record.

Net effect: the frozen primary is exact, and the only reviewer-side disagreement in its favour is E1 (≤ 1 row per run). **There is no reason to change the frozen rule.**

## Q2. Source, config, dose, blocks, state and terminal — PASS for all 8
This check ran in the container, on git objects at 860aa4cb only.
- **Source.** `SOURCE_BINDING.source_files` equals the 32-source frozen-LR bundle that I reviewed at c5053814, byte for byte. The intent `source_sha256` equals the digest of that bundle.
- **Config.** The config equals the original spec config (spec ab49b0a6). The intent `config_sha256` equals `digest(config)`.
- **Ledger chain.** claim `intent_sha256` = `digest(intent)`, terminal `claim_sha256` = `digest(claim)`, and terminal `evidence_sha256` = `digest(artifact_manifest)`. Every terminal status is `completed`.
- **Recipe.** `recipe.lrs` equals `LR_VECTORS["256"]` exactly, and `recipe.schedule` equals the frozen per-student plan's `updates`. I reproduced those plans myself in 20261013ab. `identity.config` equals the config and carries no `physical_run_id`.
- **Dose.** Across the 256 `update_XXXX` records:
  - step i has index list = schedule[i];
  - lr = LR[i];
  - cumulative targets add up to **524,287**, equal to the plan's `supervised_targets`.
- **Blocks.** There are 16 `training_block_*` records, and the block journal shows (16, 256, 32 boundary calls).
- **Provider.** The app is stopped and owns 0 containers.
- **Local oracle.** It passed, and its correct counts, updates and targets agree with mine.
- **State.** `checkpoint_0256` publishes only `manifest.json`. **As Codex says, the state SHA (e.g. 53b51028… for d1_b1_p4_breadth) is a recorded checksum, not something I inspected externally.** I verified no binary.
- **Walls.** They range from 2,757 to 4,000 s, all under the 5,400 s flag and the 6,001 s cap. The total is about 27,000 s, roughly **$32.8** at the H100 rate. That is a rate estimate, not an invoice.

## Q3. Collection after the DNS disconnect — PASS
Each run has a `COLLECTION.json` with these fields:
- `collected_after_local_disconnect: true`;
- `new_model_calls: 0`;
- `original_network_error_preserved: true`;
- the volume paths.

`RECEIPT_READBACK_VERIFIED.json` sha equals `COLLECTION.readback_proof_sha256`. The sha values for `result.json` and `artifact_manifest.json` in the readback proof equal the published files. It also records `new_remote_writes: 0` and the original `call_id`. **This closes my L1 from 20261013af.**

I did not see the local "one-collector repair / 202 fresh records" step itself. I checked only its published outputs.

## Q4. Scope — PASS
- SUMMARY lists `completed_original_t1: 8`, `missing_logical_cells` = the two D1 B1/p0 cells, `replacement_results_included: false`, `t8_outcomes_available: false` and `final_cpu_integrity_complete: false`.
- Failed-parent records are preserved.
- There is no imputation, no effect gate and no T8 inference.

## Caveats for anyone using these numbers (slides included)
- **Descriptive only.** The eight cells span about 71.4–73.5%, and every Wilson interval overlaps every other.
- **The design is incomplete.** D1 B1/p0 has no breadth-vs-depth contrast until the replacements land, and the T8 cells do not exist yet. Do not read a breadth/depth or price effect from this table. Do not pick a winning draw or seed.
- **Draw versus initialization.** The highest pair is D2 B1/p0 (968/970), but its D1 counterpart is the missing cell, so neither a draw comparison nor a price comparison can be made yet. Both draws use the same initialization seed and differ in their data paths, so draw-to-draw spread is part of the noise floor.
- **Test-set exposure.** The test set was researcher-seen in September, and final-answer correctness does not certify the reasoning.
