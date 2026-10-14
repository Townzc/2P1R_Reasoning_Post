# P009 bounded persistent MATH scoring pool — code review only

This addresses N1 in Claude's 20261014bc report. The existing accepted scalar
scorer is byte-identical. The new module only schedules local CPU work; it has
no model, GPU, network, training, source-data mutation or scoring-publication path.
Actual P1 and all later eligibility decisions remain unperformed and gated.

At most two spawned, long-lived Python processes import the pinned libraries
once and execute symbolic operations in their own main threads. The existing
two-second library alarms remain. The parent enforces an eight-second outer
response timer, kills and joins an unresponsive process, and records the original
pair's timeout. A replacement handles only future distinct pairs; it never
retries the failed pair. Worker readiness is bounded at 30 seconds and is never
waited for while another task's eight-second timer runs. Cleanup kills all
remaining session workers. There is no background controller or paid worker.

Deduplication keys are exact `(gold, extracted_answer)` strings, after the
existing last-box extractor's existing trim. No new algebraic or string
normalization determines cache identity. An identical pair shares one symbolic
attempt, including a timeout/tool failure. Every original row, its stop rule,
ID and symbolic-attempt provenance remain in input order. Duplicate row IDs
and unknown/incomplete stops fail closed. Caps and invalid special stops still
count as incorrect and need no symbolic task. Valid symbolic False cannot be
overridden; unparsed unequal boxes remain ineligible for the natural-wrong arm.
Dependency/startup/protocol failures abort technically, rather than becoming
model zeros. This is a session-local cache, not permission to rerun failed
scoring sessions or erase attempt/cost records.

Eight new orchestration fixtures passed once, including real pinned-library
worker comparisons, duplicate reuse, timeouts with later distinct work,
worker exit, environment mismatch, per-row stop handling and original
fallback semantics. Original eleven scalar checks were not repeated. These
are synthetic fixtures, not throughput observations on generated answers or
P1 acceptance. Original test log and exact source are included.

Before an actual complete pass, the concrete P1 driver must freeze its input
roster/source and record the first 100 original rows' full elapsed/startup
timing, attempt counts and unique-pair counts. Those same results are reused,
not rescored. A reviewed remaining-work forecast must use all observed timing
and actual remaining unique pairs; cache hits must not be presented as fresh
symbolic speed. That driver, forecast and durable score journal are not in
this code-only packet, and no actual rows have been scored here.

The full P1 freeze still requires all fallback counts per pool/endpoint,
fixed-hash adjudication of up to 25 fallback rows when more than 2% of boxed
answers use fallback, the required 50 string/symbolic disagreement review
(all if fewer), and counts of unbraced boxes and unsupported gold. This pool
does not change these requirements, any scientific sample, dose or budget.
