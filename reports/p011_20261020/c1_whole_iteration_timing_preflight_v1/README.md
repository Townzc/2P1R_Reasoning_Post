# C1 complete-iteration timing correction — short exact CR pending

Claude N1 identified two excluded volume commits in each old chunk timing.
The worker now starts its timer at loop entry and ends after all three commits
and remote chunk_done. The next forecast uses that complete interval. A separate
COMPLETE_ITERATION_TIMES file preserves intervals and old body-only ack values;
the readonly checker verifies and replays the same full intervals. The final
proof/summary persistence is explicitly outside each chunk and remains within
the numerical future allowance; no recursive timing claim is made.

validate_spec now rejects missing/false whole_chunk_iteration_timing. The prior
source acceptance does not authorize this new runtime. A real timing basis for
batch1 forwards, FP32 loss, all commits and fixed overhead is still absent.
Old training durations are not direct C1 measurements; reviewer estimates and
synthetic fixtures are not selected actual caps or numerical acceptance.

Four new synthetic/mocked-body tests passed once in0.036s: all commits reach the
next forecast and read-only replay; old timing basis rejected; body-only duration
substitution rejected; timing-scope tampering rejected. Existing successful tests
were not rerun. No corpus was re-encoded and no actual model/forward was invoked.
The original approved input copy completed before this source edit. Eleven other
source files and all scientific token/mask/NLL definitions remain unchanged.

Review this bounded correction and the actual input A1 within the SAME C1 shared
request. Final numeric A2-lite must still bind the actual spec, timing, input,
source and original limits before upload or dispatch. No new independent gate.
