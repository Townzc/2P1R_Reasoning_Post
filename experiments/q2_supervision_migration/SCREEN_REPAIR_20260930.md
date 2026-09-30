# Scoring repair and completion of the same experiment

The owner explicitly corrected the shutdown policy: finish the complete experiment
before shutdown, and handle ordinary engineering faults in the same powered
session. The earlier automatic-shutdown-on-any-failure rule is superseded. Keep
the existing spend/time limits, retain failures and never replay uncertain work.

The first attempt at d33cbbfa committed five updates and saved96 outputs, all
accounted for. No final checkpoint was exported; those five updates cannot be
resumed from the stopped process. Their cost/dose remains separate from the
scientific comparison. No hypothesis was rejected by that engineering failure.

## Concrete repair

For each base/extra suite independently, use the pinned evaluator's fast_check=True:
a first failed test establishes failure of the conjunction, so stop that suite.
A PASS still requires all tests. Empty extra suites remain vacuous PASS. Unresolved
outer TIMEOUT/error remains unresolved; do not turn unknown status into zero.
The original full-suite mode stays supported for the original frozen plan. The
new plan explicitly selects first_failure_per_suite and has a distinct v2 run ID.

An authored control-flow probe of the exact cached upstream loop found identical
binary outcomes in four harmless cases (all pass, first failure, late failure,
candidate exception), with earlier stopping only for failed cases. OS/time guards
were substituted in that probe; it is not a Linux scoring or sandbox qualification.
47 authored CPU tests pass. Full Linux regression is required before training.

The isolated Linux CPU preflight scores exactly96 already saved outputs, generating
nothing and performing no updates. It reuses the hash-verified reference cache and
checks every saved input against its signed sample and original backend return.
All90 previously known base/extra pairs must agree and all96 new diagnostic pairs
must resolve. Parent-owned group cap:180seconds. Preserve old verdicts unchanged;
these post-run diagnostics are not scientific evaluation results. On failure,
inspect and repair the engineering issue while retaining the same instance and
remaining budget, rather than cycling GPU power.

## Same scientific experiment, bounded repair attempt

After the CPU gate passes, run the original five128-update phases and six fixed
128-task/eight-sample evaluations from the original model. Seeds, task schedules,
model, training recipe, metrics and practical screening criteria are unchanged.
No new arms or tuning against heldout outcomes. The repaired screen schedules
640 updates and16,384 completions. Including the failed attempt, the two attempts
would total645 committed update opportunities and16,480 generated outputs if the
new screen completes. Do not present the failed attempt as a second training seed.

The new parent has a maximum10,800 seconds (three hours), with the original phase
caps and at least600 seconds of collection/shutdown reserve. The normal provider
shutdown deadline remains September30 09:47UTC (02:47PDT), measured from the
original conservative05:47UTC start. This includes the downtime and therefore
keeps total powered cost below the original four-hour/CNY31.92 ceiling at7.98/hour,
excluding storage. Do not reset this deadline on restoring the same instance.
Require the whole remaining parent allowance plus reserve before admission;
latest admission06:37UTC. No new rental, GPU change, install or deletion.

Recoverable engineering failures stop owned model work for diagnosis; they do
not themselves mandate provider shutdown. Preserve and reconcile completed,
failed and uncertain work before any repair. Do not duplicate workers or invent
missing receipts. Complete all admitted training/evaluations, collect/verify and
then shut down. Stop sooner only at the agreed budget/time limit, an unsafe or
unrecoverable condition, or a user stop request. Do not broaden scientific scope.
