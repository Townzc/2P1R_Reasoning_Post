# Claude audit 20261013ae — base endpoint G3 @ efeb6380: **PASS**; replacement proposal @ 428aa49c: **PASS-WITH-NOTES (proposal level only)**

## Part A. Base endpoint, independent G3 (raw → my decode → my stop → my parser)

**Verdict: PASS.** I reproduce the frozen primary result **638/1,319 = 48.370%** exactly. The Wilson 95% interval is 45.68–51.07%.

### Inputs I checked
- **Files:** the device copies match commit efeb6380 byte for byte (`gsm8k_test1319.jsonl` ea61d5f1…, `result.json` a318f0a6…, `batch_0000_raw.json` 716c74bb…).
- **Eval set:** `gsm8k_test1319.jsonl` is byte-identical to the `student_admission_v1` input set I accepted in 20261013ab.
- **Rows and gold:** all 1,319 rows are present, in eval-set order, across 83 raw files. Every gold scalar equals the `####` tail of its reference response.
- **Prompts:** `decode(input_ids) == "Problem: {prompt}\nSolution:\n"` holds for all 1,319 rows. This is the frozen `src/sft_data.py` template, and I used my own byte-level BPE decoder, not HF.
- **Ledger:** 83 `done` entries cover 1,319 items. For all 83, `raw_sha256` and `scored_sha256` equal the file bytes. The 83 `unit` entries carry identical problem_ids and config {16, 2048, 512}.
- **Terminal:**
  - The claim and terminal records share attempt `f8011560…`, status `completed`, with 756¢ reserved and charged as a reservation.
  - The run finished 1,624 s after its claim, inside the 5,492 s cap.
  - The provider app is stopped and 0 containers are owned.
- **Source:** all 30 `SOURCE_BINDING` files equal the 4b6f5180 blobs, and their digest is the intent `source_sha256` 3d87610b…. The same 30 files are byte-identical at 0be9e6e0, eb398fb1 and 121f17b1, the commits I reviewed. **The base therefore ran on reviewed code.**

### Stopping, re-derived independently
I wrote my own line-scan boundary detector (it does not use the frozen regex) and searched for the minimal token prefix.
- **Agreement:** all 1,319 events match on `stop_reason`, `retained_tokens`, `actual_eos_at_stop`, `answer_segment`, `boundary_offset` and `trigger_text`.
- **Mismatches: 0.**
- **Stop reasons:** native_eos 976, new_problem_boundary 302, length_cap 41.
- **Generated tokens:** 221,196, which matches.
- **`padded_tokens` 553,136** is the sum of per-row `batch_generated_steps`. That equals my n·(prompt_width+steps), 702,841, minus the prompt padding of 149,705. It matches exactly.

### Scoring

| Rule | Correct |
|---|---|
| **Frozen primary (`task_answer_correct`)** | **638** (I reproduce it from the rows; `summary.question_correct` agrees on every row) |
| My own marked-answer parser (all claims must agree) | 640 |
| My last-claim variant | 642 |
| Sensitivity: the 41 caps scored by their marked answer | +6 (not the frozen rule; caps stay incorrect) |

- **Direction:** both 640-vs-638 disagreements go the same way as every earlier class — **the frozen parser is stricter**. Both are frozen `unresolved_marked_answer` cases.
- **Two new classes for my list:**
  - **E4, abbreviation period in a prose answer.** `test/00375` reads "Answer: Mrs. Sherman fed 48 pieces…". `prose_scalar` rejects it because `rest` contains `.`.
  - **E5, unit rate in a prose answer.** `test/00507` reads "Answer: Janet would save $2/week…". `prose_scalar` rejects it because `rest` contains `/`.
- **Impact:** 2/1,319 ≈ 0.15 pp. **This is not a reason to change the frozen rule.** Both gold values match my parse.
- **Caution for the slides:** the base model often keeps writing after its answer (for example "Source: …" or "You are an AI assistant…"). 302/1,319 rows stop at a new-problem boundary rather than at EOS. Final-answer correctness does not certify reasoning, as the README already says.

## Part B. Replacement proposal `student_lr_replacement_proposal_v1` @ 428aa49c

**Verdict: PASS-WITH-NOTES, at proposal level.** Runtime admission still needs (i) direct owner confirmation in the Codex chat and (ii) a separate exact review of the new entry and binding. Codex is preparing that entry (`modal_student_replacements.py`, `student_replacement_binding.py`), and I will review it once it is requested.

### What checks out
- **Configs:**
  - Each replacement `config` deep-equals the `config` in the failed attempt's preserved `evidence/intent.json`.
  - Fields: draw 1, B1, p0, breadth/depth, `input_sha256` dae1bd27…, the same plan/rows files, 256 updates, 524,287 targets, seed 17, 1,319 endpoint outputs and `max_seconds` 6,001.
  - Reservations are 818¢ each, the same as the originals.
- **Budget arithmetic:**
  - 2 × 818 = 1,636.
  - 24,968 + 1,636 = 26,604, i.e. **$266.04**. The 24,968 is the aggregate I accepted in the completion-queue review.
  - No original reservation is reclaimed.
- **Preservation:** `failed_preservation_sha256` 5e5667a0… = sha256 of `student_lr_failures_closed_v1/RECONCILED.json`. `original_timing_roster_sha256` 3c22d003… is the roster in `student_frozen_lr_accepted_v1/RUNTIME_ACCEPTED.json` and `student_t1_dispatch_admission_v1/MANIFEST.json`.
- **Limits:** one call per slot, no automatic retry, no new arm, no endpoint selection, max 8 concurrency and the 21:00 PDT freeze are all stated.
- **Timing lineage:** keeping both failed attempts and mapping each logical member to exactly one replacement, with no host deletion, is the rule I asked for in ad.
- **Governance:** Codex treating my relay (comment 6154672302) as insufficient for a stage-cap change is **correct**, and matches our no-relayed-authority rule.

### Notes
- **R1 (LOW, digest encoding).**
  - `original_config_sha256` (b31a2865…, a5c9e178…) is sha256 of `json.dumps(cfg, sort_keys=True, indent=2)+"\n"`, a file-style encoding.
  - The ledger intents and every runtime binding use the canonical compact `digest()`, which gives **b8217806…** and **f04e7f28…** for the same configs.
  - The configs are identical, but the admission check must compare `digest(cfg)` to the ledger values. Please label the encoding, or record the canonical digests in the admission packet.
- **R2 (REQUIRED for admission, project-wide sum).** The proposal states the $450 ceiling and $50 protection but does not show the sum. The admission packet should list committed and reserved amounts for every stage, including pre-P008, and show that the total with P008 = $266.04 is ≤ $400.
- **R3 (REQUIRED, capacity).** All 8 frozen-LR T1 students are dispatched, so max-8 student concurrency is full. The replacements can start only after two of them close, and only through the same `dispatch_lock` / `occupied_capacity` check. The admission packet should show that check run at dispatch time; the proposal must not assume capacity is free.
- **R4 (advisory, cap headroom).**
  - The 6,001 s cap now has to cover 256 updates plus a **1,319-question** endpoint. The P007B T1 walls of 3,488–5,320 s were measured with the 431-question endpoint.
  - The base endpoint alone took about 1,600 s of wall time.
  - Because of R3, at least two of the eight T1 walls will be measured before any replacement starts. **If those walls approach the cap (above about 5,400 s), flag it before dispatching the replacements.** I am not asking to change the cap. The two replacements must keep identical caps.

## Effect on N2
N2 stays OPEN. Its required set is: 8 frozen-LR T1 + 2 replacements + base (closed now, 1,607.7 s wall), with the 2 failed attempts kept in the lineage. I will review the numerical N2 once all of these exist.
