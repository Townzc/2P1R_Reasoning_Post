# October 1 engineering amendment: collect evidence before deciding

The owner reopened engineering work after review found an unnecessarily strong
passing-prefix gate and premature diagnostic exits. This amendment supersedes
the historical prefix-matching and first-item-exit rules below; it does not
change test inputs/oracles, individual test timers, reward formulas or the
scientific training/evaluation queue. Historical outputs remain immutable.

- Classify each current execution from its observed outcome and exception
  attribution. A saved outer-timeout prefix is not a known whole-suite PASS.
  Preserve prefix conflicts as metadata warnings. Killed, incomplete or
  unattributed executions remain UNKNOWN; they cannot produce reward zero.
- Run five authored controls, all 96 saved outputs, 32 known W sentinels and
  fixed three repeats of both failure fixtures. Collect per-item intent/result
  records despite isolated failures. The 1,200-second shared hard limit remains;
  the parent reports partial coverage if its worker is interrupted. No item is
  retried and no passing repetition is selected.
- `diagnostic_summary.json` records `diagnostics_completed` independently of
  `model_admitted`. A schema-2 `preflight_complete.json` is emitted only with
  full known-reward agreement, all unknown fixtures resolved consistently and
  exact coverage. The model parent requires both flags and an empty blocker
  list, bound to the same published source and reference identities.
- In live scoring, a complete UNKNOWN reply leaves the channel usable. Inspect
  the rest of that already generated batch before rejecting incomplete training
  rewards. Save request identity and raw reply before parsing. On transport or
  protocol failure, close the connection; never assign a late reply to the next
  sample. This does not implement automatic scorer restart or regenerate output.
- Periodic/confirmed-failure checkpoint preservation remains in place. Exact
  cross-process vLLM continuation is still unverified; old C100/R25 cannot be
  declared resumed merely because a partial checkpoint exists.

`timing_probe` independently crosses original/guarded scoring with direct and
fixture-first process histories, two fixed observations per combination. Every
cell starts a fresh interpreter; eight cells have a 210-second individual and
1,800-second total maximum, also bounded by an absolute deadline. A failed cell
is recorded and other predeclared cells may continue. The probe observes timer
boundaries, process CPU/wall times, signal state, CPU placement and visible
resource quotas. Its measurement wrapper changes the observation path: results
are diagnostic only, cannot admit training, and do not prove uninstrumented
reward equivalence. No-card mode's previously observed 0.5-CPU allocation is not
a substitute for the original host's timed scoring environment.

Local replay of five saved guard metadata records verifies the classification
change: three complete PASS records stay PASS; two attributable candidate FAILs
previously censored by the prefix rule are now FAIL with warnings. The three/two
outcome disagreement remains unresolved. This replay did not execute candidate
code or change any historical reward. The fixed Linux validation below is now complete; neither the local tests nor
this finite sample establishes universal runtime stability.

Any server diagnostic must preserve the original instance and fixed session
cost/deadline bounds; do not renew a closed budget or extend time silently. This
engineering amendment alone does not admit model training.

## Completed Linux validation, October 1

Execution source: `d347a3c8ab4360666925a810dbd58174d1fbb14b`.
160 authored checks passed locally and on the original Linux runtime, including
real fork, SIGALRM and killed-child timing-record preservation. The collect-all
preflight finished in 373.04 seconds with 140/140 items and no blockers:

| Check | Observed result |
|---|---|
| Previously known paired rewards | 90/90 unchanged |
| All old saved outputs | 96/96 resolved |
| Known W sentinels | 32/32 unchanged |
| Exact saved R599 failure | FAIL in all 3 fixed diagnoses; prefix warnings retained |
| Exact saved C260 failure | FAIL in all 3 fixed diagnoses |
| Authored controls and inventory | Passed |

The three R599 diagnoses agreed on binary FAIL but ended after 10, 14 and 7
observed tests, respectively. Binary agreement is not stable per-test timing.

The separate eight-cell timing probe finished in 167.74 seconds. Seven executions
hit an attributable per-test timeout near 5 seconds; measured CPU and wall time
were nearly equal. One original-scorer execution was cut off after 34 passing
tests at its approximately 62-second outer bound, with its next test incomplete.
There were no recorder failures. This supports the distinction between a current
attributable failure and outer censoring. It does not establish the cause of every
historical disagreement: previous PASS records remain, and the measurement wrapper
changes execution. Nothing was repeatedly run until a desired verdict appeared.

The machine summary's `reward_semantics_unchanged` means the configured test/oracle,
per-test limits and reward rule were retained and the finite known-score checks
matched. It is not proof that every timing-sensitive program has identical scores
across workers or days. The admission policy intentionally changed: historical
prefix agreement no longer overrides a current attributable outcome. The separate
timing probe cannot supply rewards or authorize model work.

All 430 compact artifacts were collected and hash-verified; all 37 files in the
three old checkpoint sets were independently rehashed. No owned CPU/GPU workers
remained. The same instance was normally shut down, provider OFF verified, and the
old fallback cleared only afterward. Zero training updates and zero model outputs
were added. See [compact closeout](../../reports/q2_engineering_repair_20261001/CLOSEOUT.json),
[regression summary](../../reports/q2_engineering_repair_20261001/DIAGNOSTIC_SUMMARY.json)
and [timing observations](../../reports/q2_engineering_repair_20261001/TIMING_PROBE_SUMMARY.json).

The next scientific step remains the already specified fresh C_prefix128,
C_future128 and R_future128 with their three evaluations, reusing old W. It is
not an exact resume of C100/R25. The prior 103–123 minute estimate does not fit
the remaining original October 1 window with collection reserve, so this CPU
repair did not start that queue or renew its budget. The new diagnostic gate
passed, but live-model completion and cross-process RNG recovery remain untested.
No conclusion about the hypothesis follows from this engineering success.

---

# Final finite control completion: frozen repair and admission

September30,2026. The owner explicitly authorized startup if necessary and a final
attempt to complete the missing controls, with normal shutdown afterward. If it
still cannot complete, pause Q2. This is a new bounded session, never an extension
of the closed four-hour window. The earlier conditional proposal is preserved.

## Question and queue

After base-only acceptance data become base+extra tests, should training retain
weak-history weights or restart from R? C uses strong supervision throughout to
control for the additional training history. Reuse completed W_prefix/W_future
and all old evaluations; no regeneration or new seed. Run fresh C_prefix128,
C_future128, R_future128, then eval_C_prefix, eval_C_future, eval_R_future. New
maximum384 optimizer updates,6144 training outputs and3072 evaluation outputs.
The fresh C/R starts are not exact resumes of failed C100/R25. Their old cost and
outputs remain in accounting; run/sample identities distinguish this attempt.

Scientific plan, dataset, reference cache, paired schedules, phase seeds, optimizer,
per-test allowances, first-failure rule, test order, tolerance and memory limits
remain frozen. New execution identity is controls_completion_1. No dose extension
will be used to find the desired result. W/R, W/C and C/R must be reported together.

## Scoring admission before any new model output

Original EvalPlus0.3.1 handles every known pass/fail. Only an outer unknown can
enter the new attributed guard. The guard clones the pinned evaluator, observes
exceptions after they occur, and keeps candidate tests/timers/oracles unchanged.
A bounded outer allowance can permit the original per-test contract to finish;
a kill, infrastructure error or unexplained contradiction remains unknown.
Every promoted result must preserve the already observed passing prefix. No line
tracing, new label, altered tolerance or replacement sampling backend is allowed.
The old suite-watchdog flag that failed its gate must remain disabled.

Linux CPU gate, maximum1200seconds: three repeats each of exact saved R599 and
C260 failures, all90 known pairs among the original96 outputs unchanged and all96
resolved, plus32 known W outputs on599/260 unchanged. R599 must preserve its
34 passing tests and produce the same attributable outcome across all repeats.
Any mismatch or unresolved verdict fails admission; do not select favorable
repeats. All diagnostic records remain separate from historical/scientific scores.
Finite regression evidence does not prove universal wall-clock equivalence.

## Recovery and receipts

Journal raw backend tokens and sampled logprobs before decoding or validation.
Validate alignment, finite values and policy/update lineage only after preserving
returns. Resolve CPU scoring in the same live callback; never call generation a
second time for that batch. Save every32 steps without pruning. Hash the actual
checkpoint file set against contiguous finite commit receipts and Trainer step;
retain a confirmed exception checkpoint when safe. Unknown optimizer commit,
trainer death or engine-state loss forbids automatic cross-process resume. The
saved vLLM RNG has not been verified, so a checkpoint alone is insufficient.

## Budget, stop and interpretation

Conservative startup through provider OFF is capped at10800seconds/three A800
hours/CNY23.94 at verified7.98/hour, excluding storage. Setup, tests, repairs,
collection and idle time count. Provider fallback is fixed at startup+10800;
model work ends no later than600seconds before it, each training phase2700seconds
and evaluation1800seconds subject to the shared deadline. No resetting the clock.

Ordinary repair may occur inside the same session, after evidence reconciliation
and source publication, with no replay or expanded dose. Gate failure, irrecoverable
state loss, incomplete queue at the hard limit, or user stop closes this attempt.
Collect compact artifacts/checkpoint inventories and verify them, normal provider
OFF promptly, verify OFF, retain all volumes/evidence. Never invoke a helper that
also empties Trash. If successful, analyze original matched contrasts using the
predeclared screen criteria; one paired training replicate is not seed evidence.
If unsuccessful, pause this direction rather than authorize another completion.
