# Final Q2 completion stopped at scoring admission

September 30, 2026. **Q2 is paused under the owner's stop condition.** The final
missing-control completion was authorized and designed, but its saved-output
comparability gate failed before any new training or evaluation generation.
This is an engineering/measurement failure, not evidence against the scientific
hypothesis. All W/R, W/C and C/R matched-future comparisons remain unavailable.

## What was repaired and actually checked

Source `34a3afab08ea8610f320c73828fc5acdb221ea41` was published before execution.
The repair records candidate/test/oracle exceptions, checks the entire previously
observed passing prefix before accepting recovery, preserves raw backend tokens
and sampling logprobs before decoding, and validates checkpoint files against
committed optimizer receipts. A serial no-retry queue was frozen at 384 updates,
6,144 training outputs and3,072 evaluation outputs, under a separate 3-hour cap.

All 111 authored unit checks passed locally and on the pinned Linux runtime.
Five Linux authored controls also passed: valid answer, wrong answer, syntax
error, initialization error, and per-test timeout. These demonstrate the guard's
basic classifications and rejection behavior; they do not establish stable
scores for the actual generated programs or live-GPU checkpoint recovery.

## Why admission failed

The exact saved R_future batch 25/sample 8, Mbpp/599, previously passed the first
34 of 88 extra tests before the suite's outer watchdog terminated it. The new
bounded diagnostic passed nine tests, then hit `TimeoutException` **inside the
candidate's loop on test 10**, with input `n=100000001`. Its unchanged per-test
allowance was **5.012398719787598 seconds**, derived from the frozen canonical
reference time 1.2530996799468994 seconds multiplied by 4. The child exited normally;
the new outcome was not an outer kill or an observed wrong numeric answer.

Because test 10 belonged to the previously passing prefix, recovery was rejected
as unknown. This concrete observation establishes a timeout-based inconsistency
between runs of the same saved candidate. It does **not** identify why timing
changed, prove the instrumentation has zero timing effect, establish a general
rate of score instability, or explain the older diagnostic failure on test 18.
Candidate correctness cannot be inferred from the unknown suite verdict.

The diagnostic has one metadata-label defect: the same test exception propagates
to the outer handler and its duplicate event is mislabeled as initialization
timeout. It is not a second failure or an initialization failure. Admission uses
the test event and prefix consistency, so that label did not cause rejection.
The original event record is retained unchanged. After shutdown, an offline
metadata-only correction distinguishes propagated test exceptions; two added
checks preserve admission decisions. All 113 local unit checks pass afterward.
That correction was not rerun on saved programs or Linux and does not pass
the failed scientific-admission gate.

The gate stopped on that first contradiction, as frozen. The other two R repeats,
three C repeats, 96-output regression and 32-W-sentinel regression **did not run**.
No favorable repeat was selected, no timeout was relabeled as reward 0/1, and no
per-test limit, task, oracle, label or old score was changed to force completion.
The full reward-comparability requirement therefore remains unpassed.

## Closeout and decision

This session produced **zero new model outputs, zero optimizer updates and zero
new checkpoints**. One saved candidate and five authored controls were executed
only for CPU diagnosis. All 21 compact files were collected and hash verified.
The old W_prefix/W_future final files and R_future25 checkpoint files were again
independently rehashed; old failures and all 9,296 saved model outputs remain intact.
No GPU or owned scoring workers remained. Normal provider OFF was verified by
11:48:23 UTC and the temporary fallback timer was cleared. The conservative
powered window was at most 7.38 minutes, a CNY 0.98 compute upper proxy at
7.98/hour, excluding storage and not an invoice; the 3-hour/CNY 23.94 cap was not extended.

Do not start another completion, extend doses, change evaluator allowances or
present this as a negative matched-control scientific result. The checkpoint
and raw-logprob improvements are source/unit-tested preparation; their new live
training integration remains untested because admission correctly blocked it.

For Thursday, discuss whether the supervision-upgrade checkpoint-retention
question justifies a redesigned measurement setup at all, given the missing
controls and limited current evidence. Any proposal to change timing semantics
must re-establish comparable training across **all** relevant arms and audit
novelty/cost first; it is not approved follow-up work. No replacement direction
has yet passed the same novelty and asset audit.

Evidence: [diagnostic records](DIAGNOSTIC_EVIDENCE.json), [closeout and checkpoint
inventories](CLOSEOUT.json), [frozen completion/repair design](../../experiments/q2_supervision_migration/COMPLETION_REPAIR_20260930.md).
