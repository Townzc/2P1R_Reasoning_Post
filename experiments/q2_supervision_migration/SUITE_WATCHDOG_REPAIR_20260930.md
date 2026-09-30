# Retain per-test semantics when the suite watchdog expires

R_future stopped after25 committed updates, with416 returned TRAIN outputs.
The failed sample8 in batch25 is Mbpp/599: all3 base tests and the first34 extra
tests passed. The outer62-second process watchdog stopped the88-test extra suite.
The saved candidate loops over natural numbers; test34 includes99,999,994, and
its unchanged per-test allowance is about5.03s. The original60-second suite cap
can expire after multiple individually admissible calls. Neither this timeout
nor this engineering failure establishes a negative scientific result.

The opt-in CPU diagnostic preserves pinned EvalPlus inputs, order, references,
oracles and every per-test limit. It retains the initialization timer and allows
an outer budget min(180,sum(per-test limits)+1) seconds, plus one second cleanup.
Only a normally exited child with a complete all-pass suite or an observed failed
test establishes a new diagnostic verdict. An externally killed/unknown child
remains unknown. Previously known PASS/FAIL outcomes are never rerun; the original
timeout is retained in detail and all historical records stay immutable. This is
an explicit engineering amendment to the outer safety watchdog, not a claim that
a timeout was itself a wrong answer. Per-request accounting rises to600s only
for this opt-in mode; original phase and shared/provider deadlines always win.

A210-second CPU-only gate checks the exact saved sample and authored pass/fail
controls. It must resolve the suite and retain its34 previously passing tests
before use.54 authored CPU checks passed in preparation. No new generation,
optimizer update or user annotation is produced by the diagnostic.

The exception handler retained R's full25-step model/optimizer/Trainer checkpoint.
However, the failed batch's sampling log-probabilities were not persisted, and
exact vLLM RNG recovery is not verified. A checkpoint is therefore not sufficient
proof of exact continuation of that batch. Do not silently regenerate it, disable
importance correction, or claim an exact resume. W_prefix/W_future are complete;
three original state evaluations remain possible without replay. R_future and
C comparisons remain unavailable unless an explicitly approved repair can finish
them within the original budget. No new restart is authorized by this source.

## Gate outcome and admitted fallback

The prepared suite watchdog gate FAILED after35.37s. The new execution failed
test18, whereas the earlier run passed its first34 tests. This timing-sensitive
change does not establish a stable diagnostic, and the suite-recovery opt-in
is not admitted for the remaining model work. Preserve both observations.

Only eval_R, eval_W_prefix and eval_W_future remain runnable without repeating
training or evaluating an unplanned partial checkpoint. An explicit evaluation
option retains unresolved verdicts instead of aborting all later samples; the
training reward contract remains strict. Every planned output is kept, unknown
counts are reported, and point estimates requiring complete labels cannot be
claimed when that gate fails. Scorer process/transport failures still abort.
No scientific reward, test oracle, sample seed or planned state is added. The
original 09:24:41UTC worker/09:47UTC provider deadlines remain unchanged.
