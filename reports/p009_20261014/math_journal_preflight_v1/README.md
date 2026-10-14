# P1 durable scoring journal — code candidate only

This adds a create-only local journal around the previously reviewed, unchanged
scalar MATH scorer and two-process SymbolicPool. It has scored no actual teacher
row and performed no actual math-verify operation. Eleven new tests use a fake
pool only. The pinned math-verify/scalar rules, two workers, eight-second outer
timeout and valid-False semantics do not change. No model, GPU, cloud request or
training is performed by this helper.

The original ordered rows and caller-supplied future source/input binding are
frozen once. An exclusive local lock prevents concurrent scoring. Before each
chunk of at most100 original rows, a durable intent lists every prospective new
answer pair. Completed chunks and symbolic observations are fsynced create-only.
A normal later session may read a fully committed cache, including failures,
and proceed only to previously unscored rows. It never rescores an old pair.
A caught error preserves confirmed pairs and unconfirmed pair intents. An abrupt
loss may leave additional unconfirmed pairs; any incomplete chunk or torn file
blocks all continuation. This code does not reconcile or retry unknown work.
It deliberately cannot claim that every predeclared pair was actually attempted.

The first chunk must contain the first100 actual ordered rows (or all if fewer).
The rest requires a real exact first100 timing review binding the same input
basis and result bytes. Its serial scenario uses the slowest observed new pair,
remaining distinct pairs,20% margin and an uncalibrated300-second allowance;
it assumes no two-worker speedup. Startup observations are separately retained.
The measured chunk interval includes the committed outcome proof but excludes
the last tiny timing-record write, explicitly disclosed. Neither the scenario
nor the current code package admits a real run or guarantees future CPU speed.

A complete-pool report retains all labels and draws fixed-hash up-to50 symbolic/
string disagreements, plus up-to25 fallback rows when fallback exceeds2% of
boxed responses. All adjudications remain null until independent inspection.
Outer timeouts exceeding0.5% of unique pairs are flagged before eligibility.
Gold must be structurally present; semantic parse failures stay visible under
the original fallback rules. Unbraced boxes are counted. No labels, cohort,
selection, cost or scientific gate are repaired by this helper.

This package is not a runnable actual-P1 admission. The future original teacher
rows/provenance, exact driver, first100 measured timing/full-pass admission,
independent sample adjudications and real A2 must still be bound and reviewed.
It does not block the separate P0 entry repair. New tests can be read or run as
`PYTHONPATH=.:tests python -m unittest test_p009_math_scoring_journal -v`.
