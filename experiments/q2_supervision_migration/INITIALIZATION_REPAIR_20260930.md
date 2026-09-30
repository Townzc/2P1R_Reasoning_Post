# Candidate initialization timeout repair

The repaired screen completed W_prefix (128 updates, 2,048 outputs; final model
independently hash verified). C_prefix stopped after 100 committed updates, with
the next 16 outputs saved. Its batch100 sample2 has a top-level self-test that
does not terminate: the base evaluator reports TIMEOUT before any test, while
extra reports FAIL. No C policy/optimizer checkpoint was saved. This lost
recoverability is an implementation mistake, not a scientific finding.

The normal provider remains powered for repair, following the owner's explicit
completion-first instruction. Original shared worker deadline09:24:41UTC and
provider09:47UTC/CNY31.92 ceiling are unchanged. Do not restart any model phase
merely because this repair source exists; completed or ambiguous work cannot be
replayed under the currently frozen dose. Repeating C requires a separate explicit
decision about its100 already committed updates. W_prefix must be reused.

The opt-in repair never re-executes a known PASS or FAIL. For an unresolved TIMEOUT
only, diagnose the same saved candidate with the pinned upstream evaluator and an
additional timer around its exec(code) initialization. The timer uses the existing
nominal task allowance min(60,sum(per-test limits))+1 seconds. The original
watchdog additionally has one second of process/cleanup reserve. All oracles,
per-test guards and candidate code are retained. Only an observed initialization
TimeoutException, upstream FAIL, and a normal diagnostic-child exit establishes
candidate failure. Other outcomes remain unknown. The original TIMEOUT remains
in the new diagnostic detail; old ledgers are never changed.

Such CPU diagnosis is not a new rollout or optimizer update. A bounded45-second
Linux preflight exercises the exact saved timeout and two authored negative
controls; it must pass before repaired model work.49 authored CPU checks pass.
The original per-request120-second limit can be too short for two original suite
watchdogs plus two diagnostic watchdogs. Opt-in workers record a300-second request
cap while retaining all original phase and absolute deadlines.

Opt-in training also saves complete Trainer checkpoints every32 updates without
deleting old checkpoints, and attempts a checkpoint on an ordinary exception at
a confirmed committed step. This preserves evidence but does not claim exact
vLLM RNG resume or permission to replay an in-flight batch. Scientific models,
task split, schedules, sampling seeds, update count per phase and reward truth
table remain unchanged. The completed W model and failed C evidence are retained.
