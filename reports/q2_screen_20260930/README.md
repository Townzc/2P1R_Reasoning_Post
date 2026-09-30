# Latest: available-state evaluations running; full comparison incomplete

At September30 08:31UTC, the repaired evaluation engine had produced128 signed,
independently verified outputs. The queue contains only the three originally
planned available states: R, W_prefix and W_future,1024 outputs each. The first
startup failed before any generation; the environment repair discovered the
already installed build tools. No model/backend/seed was changed.57 authored CPU
checks passed locally and on Linux. [Milestone receipt](AVAILABLE_EVALUATIONS_MILESTONE.json).

Both W phases completed128 updates/2048 outputs each. R_future subsequently
failed after25 updates/416 outputs; its15-file exception checkpoint is verified,
but missing sampled probabilities and unverified sampler RNG recovery prevent an
exact continuation. C_prefix remains failed at100 updates/1616 outputs without
weights. Including the first5-update/96-output failure, actual training dose is
386 committed updates and6224 saved outputs. All failed records are retained.

The attempted suite-watchdog diagnostic disagreed with previously passing tests
and is **not enabled**. Remaining evaluations retain unresolved suite scores as
unknown. W/R, W/C and C/R matched-future contrasts are all unavailable; descriptive
scores of the three existing states cannot replace these controls. This is not a
completed scientific screen or evidence for/against its hypothesis. No automatic
C/R training replay is authorized. Original deadlines and compute cap remain.

Earlier dated entries below are historical.

# Latest: W training complete, R training running; evaluation pending

At September30 08:00UTC, W_prefix and W_future have each completed128 updates
and2,048 training outputs. All W_future batch ledgers and update receipts were
independently reconciled; its11 final export files match their manifest, and its
15-file terminal Trainer checkpoint contains identical model weights.3,213
compact W_future evidence files were retrieved and individually hash verified.
This is a training milestone, not evidence of efficacy. R_future is running;
no heldout evaluation has completed. See [milestone receipt](W_FUTURE_MILESTONE.json).

Preserved failures: first attempt5updates/96outputs; C_prefix100updates/1,616
outputs without a recoverable policy checkpoint. The initialization-scoring
repair passed its saved-candidate CPU gate; original unknowns remain unchanged.
Only untouched W/R phases are continuing, using execution source d27c6fb9.
Repeating C needs the pending owner dose decision; C comparisons remain missing.
The original09:24:41UTC worker /09:47UTC provider deadlines and cost cap stand.
All earlier snapshots below are historical.

# Latest: first attempt retained; scoring repair prepared

The first attempt stopped after five updates and96 saved training outputs, before
any scientific comparison. The owner requested completing the full experiment
before shutting down and fixing routine faults within the same powered session.
A bounded CPU regression on all96 saved outputs will precede the repaired screen.
No extra scientific arm or seed is introduced; the original failed attempt stays
in the accounting. See [first attempt](FIRST_ATTEMPT.md) and
[repair amendment](../../experiments/q2_supervision_migration/SCREEN_REPAIR_20260930.md).

The preparation snapshot below is historical.

# Q2 short scientific screen — prepared, not executed

September30 UTC. The owner requested continued experiments and a concrete
proposal before Thursday. The earlier two-update engineering test passed.
The new finite W/C/R screen is implemented and CPU-checked; the server is still
OFF and no new model or benchmark program ran during preparation.

| Comparison | What it addresses |
| --- | --- |
| W_future − R_future | Future value of retaining base-test-trained weights |
| W_future − C_future | Dependence on prior supervision, at matched historical update dose |
| C_future − R_future | General effect of additional training under the stronger tests |

The frozen queue has two128-update prefixes, three128-update continuations and
six1024-completion evaluations:640 updates,10,240 training completions and6,144
evaluation completions. Each phase covers all250 TRAIN tasks; evaluation uses
the existing128-task split. No new benchmark or annotation is created.

Expected2–3 hours on oneA800 is a rough extrapolation from the small engineering
profile; full-distribution and standalone-evaluation throughput remain unmeasured.
The hard powered cap is4 hours, with a shared13,200-second worker limit and
normal provider timer. At the previously verified7.98CNY/hour, the compute cap
is31.92CNY excludingstorage, subject to live verification. Startup remains with
the owner. No new rental, installation or automatic retry is queued.

Forty-five authored CPU checks passed, including 19 new screen checks. They cover
planning, score-status handling, backend-to-scoring output identity, incomplete
update accounting and finite orchestration. They do not verify full GPU execution. The original
engineering runtime is retained unchanged. No old result or failure was removed.

A3-point W_future deficit to both alternatives, alongside C_future no more than
1point below R_future, is a predeclared **pilot priority pattern**, not proof of
noninferiority or scientific novelty. Weak or imprecise evidence can justify
project deprioritization without scientific falsification. Backup review found
no admitted alternative; do not automatically start a different training project.

[Full protocol](../../experiments/q2_supervision_migration/SCREEN_PROTOCOL_20260930.md),
[frozen plan](../../experiments/q2_supervision_migration/assets/screen_t128_k128.json),
[preparation receipt](PREPARATION.json).
