# Combined review (~06:58 UTC): ext-3B v2 diff, ext-3B actual A2, and the forced-answer relaunch launcher

## 1. ext-3B runtime v2 diff (c1a73d32, request 78e64679) — **PASS**
There are two changes. The owned score child now imports and snapshots `ext3b_math_scoring.score_once`; v1 pointed it at the old D2 driver, which was a real bug and is fixed. The runtime contract's SPEC locator now points to v2. The other 84 bindings are unchanged from 61a14c85 (PASS 65eb8c30). All 12 source flags are true for v2.

## 2. ext-3B actual-input and numeric A2-lite (5f1003c5, request fd62e95b) — **PASS**
**What I recomputed independently.**
- I took the old 12,096-cell ROW_METADATA from the published f679fa5c archive and the new packet's ROW_METADATA. The new one is **exactly** the first 9,072 rows of the old one.
- B′ = 123,808,531, which is 2.961× A7's B. The small cell's single pass is 41,282,839 tokens, which gives q = 2 with a remainder of 41,242,853 and E = 2.99903.
- Running the repo's original `whole_schedule` on both rosters reproduces the saved PLAN files **byte-identically**. U = 1,935 for both cells. In the large cell all 9,072 answers appear once. In the small cell 3,020 answers appear 3 times and 4 appear twice.
- `RATES_S-F15` equals `learning_rates(1935, 'S-F15')` to within about 1.7e-21 (float serialization), and `compatible_frozen_rates` returns True.

**Fit with measured A7 timing (projection, not a guarantee).** 1,935 updates × about 9.9 s per cycle is about 5.3 h. Adding 5–15% for longer sequences and three 500-step checkpoints brings training to about 5.6–6.2 h. MATH-only evaluation (2,500 rows) takes 0.8–1.7 h. The total of about 6.4–7.9 h is within the 7.97 h money window at $45/cell. Margin is thin in the worst case, which is acceptable: greedy runs first, and partial completion is preserved.

**Not accessed:** private model binaries and the full 1.3 GB encoded corpus. I verified the prefix through ROW_METADATA identity plus Codex's line-level prefix check (cf630e86 code review).

Flags (all true): exact12096_prefix… / equal_measured_Bprime… same U and actual E / original model receipts, no gold upload / actual job manifest bound to v2 SPEC with the 90/45 caps, checkpoint and resume.

**Both 3B gates are now PASS, so both cells may be launched in parallel, subject to the fresh budget and slot checks.**

## 3. Forced-answer delegated relaunch (3396e258, request 971ecc91) — **PASS-WITH-NOTES**
The owner's direct words to Codex ("今晚权限我交给Claude了，按他的判断即可，不要停下来等我答复", i.e. "I've handed tonight's authority to Claude; go by his judgment and don't stop to wait for my reply") together with decision 1 in 469f0fc2 authorize one relaunch.
- **Launcher.** The entry point is module-qualified: `experiments.p011.modal_forced_answer_retry`, with sources copied into /workspace and PYTHONPATH=/workspace. The worker writes an `imported` acknowledgement as its first action, which the 600 s watchdog checks. Cells run as `python -m experiments.p011.forced_answer_retry_cell`, which only re-points `STORE`. Because `forced_answer_worker.run` reads the module global at call time, the redirect takes effect, and `REMOTE` is asserted to be unchanged.
- **Parent-failure checks.** The exact pre-claim failure is required: no claim, no terminal state, every cell not_started, STOPPED0. The original upload is reused, and the run and results paths must not exist yet. There is a new r2 store and a permanent one-relaunch fence. Science, inputs, the scorer adapter and the analysis are unchanged; only paths are routed.
- **Budget.** 12 minus the failed attempt's compute upper bound minus $3 in noncompute allowances, at $4.3952/h with 32 GiB. If the failed upper is about $1–2, the worker window is about 1.4–1.6 h. Forced-answer needs about 160M prefill tokens plus 7 model loads, which I estimate at 1.0–1.7 h. **It may not finish D2**, the last cell. Partial cells are kept unscored and never zero-filled. Accepted as a disclosed risk within the $12 total.
- All 7 flags are true.
