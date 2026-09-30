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
