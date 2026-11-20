# CR: ext-3B prefix input / reschedule (target cf630e86, request 8ca92aa0) — **PASS**

Reviewer: Claude, 2026-10-22 ~06:30 UTC.

## Which 3B definition applies
The owner's **direct** message to Codex, "4B 按 ②+③ 执行" (run 4B with ② + ③), defines 9,072×1 versus the first **3,024** at about E3. Codex recorded it at about 05:58 UTC. **This direct owner choice takes precedence** over the 9,072 / 2,268 (E≈4) variant I recorded under delegation in 469f0fc2. I withdraw that variant; **3,024 stands.** The interpretation is 3:1 repetition versus new questions at about 3× the original dose.

## Code review (ext3b_contract.py, prepare_p011_ext3b_inputs.py)
- `prefix_metadata` requires exactly 12,096 unique path and parent IDs with positive doses, and returns rows[:9072] and rows[:3024]. In the ext-4B builder, both ROW_METADATA and ENCODED.jsonl were written in the selected-parent order, so these prefixes are the first 9,072 and first 3,024 questions of the fixed `p011-ext-4B-20261022` order, with unchanged answers.
- `copy_prefix` copies the first 9,072 encoded lines byte for byte and checks each line's path, parent, n_supervised and n_processed against the metadata. Nothing is encoded again.
- B′ is the sum of n_supervised over the 9,072 rows, and both cells use it in the original `whole_schedule`, so U = ceil(B′/64,000) and is identical for both. The rates come from `learning_rates(U, 'S-F15')`.
- For the small cell I expect B′ / one-pass(3,024) ≈ 2.99, giving q = 2 plus a large remainder: most answers appear 3 times and a few appear 2 times. The plan records q, the effective E and the presentation-count distribution, which is fine. Please make sure the actual A2 states these numbers explicitly.
- Endpoint files are symlinks to the accepted originals, with the manifest pointing at the prior inventory hashes. MATH-first ordering and scoped scoring belong to the runtime and need their own diff CR.

Flags: all five required flags are **true** (exact prefix, nested subset, byte reuse, equal B′ and U with the original q/q+1 schedule and LR, input-only with no GPU).

## Forced-answer relaunch
In 469f0fc2 I recorded the owner's delegation verbatim ("今晚你觉得需要重跑就重跑…我给你这个权限", roughly "rerun tonight whatever you judge needs it… I'm giving you that authority"), and under it one forced-answer relaunch at ≤ $12 total. EXT3B_OWNER_OPTIONS notes `no_new_forced_retry_authorized`, which reflects only the "②+③" message. If Codex needs the owner's direct words for the forced relaunch, it should wait for them. Please do not treat silence as refusal; the delegation record stands.
