# Pairing-seed arithmetic exposure audit — 2026-09-09

**The frozen pair matches canonical structures at every update, but it does not
match every numerical property of the presented calculations.** This bounded CPU
audit reads only the seed17/seed23 frozen Paths/GCM training rows and schedules.
It uses no model outcomes, development results, holdout data, server access or GPU
work. The already fixed seed23 training plan is unchanged.

Timing clarification (recorded at 2026-09-09T06:01:53+00:00): this audit occurred during seed23
GPU training. The coordinating agent reported that training-loss logs already
existed, while seed23 development-evaluation outcomes had not yet been generated.
This audit did not read those training logs or any new model outputs. Its timing
label therefore means **before seed23 evaluation outcomes**, not before all
training output.


Global identity-operation exposure is almost equal between arms and is unchanged
by the new GCM assignment seed: Paths has 2780 such presentations and GCM 2800
in each seed. Nevertheless, their placement across updates and individual
problems changes. No selected training trace has a fractional intermediate in
either arm or seed, which sharply limits the arithmetic domain represented here.

## Definitions and independent checks

Every arm has 1024 frozen rows, each presented four times in its 1024-update
schedule: 4096 presentations and 16 exposures per problem. Statistics below
weight actual scheduled presentations, not just unique response strings. Each
four-number expression has three binary operations and two nonroot intermediate
results; the final target is excluded from the intermediate-value counts.

The identity definition is exactly the [existing structure audit's definition](pilot_v1_structure_bias_20260909/summary.json): multiplication with an evaluated
operand equal to one, division with denominator one, addition with an operand
zero, or subtraction with right operand zero. This includes numerical values
produced by subexpressions. It excludes `0 - x`, `1 / x`, multiplication by zero,
and `x / x` unless the evaluated denominator is one. These rules are an explicit
operational convention, not a complete taxonomy of algebraic equivalence.

A fractional intermediate has a reduced exact rational denominator other than
one. Negative, zero and one intermediates are counted separately. Ordered-tree
depth counts binary-operation levels on the longest input-to-root path; leaves
have depth zero. It is measured before any AC canonicalization. The measured
attributes do not define semantic strategies or model difficulty. These are
presentation/event counts; this audit does not attribute individual token losses
to the features or claim that their full joint distributions are matched.

An independent recursive walker uses the existing AST whitelist and `Fraction`;
it checks every expression, input multiset, target and canonical label, and
cross-checks identity events against the established implementation. A second
calculation parses the three displayed training equations directly, evaluates
them as rational numbers, and obtains depth from a separate AST traversal.
All 4096 stored rows across the two seeds and two arms agree with the reported
exposure totals. The schedules use every row exactly four times; ordered problem
identities and canonical-structure histograms agree between arms at all 1024
updates in both seeds.

All residual signs below are **GCM minus Paths**. The machine-readable
[companion JSON](pairing_seed_semantic_audit_20260909.json) retains histograms,
256 per-problem records, exact rational means, source hashes and the computation
hash. A fresh temporary-workspace rerun reproduced it byte for byte. No existing
source, dataset, config, metric or run artifact was changed.

## Global scheduled exposure

Paths' full feature histograms are identical across seeds. Its four selected
paths for every problem are also identical; the assignment/order seed does not
change the globally presented Paths support.

| Attribute, summed over 4096 presentations | Paths seed17 | GCM seed17 | Paths seed23 | GCM seed23 |
|---|---:|---:|---:|---:|
| Presentations containing an identity operation | 2780 | 2800 | 2780 | 2800 |
| Total identity-operation occurrences | 2780 | 2800 | 2780 | 2800 |
| Presentations with a fractional intermediate | 0 | 0 | 0 | 0 |
| Fractional intermediate occurrences | 0 | 0 | 0 | 0 |
| Presentations with a negative intermediate | 576 | 576 | 576 | 576 |
| Negative intermediate occurrences | 832 | 832 | 832 | 832 |
| Zero intermediate occurrences | 508 | 528 | 508 | 528 |
| One intermediate occurrences | 956 | 960 | 956 | 928 |
| Depth-2 presentations | 752 | 752 | 752 | 752 |
| Depth-3 presentations | 3344 | 3344 | 3344 | 3344 |

Here, each selected path contains at most one identity operation, so its
presentation count equals its identity-operation count. The identity exposure
rates are 67.87% for Paths and 68.36% for GCM: a +20/4096, or approximately
+0.49 percentage-point, GCM residual in both seeds. This near balance does not
establish semantic equality.

The only changed GCM **global** feature total among these attributes is the
number of intermediate ones: 960 to 928, a change of -32 occurrences. Relative
to Paths' fixed 956, the residual shifts from +4 to -28. Other attributes and
joint relationships not measured here may also change. No fractional
intermediate in the frozen selection does not mean that these problems have no
fractional-intermediate solutions outside their selected paths.

## Residuals at the optimizer-update level

Each entry counts updates with a nonzero difference between the four
presentations of the two arms. These compare corresponding frozen updates
**within** a seed; seed17 and seed23 update numbers do not identify the same
problem block after reshuffling.

| Attribute | Nonzero updates, seed17 / 1024 | Nonzero updates, seed23 / 1024 | Largest absolute count residual per update |
|---|---:|---:|---:|
| Identity-containing presentations / identity operations | 44 | 28 | 1 |
| Fraction-containing presentations / fractional intermediate nodes | 0 | 0 | 0 |
| Negative-containing presentations / negative intermediate nodes | 0 | 0 | 0 |
| Zero intermediate nodes | 44 | 28 | 1 |
| One intermediate nodes | 44 | 28 | 1 |
| Ordered-tree depth sum | 0 | 0 | 0 |
| Any audited attribute differs | 72 | 48 | — |

For identity operations, seed17 has 32 positive and 12 negative update residuals;
seed23 has 24 positive and 4 negative residuals. Both sum to +20. Intermediate
ones have 24 positive and 20 negative residuals in seed17, versus 28 negative
and no positive residuals in seed23. Thus equality of total exposure for some
attributes does not establish identical optimization-time presentation.

Depth and negative-intermediate exposure happen to match at every update in this
selection. That is an observed property of these data, not a general implication
of canonical operator-tree matching. Conversely, the nonzero numerical residuals
do not invalidate the separately verified canonical matching claim.

## Residuals for individual problems

For each problem, Paths presents each of its four selected paths four times;
GCM presents its one assigned path 16 times. The companion JSON stores each
problem's 16-exposure feature sums and GCM-minus-Paths differences.

| Attribute | Problems with a nonzero arm residual in seed17 / 256 | In seed23 / 256 | Problems whose GCM attribute changes between seeds / 256 |
|---|---:|---:|---:|
| Identity-operation count | 41 | 41 | 12 |
| Fractional intermediate count | 0 | 0 | 0 |
| Negative intermediate count | 64 | 64 | 24 |
| Zero intermediate count | 56 | 56 | 24 |
| One intermediate count | 56 | 56 | 22 |
| Ordered-tree depth sum | 124 | 124 | 56 |
| Any audited feature | 180 | 180 | 99 |

GCM changes its assigned path on **196/256** problems; 99/256 change at least
one of these audited attributes. The same count of affected problems across
seeds need not mean the same problems are affected. For identity operations,
both seeds have 32 problems with +4 exposures relative to Paths and 9 problems
with -12 exposures. Twelve problems switch their identity status between seeds,
while the global imbalance remains +20.

Three concrete frozen-training examples make the distinction clear:

- Problem `09a9ed4f49539ce59c7b`, numbers 9, 11, 19, 28, target 11: seed17 GCM
  uses `11 - (19 - (28 - 9))`, ending with subtraction of zero. Seed23 uses
  `9 + (19 - (28 - 11))`, with no identity operation under the declared rule.
  Paths supplies 12 identity exposures out of 16 for this problem; GCM supplies
  16 in seed17 and zero in seed23.
- Problem `0af429f1d3ac2df9c512`, numbers 2, 12, 24, 28, target 32: seed17 uses
  `12 + ((2 * 24) - 28)` with no negative intermediate. Seed23 uses
  `12 - (28 - (2 * 24))`, with intermediate -20. Global negative exposure is
  unchanged because other assignments compensate.
- Problem `0873e8cb5caabec412a3`, numbers 24, 25, 26, 27, target 53: seed17 uses
  `(26 + 27) / (25 - 24)`, depth 2. Seed23 uses
  `27 + (26 / (25 - 24))`, depth 3. Paths' mean depth for this problem is 2.5;
  both GCM assignments still participate in globally matched depth histograms.

## Identification scope and the next control

This pair estimates a conditional contrast between the **specified
path-allocation procedures on this frozen pool and pairing seed**, under matched
canonical structure exposure, problem presentations, update count and supervised-
token budget. It does not isolate an effect of abstract semantic
strategy diversity after holding every numbers-dependent feature fixed. Seed23
also jointly changes assignment, order and training RNG as already declared;
this audit does not separate their contributions.

The numerical exposure differences can be consequences or components of the
allocation treatment itself. Calling all of them confounders would impose an
unsupported causal model. Conversely, a correlation with an eventual outcome
would not prove that identity operations, negative intermediates or depth caused
it. Adjusting for or matching these attributes after seeing outcomes can change
the estimand or condition on treatment-induced quantities. No such adjustment
or training change is made here, and this audit supplies no mechanism proof.

For a later mechanism-focused study, first state which path property should be
manipulated and which exposure properties should be held fixed. Then construct
shared-support controls for numerical identity events, intermediate-value
profiles and depth at the appropriate global/update/problem level, or report the
remaining residuals before training. Requiring equality of each problem's entire
path-property distribution may remove part of the within-problem-versus-single-
path treatment; if so, the target estimand must be revised explicitly rather
than hiding the conflict. A neutral-rewrite control and nontrivial-computation
control need a feasibility audit, preserved difficulty/selection diagnostics and
a new reviewed protocol.

The absence of fractional intermediate training is a domain boundary to test in
that later construction, not a reason to modify the active seed23 replication.
The current fixed primary metric, data and two-arm dose remain unchanged; both
favorable and unfavorable outcomes must be interpreted within this scope.

## Reproducible bounded computation

The following is the exact computation used for the companion JSON. It refuses
to overwrite an existing result. For a reproduction, save this block as a Python
file and run it in a temporary workspace that links this repository's `src`,
`scripts` and `runs` directories and has an empty `reports` directory. The original
computation SHA-256 is recorded in the JSON; copying the block with different
line endings changes that code hash but not the analytical definitions. It reads
only six frozen training/schedule files and the two arithmetic helper source
files shown in `source_sha256`.

```python
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib, json
from pathlib import Path
from src.countdown_smoke import safe_parse, canonical, verify_expression
from scripts.audit_pilot_structure_bias import identity_operations

DATA = {17: Path('runs/pilot_v1_20260908_r3'),
        23: Path('runs/pilot_replication_seed23_20260909_r1')}
FEATURES = ('has_identity', 'identity_operations', 'has_fraction_intermediate',
            'fraction_intermediate_nodes', 'has_negative_intermediate',
            'negative_intermediate_nodes', 'zero_intermediate_nodes',
            'one_intermediate_nodes', 'ordered_tree_depth')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def feature(row):
    tree = safe_parse(row['expression'])
    assert verify_expression(row['expression'], row['numbers'], row['target'])
    assert canonical(tree) == row['path_id']
    assert canonical(tree, structure_only=True) == row['structure_id']
    intermediate, identities = [], []
    def walk(t, address=''):
        if t[0] == 'n': return Fraction(t[1]), 0
        op, left, right = t
        a, da = walk(left, address+'L')
        b, db = walk(right, address+'R')
        if op == '+': v, neutral = a+b, a == 0 or b == 0
        elif op == '-': v, neutral = a-b, b == 0
        elif op == '*': v, neutral = a*b, a == 1 or b == 1
        elif op == '/': v, neutral = a/b, b == 1
        else: raise ValueError(op)
        if address: intermediate.append(v)
        if neutral: identities.append((address or 'root', op, str(a), str(b)))
        return v, max(da, db)+1
    value, depth = walk(tree)
    known_value, known_events = identity_operations(tree)
    assert value == row['target'] == known_value
    assert identities == [(x['node_address'], x['operator'], x['left_value'], x['right_value']) for x in known_events]
    assert len(intermediate) == 2
    fractions = sum(v.denominator != 1 for v in intermediate)
    negatives = sum(v < 0 for v in intermediate)
    return dict(zip(FEATURES, (int(bool(identities)), len(identities), int(bool(fractions)),
                              fractions, int(bool(negatives)), negatives,
                              sum(v == 0 for v in intermediate), sum(v == 1 for v in intermediate), depth)))

def residual(a, b):
    # Every sign is GCM minus Paths.
    delta = [y-x for x,y in zip(a,b)]
    return {'gcm_minus_paths_total': sum(delta), 'nonzero_count': sum(x != 0 for x in delta),
            'positive_count': sum(x > 0 for x in delta), 'negative_count': sum(x < 0 for x in delta),
            'maximum_absolute': max(map(abs,delta)), 'absolute_sum': sum(map(abs,delta)),
            'mean_absolute': str(Fraction(sum(map(abs,delta)), len(delta))),
            'histogram': {str(k): v for k,v in sorted(Counter(delta).items())}}

sources, paths_by_pid, schedules, all_rows, all_features = {}, {}, {}, {}, {}
for seed, root in DATA.items():
    schedule_path = root/f'schedule_seed{seed}.json'
    sources[str(schedule_path)] = sha(schedule_path)
    schedules[seed] = json.loads(schedule_path.read_text())
    assert len(schedules[seed]) == 1024 and all(len(x) == 4 for x in schedules[seed])
    all_rows[seed], all_features[seed] = {}, {}
    for arm in ('paths', 'gcm'):
        path = root/f'train_{arm}.jsonl'
        sources[str(path)] = sha(path)
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        assert len(rows) == 1024
        exposure = Counter(i for update in schedules[seed] for i in update)
        assert exposure == Counter({i:4 for i in range(1024)})
        all_rows[seed][arm] = rows
        all_features[seed][arm] = [feature(row) for row in rows]
        per_pid = defaultdict(list)
        for row in rows: per_pid[row['problem_id']].append(row)
        assert len(per_pid) == 256 and all(len(x) == 4 for x in per_pid.values())
        paths_by_pid[seed, arm] = per_pid
    for update in schedules[seed]:
        assert Counter(all_rows[seed]['paths'][i]['structure_id'] for i in update) == Counter(all_rows[seed]['gcm'][i]['structure_id'] for i in update)
        assert [all_rows[seed]['paths'][i]['problem_id'] for i in update] == [all_rows[seed]['gcm'][i]['problem_id'] for i in update]

summary = {'status': 'CPU_TRAINING_EXPOSURE_AUDIT_BEFORE_SEED23_EVALUATION_OUTCOMES',
           'created_utc': '2026-09-09T06:01:53+00:00',
           'audit_timing': 'Conducted during seed23 training. The coordinating agent reported that development evaluation outcomes had not yet been generated. This audit read no new model outputs or training logs.',
           'sign_convention': 'All residuals are GCM minus Paths.', 'seeds': {}, 'source_sha256': sources}
for seed in DATA:
    result = {'optimizer_updates':1024, 'presentations_per_arm':4096,
              'per_update_canonical_structure_histograms_equal': True,
              'same_ordered_problem_ids_at_every_update':True,
              'global':{}, 'per_update_residual':{}, 'per_problem_residual':{}}
    global_values, updates, problems = {}, {}, {}
    for arm in ('paths','gcm'):
        feats, rows, schedule = all_features[seed][arm], all_rows[seed][arm], schedules[seed]
        flattened = [feats[i] for update in schedule for i in update]
        global_values[arm] = {k:[f[k] for f in flattened] for k in FEATURES}
        updates[arm] = {k:[sum(feats[i][k] for i in update) for update in schedule] for k in FEATURES}
        per_pid = defaultdict(Counter)
        for update in schedule:
            for i in update: per_pid[rows[i]['problem_id']].update(feats[i])
        problems[arm] = per_pid
        result['global'][arm] = {k:{'sum':sum(v), 'mean':str(Fraction(sum(v),len(v))),
                                   'histogram':{str(x):n for x,n in sorted(Counter(v).items())}}
                                 for k,v in global_values[arm].items()}
    pids = sorted(problems['paths'])
    for k in FEATURES:
        result['per_update_residual'][k] = residual(updates['paths'][k], updates['gcm'][k])
        result['per_problem_residual'][k] = residual([problems['paths'][pid][k] for pid in pids],
                                                    [problems['gcm'][pid][k] for pid in pids])
    result['updates_with_any_audited_attribute_residual'] = sum(any(updates['paths'][k][i] != updates['gcm'][k][i] for k in FEATURES) for i in range(1024))
    result['problems_with_any_audited_attribute_residual'] = sum(any(problems['paths'][pid][k] != problems['gcm'][pid][k] for k in FEATURES) for pid in pids)
    summary['seeds'][str(seed)] = result

per_problem = []
for pid in sorted(paths_by_pid[17,'paths']):
    p17, p23 = paths_by_pid[17,'paths'][pid], paths_by_pid[23,'paths'][pid]
    assert {x['path_id'] for x in p17} == {x['path_id'] for x in p23}
    assert len({x['path_id'] for x in p17}) == 4
    a = p17[0]
    row = {'problem_id':pid,'block_id':a['block_id'],'numbers':a['numbers'],'target':a['target'], 'gcm':{}}
    base = {k:sum(feature(r)[k] for r in p17)*4 for k in FEATURES}
    row['paths_exposure_feature_sums'] = base
    for seed in DATA:
        g = paths_by_pid[seed,'gcm'][pid]
        assert len({x['path_id'] for x in g}) == 1
        f = feature(g[0])
        row['gcm'][str(seed)] = {'path_id':g[0]['path_id'],
                               'gcm_minus_paths_feature_sums':{k:f[k]*16-base[k] for k in FEATURES}}
    row['gcm_assigned_path_changed'] = row['gcm']['17']['path_id'] != row['gcm']['23']['path_id']
    row['gcm_audited_features_changed'] = row['gcm']['17']['gcm_minus_paths_feature_sums'] != row['gcm']['23']['gcm_minus_paths_feature_sums']
    per_problem.append(row)
summary['cross_seed'] = {
    'paths_per_problem_path_sets_unchanged':True,
    'paths_global_audited_feature_histograms_unchanged': summary['seeds']['17']['global']['paths'] == summary['seeds']['23']['global']['paths'],
    'gcm_assigned_path_changed_problems':sum(r['gcm_assigned_path_changed'] for r in per_problem),
    'gcm_audited_features_changed_problems':sum(r['gcm_audited_features_changed'] for r in per_problem),
    'gcm_feature_changes_per_problem':{k:sum(r['gcm']['17']['gcm_minus_paths_feature_sums'][k] != r['gcm']['23']['gcm_minus_paths_feature_sums'][k] for r in per_problem) for k in FEATURES},
    'gcm_global_feature_sum_seed23_minus_seed17':{k:summary['seeds']['23']['global']['gcm'][k]['sum']-summary['seeds']['17']['global']['gcm'][k]['sum'] for k in FEATURES},
}
summary['per_problem'] = per_problem
for path in ('src/countdown_smoke.py','scripts/audit_pilot_structure_bias.py'):
    sources[path]=sha(Path(path))
summary['audit_computation_sha256']=sha(Path(__file__))
out=Path('reports/pairing_seed_semantic_audit_20260909.json')
with out.open('x') as stream:stream.write(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='per_problem'},indent=2))
```
