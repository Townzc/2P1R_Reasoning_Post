# Claude audit 20261014as — exploratory-20261014-three-run-code-data-r1 @ 32c473d6: **PASS-WITH-NOTES** (code + data/input binding)

Scope: `exploratory-20261014-code-and-data`, i.e. the exact source, spec and input binding for the three owner-authorized exploratory slots. This is not a P008 extension and not a result review.

**Bound identities (as checked):**
- target commit `32c473d6d1eebbbbf81792df639ab5b36674d851`
- 37 source files, canonical digest `5b2b22755b26afbd43c29d650a98dd8c99f9f92e4e97932f92f42258a24f37e4`; every file sha equals its blob, the `admission_v1/source/` copies are byte-identical, and the set equals SOURCE_BUNDLE
- ADMISSION: canonical digest `1ba8f792e1a70410bbcdbbf132eb920ba33120b900181454f27f5de6aeee409c`, file sha `ceb0d47b10d337f3afaa65e7d6fb8aef7378ee261ef27c2e96959e21fa2e0d3d`
- input manifest file sha `d0d4a793138145a303235a529e7f6c8c42ace7d96499c605935c63b50bedecfd`; 14/14 input files match
- I/O helper `scripts/exploratory_20261014_io.py` sha `926ffd4d8e97022d044c673939a0d5f1a4ca314e748b3f5f040f1dc904791571`; equals the admission copy and IO_HELPER_BINDING
- SELECTION file sha `f5f44a00…` = `ADMISSION.selection_file_sha256`

## Q1. Wrong-answer selection — independently reproduced: YES
I recomputed the selection from the published `pool_d1_v1` scored batches (7,420 rows) and `frozen_wallets.parent_order`, without importing Codex's selector. Order: parent order, then attempt. Eligible means native EOS, not truncated, last token in {151643, 151645}, frozen `marked_answer_v1` status `parsed`, `answer_correct` False, and not an exact within-parent duplicate.
- The `duplicate_of` provenance re-derives with **0 mismatches**.
- **864 eligible; the first 429 come from 101 parents.** The ordered candidate ids are identical to SELECTION, and all 429 records are byte-identical as JSON.
- Each training `response` equals the original pool text. My own byte-level BPE decode of the original `text_token_ids` equals the response for 429/429. `n_supervised` = text tokens + 1 EOS for 428 rows; one row differs by 0, which is a boundary-merge case of the joint tokenization.
- The gold answer is metadata only. No new teacher output and no score repair.

## Q2. Prompts, examples, models: YES
- **Dev examples** are exactly the first four of `sorted(train ids, key=stable_seed('dev_split',0,id))` (02125, 04525, 02445, 06596). None is in test or among the selected parents.
- **Test file** sha `ea61d5f1…` is identical to the P008 base/T1/T8 packets.
- **Independent decode of all 3 × 1,319 prompt rows** with my own BPE decoder from the frozen tokenizer.json. **0 mismatches** against the expected strings:
  - base_4shot = 4 × (`Problem: …\nSolution:\n` + reference + `\n\n`) + `Problem: {q}\nSolution:\n`;
  - wrong_teacher_t1 = `Problem: {q}\nSolution:\n`;
  - instruct_0shot = `<|im_start|>system\n{SYSTEM}<|im_end|>\n<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n`.
- **Lengths** are 771–936 / 27–192 / 51–216, all ≤ 2048 − 512. The base and student prompts contain no EOS ids.
- **Parser.** `marked_answer_v1` accepts `####` as well as `\boxed`, so the 4-shot GSM8K-style demonstrations do not bias parsing. The task boundary (`Problem:`) stops base continuations exactly as in base_v1.
- **Instruct model.** tokenizer eos `<|im_end|>` (151645), pad `<|endoftext|>`. The runtime stops on {151645, 151643}, normalizes only for the stop detector, keeps the saved ids, uses greedy decoding with repetition_penalty 1.0, and does not inherit the card's sampling defaults. The weight is pinned at revision `989aa798…` and sha `dd924a11…` (3,087,467,144 B), fetched by one GET inside the paid worker, with no retry and the partial download kept.
- **Disclosure.** The system prompt is the Math-card instruction applied to the general Instruct model. This is disclosed and is not claimed as the model-card default.

## Q3. Wrong student dose: YES
- `schedule(n_supervised, 524287, 256, 17)` reproduces the published plan exactly (all keys).
- Σ targets = 524,287 over 256 updates. `lrs` equals the published `d1_b1_p0_breadth_t1_plan.json` vector byte-for-byte.
- `row_path_ids` equals the selection order. Exposures: 219×3 and 210×4 (q = 3); zero-exposure rows: 0.
- The runtime reuses `rt.new_model(adapt=True)`, `rt.train`, `validate_plan` and `save_steps=(256,)`, followed by the sole endpoint. The oracle checks `state.lrs == plan.lrs`.
- **No host LR recomputation**: grep finds no `lrs(` or `cos(` in the new files.

## Q4. Execution, caps, budget: YES
- **Entry guards.** Before dispatch the entry requires:
  - the published HEAD equals `origin` and the bytes equal HEAD;
  - an exact release/acceptance/upload binding;
  - a full 6,701 s window, checked both before and after the provider checks;
  - no prior local destination, remote claim/intent/terminal/unit/attempt key or remote directory;
  - occupied capacity < 3, counting pending calls and unmatched containers.
- **Worker.** stop = min(entry + 6001, deadline − 30), with a hard `os._exit` timer; platform limit 6061, startup 600; `retries=0`, single-use containers, `max_containers=3`. Failure records `failed` with the full reservation.
- **Reservation.** ceil(6761 × 4.393584 / 3600 × 100) = **826¢** per slot. 3 × 826 = 2,478, plus 522 = **3,000¢**.
- **Project total.** 87.66 + 266.44 + 30 = $384.10 ≤ $450, before even counting the $50 protection. Not an invoice.
- **Deadline.** The plan deadline is 14:00 UTC, so **the last admissible launch is about 12:08 UTC (05:08 PDT)**. All three can run in parallel.

## Q5. Oracle and collector: YES (code)
- `audit_batch` independently re-derives each stop event, the post-stop padding, the decoded text, the completion and legacy scores, and the cap-is-incorrect rule for every batch at runtime.
- `audit_exploratory_20261014.py` binds release, ledger, manifest, block journal, dose and state.
- The collector is completed-only and create-only, never overwrites remote files, and checks that the provider is stopped.
- No gold is used in prompt selection, inference, stop decisions or training targets.

## Tests
- Locally: `tests.test_exploratory_20261014` + `tests.test_exploratory_batch_20261014` ran **8 pure tests OK**. The NativeStop class and the batch module need `transformers`, which is not installable in this sandbox.
- Codex's logs show 11/11 and 2/2 OK. **I did not execute the transformers-dependent fixtures.**

## Science-signal check (new standing section)
- **Exp 1** (base 4-shot, Instruct 0-shot) is cheap and directly tests the "SFT mostly teaches format" reading. Expected outcomes: a 4-shot base near 65–70% supports it; near 50% weakens it.
- **Exp 2** is weaker evidence than its name suggests, for two reasons:
  1. Its 429 answers come from 101 questions (about 4.2 per question). Coverage therefore resembles **depth**, not breadth.
  2. By my own per-question labels (20261014ar, AI judgement), **45 of the 429 selected answers (10%) are on questions whose gold label I judged wrong**, so the teacher answer there is likely *correct*. Another **127 (30%) are on ambiguous or flawed questions.**

## Notes
- **N1 (MEDIUM, interpretation).** Report **d1_b1_p0_depth_t1 replacement (965/1,319; 121 questions; 469 answers; q = 3)** alongside 969 as the closer coverage/exposure reference. Disclose the label-noise share above.
  - If wrong_teacher_t1 ≈ 72%: this is consistent with "answer correctness matters little here", but it does not isolate correctness.
  - If it is clearly lower: content matters at matched coverage.
  - Either way, no causal correctness claim.
- **N2 (LOW, ops).** The runtime re-serializes every prompt with the image's `transformers==4.56.2` and raises on any difference. That fails closed, but for `instruct_0shot` it would trigger only after the 3 GB download. Please confirm the local preparation used the same 4.56.2 version.
- **N3 (INFO).** Plan deadline 14:00 UTC; the last launch must be ≤ ~12:08 UTC. A late slot stays unsubmitted, as the packet says.

Verdict: **PASS-WITH-NOTES** for the exact source/spec/input binding above. The runtime/numeric gates in the code still apply at dispatch.
