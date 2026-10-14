"""Publish one code-only P1 journal candidate; no actual scoring or cloud work."""
from pathlib import Path
from datetime import datetime,timezone
import ast,json,shutil
from experiments.sft_allocation_midpoint.common import read,dump,sha,manifest,verify
r=Path('.local/p009_20261014/r1'); pub=Path('reports/p009_20261014/math_journal_preflight_v1')
if pub.exists():raise FileExistsError('Create only; preserve partials')
prior=read('reports/p009_20261014/review_3ce168ad_accepted_v1/ACCEPTED.json')
for path,want in prior['source_files'].items():
 if sha(path)!=want:raise ValueError('Accepted scalar/pool source changed')
log=r/'math_journal_new_checks_r1.log'
if 'Ran 11 tests' not in log.read_text() or not log.read_text().rstrip().endswith('OK'):
 raise ValueError('Missing new journal tests')
sources={p:sha(p) for p in [
 'experiments/learning_regime_p009/math_scoring.py',
 'experiments/learning_regime_p009/math_scoring_pool.py',
 'experiments/learning_regime_p009/math_scoring_journal.py',
 'experiments/learning_regime_p009/requirements_math.txt',
 'tests/test_p009_math_scoring_journal.py']}
for p in sources:
 if p.endswith('.py'):ast.parse(Path(p).read_text())
pub.mkdir(parents=True)
for p in sources:
 dest=pub/'source'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
shutil.copyfile(log,pub/'NEW_FIXTURES.log');shutil.copyfile(__file__,pub/'PREPARATION_SOURCE.py')
dump(pub/'SOURCE_BINDING.json',dict(scope='p009-math-p1-durable-journal-code',source_files=sources,
 actual_generated_rows_scored=0,actual_math_verify_calls=0,actual_gpu_calls=0,
 prior_scalar_and_pool_unchanged=True,prior_pool_review_commit='3ce168ade44c2fee2ad4c8bd6d28e641de494b9f',
 actual_input_binding_missing=True,actual_P1_NOT_RUN=True,eligibility_admitted=False))
(pub/'README.md').write_text('''# P1 durable scoring journal — code candidate only

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
''')
(pub/'REVIEW_REQUEST.md').write_text('''# Code-only durable P1 journal review

Request p009-math-p1-durable-journal-r1, scope p009-math-p1-durable-journal-code.
Review exact SOURCE_BINDING/source bytes, create-only partial failure behavior,
normal committed-cache restoration, lock and first100/review boundary. Confirm
old scalar/pool bytes and labels are untouched. Inspect fixed sampling and
technical unknown accounting; fake tests are not actual symbolic speed or P1.
Return scoped decision, target and exact source_files. This review admits no
real corpus or student selection, and does not block P0 entry repair.
''')
dump(pub/'MANIFEST.json',manifest(pub));verify(pub,read(pub/'MANIFEST.json'))
dump(r/'MATH_JOURNAL_PREPARED.json',dict(utc=datetime.now(timezone.utc).isoformat(),packet=str(pub),
 source_files=sources,tests=11,actual_scoring=False,builder_done=True))
print('Created code-only P1 journal packet; actual scoring remains NOTRUN.')
