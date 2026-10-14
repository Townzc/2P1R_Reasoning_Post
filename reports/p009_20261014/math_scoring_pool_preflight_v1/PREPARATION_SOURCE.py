"""Create-only code packet. No actual output scoring, model call or upload."""
import datetime
from pathlib import Path
import shutil
from experiments.sft_allocation_midpoint.common import read, dump, sha, manifest

root = Path('.local/p009_20261014/r1')
out = Path('reports/p009_20261014/math_scoring_pool_preflight_v1')
if out.exists():
    raise FileExistsError('Create-only packet; reconcile partial work, never repeat')
for name, expected in read('reports/p009_20261014/p0_runtime_preflight_v1/ADMISSION.json')['source_files'].items():
    if sha(name) != expected:
        raise ValueError('Active P0 source changed')
scalar = 'experiments/learning_regime_p009/math_scoring.py'
if sha(scalar) != 'd310d7e61b049cdd750f14c65f0ad12551ee45b7eeb0913646a6447a4cbc36fe':
    raise ValueError('Accepted scalar scorer changed')
log = root/'math_scoring_pool_checks_r1.log'
if 'Ran 8 tests' not in log.read_text() or '\nOK\n' not in log.read_text():
    raise ValueError('Missing actual new fixture result')
sources = [scalar, 'experiments/learning_regime_p009/math_scoring_pool.py',
           'experiments/learning_regime_p009/requirements_math.txt',
           'tests/test_p009_math_scoring_pool.py']
out.mkdir()
for name in sources:
    dest = out/'source'/name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(name, dest)
shutil.copyfile(log, out/log.name)
prior = Path('reports/p009_20261014/math_scorer_candidate_v1')
for name in ('DEPENDENCY_SOURCE_HASHES.json', 'MATH_VERIFY_INSTALL.json', 'math_verify_freeze_r1.txt'):
    shutil.copyfile(prior/name, out/name)
shutil.copyfile(__file__, out/'PREPARATION_SOURCE.py')
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
dump(out/'SOURCE_BUNDLE.json', dict(created_utc=now,
    scope='p009-math-scorer-persistent-pool-code', source_files={n: sha(n) for n in sources},
    candidate_scalar_commit='4c652b03f6e319c82abb095d03577af631fa2ddc',
    actual_P1_rows_scored=0, runtime_admitted=False, scientific_calls=0,
    active_P0_source_unchanged=True))
(out/'README.md').write_text('''# P009 bounded persistent MATH scoring pool — code review only

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
''')
(out/'REVIEW_REQUEST.md').write_text('''# Exact persistent scorer code review

Request `p009-math-scorer-persistent-pool-r1`.
Scope `p009-math-scorer-persistent-pool-code`.

Please bind the exact four source files and packet manifest, and review:

1. Unchanged scalar semantics and dependency versions; process main-thread
   alarms and parent timeout/kill; readiness cannot suspend an active deadline.
2. Exact-pair reuse including cached failures, no retry of original pairs,
   complete row identity/order/stop provenance, no correctness-based selection.
3. Technical startup/protocol/environment aborts, bounded cleanup, process cap.
4. Eight new synthetic fixtures; actual first-100 timing, durable driver,
   full fallback reporting and required adjudications remain unperformed.

This review blocks only use of the new local pool in future P1. It does not
block the original running P0, admit a teacher/student model, or replace P1's
actual-output audit. No external message is sent; request is in INDEX only.
''')
dump(out/'MANIFEST.json', manifest(out))
print(out, sha(out/'MANIFEST.json'))
