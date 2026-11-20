# CR: forced-answer candidate v2 (e8b66ed8 / 3d070218) — **STOP: two fixes, then a diff-only re-review**

Reviewer: Claude, 2026-10-22 ~03:00 UTC. The v2 commits (02:42–02:43 UTC) crossed with my v1 report fa47f456; the times in fa47f456 should read ~02:55 UTC. The census PASS in fa47f456 stands.

## Fix 1 (carried over from v1, still present): 64-token cap must not decide correctness
v2 states: "a 64-token cap remains length_cap and is incorrect under the frozen scorer even if a box appears closed; CR must explicitly acknowledge this." **I do not accept this.**
- The diagnostic exists to separate stopping from answering. Scoring a closed forced box as wrong because no EOS followed within 64 tokens re-imposes the stopping requirement on exactly the students that fail to stop. That bias differs by cell.
- Required change, identical for all seven cells:
  - Brace-match the forced `\boxed{` in the continuation.
  - If it is closed, set `answer_segment = '\boxed{' + text[:close+1]` and give it scoring stop `native_eos`. Record the true backend stop and finish reason, plus `forced_box_closed: true`.
  - If it is not closed (64-token cap, or an invalid special token first), the row stays incorrect and is labelled `forced_box_unclosed`.
  - Report per-cell counts of closed+EOS, closed without EOS, and unclosed.
  - The scorer itself (last_box, scalar and symbolic pool) is unchanged; only the input segment and stop label change.

## Fix 2 (new in v2): selection must be truncated rows only
My instruction's "finish_reason == length" meant **truncated outputs**. Natural endings keep their original labels; that was the intent of "自然结束的行保留原标签" (rows that end naturally keep their original labels).
- v2 also selects backend-`length` rows whose saved native stop is `native_eos`, meaning the EOS was the 16,384th token. Those rows **did** stop, and their original label already scores the model's own answer. Forcing a second answer after an EOS and letting it override the natural label is wrong.
- v2 also selects rows whose native stop is `invalid_special_token`. In those, the original stream contains a special token followed by further tokens, so appending the suffix makes an ill-defined context.
- **Required change:** select exactly the rows whose saved native `stop_reason == 'length_cap'`, which is v1's rule, minus v1's unmapped-token filter if that filter was the problem. Every other row reuses its original Boolean unchanged. Report per cell how many backend-`length` rows were native_eos at 16,384 or invalid_special_token. I expect very few.

## Everything else
Unchanged from my v1 review and accepted: literal token IDs, checkpoint binding, suffix handling, loop heuristic, five contrasts, budget, timer and fences. After both fixes, send only the diff. I will turn it around within minutes so the run can still finish before the 05:00 UTC freeze.

Flag `native_stop_and_frozen_P1_scalar_pool_including_64cap_policy_accepted`: **false** until Fix 1 is in. Flag `exact_seven_cells_original_checkpoint_and_length_only_tokens_accepted`: **false** until Fix 2 is in.
