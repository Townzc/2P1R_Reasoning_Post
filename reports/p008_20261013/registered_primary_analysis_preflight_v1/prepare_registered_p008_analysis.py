"""PREPARED: all-cell primary contrasts under protocol section 8, once complete.

No model execution, output rescoring, checkpoint loading, or runtime gate writes.
Requires all 18 successful logical students and base, including replacement
lineage. Shared paired-question percentile bootstrap: 10,000 / seed20261013.
"""
from pathlib import Path
import datetime, json
import numpy as np
from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest
from experiments.sft_allocation_p008.student_replacement_binding import MAPPING
from scripts.p008_paired_question_analysis import paired_percentile

r = Path(__file__).resolve().parent
s = r / 'student_completion_r1'
replacement = r / 'student_lr_replacements_r1'
preparation = r / 'student_preparation_r1'
out = r / 'registered_analysis_r1'
assert not out.exists(), 'Existing analysis attempt; preserve and reconcile, never silently replace'
logical_to_physical = {logical: physical for physical, logical in MAPPING.items()}
configs = sorted((read(p) for p in preparation.glob('*.json') if p.name != 'PREPARATION_SOURCE.json'),
                 key=lambda x: x.get('run_id', ''))
configs = [x for x in configs if x.get('run_id') in read(s / 'plan.json')['slots'] and x.get('role') in ('main', 'bridge', 'base')]
assert len(configs) == 19 and len({x['run_id'] for x in configs}) == 19
assert sum(x['role'] == 'main' for x in configs) == 16
assert sum(x['role'] == 'bridge' for x in configs) == 2
assert sum(x['role'] == 'base' for x in configs) == 1
ids = ['gsm8k/test/%05d' % i for i in range(1319)]
rows, vectors, evidence = [], [], []
for cfg in configs:
    logical = cfg['run_id']
    physical = logical_to_physical.get(logical, logical)
    queue = replacement if logical in logical_to_physical else s
    root = queue / 'exports' / physical / 'evidence'
    oracle = read(root / 'LOCAL_ORACLE_AUDIT.json')
    env = read(queue / 'runs' / physical / 'result.json')
    provider = read(queue / 'closeouts' / physical / 'provider.json')
    assert oracle['passed'] is True and oracle['run_id'] == physical
    assert oracle['outputs_rescored'] == 1319
    assert oracle['updates_verified'] == cfg['updates'] and oracle['targets_verified'] == cfg['targets']
    assert env['receipt']['status'] == 'completed' and env['receipt']['run_id'] == physical
    assert digest(env['artifact_manifest']) == env['receipt']['evidence_sha256'] == oracle['artifact_digest']
    assert provider['apps'] and not provider['owned_containers'] and all(x['state'] == 'stopped' for x in provider['apps'])
    summary_path = root / 'endpoint1319/summary.json'
    summary = read(summary_path)
    assert sha(summary_path) == env['artifact_manifest']['endpoint1319/summary.json']['sha256']
    q = summary['question_correct']
    assert sorted(q) == ids and all(type(q[i]) is bool for i in ids)
    assert sum(q.values()) == summary['correct'] == oracle['correct']
    assert summary['n'] == 1319 and env['result']['endpoint'] == summary
    if logical in logical_to_physical:
        assert oracle['logical_run_id'] == logical and oracle['parent_status'] == 'failed'
        assert oracle['outcome_blind_zero_update_replacement'] is True
    if cfg.get('training_multiple') == 8:
        assert oracle['effective_worker_seconds'] == 9600
        assert oracle['original_N2_passed'] is False and oracle['post_hoc_engineering_deviation'] is True
    record = dict(logical_run_id=logical, physical_run_id=physical, role=cfg['role'],
                  correct=oracle['correct'], n=1319, accuracy=oracle['correct']/1319,
                  length_caps=oracle['endpoint_stop_diagnostics']['length_cap_outputs'],
                  parsed=summary['parsed'], updates=cfg['updates'], targets=cfg['targets'],
                  technical_unknowns=0, provider_released=True)
    for name in ('draw', 'budget_multiple', 'training_multiple', 'price', 'policy', 'seed'):
        if name in cfg: record[name] = cfg[name]
    if cfg['role'] != 'base':
        plan_path = preparation / 'inputs' / cfg['plan_file']
        plan = read(plan_path)
        for name in ('acquired_answers', 'acquired_parents', 'exposed_answers', 'exposed_parents',
                     'zero_exposure_answers', 'q', 'subset_selection_depends_on_lengths'):
            record[name] = plan[name]
        record['plan_file_sha256'] = sha(plan_path)
    rows.append(record)
    vectors.append([q[i] for i in ids])
    evidence.append(dict(logical_run_id=logical, physical_run_id=physical,
                         summary_sha256=sha(summary_path), oracle_sha256=sha(root/'LOCAL_ORACLE_AUDIT.json'),
                         artifact_digest=oracle['artifact_digest'], full_state_sha256=oracle.get('state_sha256')))

names = [x['logical_run_id'] for x in rows]
values = np.asarray(vectors, dtype=np.uint8)
def cell(draw, budget, price, policy, training=None):
    if training is None: training = budget
    a = np.zeros(19, dtype=np.int8)
    a[names.index(f'd{draw}_b{budget}_p{price}_{policy}_t{training}')] = 1
    return a
def delta(draw, budget, price):
    return cell(draw,budget,price,'depth') - cell(draw,budget,price,'breadth')
contrasts, coefficients = [], []
def add(name, kind, draw, coefficient, **metadata):
    contrasts.append(dict(name=name, kind=kind, draw=draw, **metadata))
    coefficients.append(coefficient)
for d in (1,2):
    for b in (1,8):
        for p in (0,4):
            add(f'D{d}_Delta_p{p}_B{b}', 'policy_gap', d, delta(d,b,p), budget=b, price=p)
    for p in (0,4):
        add(f'D{d}_C_p{p}', 'joint_scaling_change_in_policy_gap', d,
            delta(d,8,p)-delta(d,1,p), price=p)
    for b in (1,8):
        add(f'D{d}_I_B{b}', 'price_interaction', d,
            delta(d,b,4)-delta(d,b,0), budget=b)
    add(f'D{d}_I_high_minus_low', 'change_in_price_interaction', d,
        delta(d,8,4)-delta(d,8,0)-delta(d,1,4)+delta(d,1,0))
assert len(contrasts) == 18
registered_main_count = len(contrasts)
for policy in ('breadth','depth'):
    add(f'D1_p0_{policy}_B8_minus_B1_at_T1', 'conditional_budget_effect_at_T1', 1,
        cell(1,8,0,policy,1)-cell(1,1,0,policy,1), price=0, policy=policy)
    add(f'D1_p0_{policy}_T8_minus_T1_at_B8', 'conditional_training_effect_at_B8', 1,
        cell(1,8,0,policy,8)-cell(1,8,0,policy,1), price=0, policy=policy)
for i in range(9):
    a, b = contrasts[i], contrasts[i+9]
    assert a['kind'] == b['kind'] and a['draw'] == 1 and b['draw'] == 2
    add('draw_mean_' + a['name'].split('_',1)[1], a['kind'], 'mean_of_two_observed_draws',
        (coefficients[i].astype(float)+coefficients[i+9])/2,
        component_names=[a['name'],b['name']])
coef = np.asarray(coefficients, dtype=np.float64)
assert np.all(coef.sum(axis=1) == 0)
point, interval = paired_percentile(values,coef,draws=10000,seed=20261013)
for i, item in enumerate(contrasts):
    item.update(estimate_pp=float(point[i]), conditional_question_percentile_CI95_pp=[float(interval[0,i]),float(interval[1,i])],
                coefficients={names[j]:float(v) for j,v in enumerate(coef[i]) if v})
    if 'component_names' in item:
        observed = [point[next(k for k,x in enumerate(contrasts) if x['name']==n)] for n in item['component_names']]
        item['observed_draw_range_pp'] = [float(min(observed)),float(max(observed))]
out.mkdir(exist_ok=False)
dump(out/'RESULTS.json',dict(schema='p008_all_cells_registered_primary_analysis_v1',
     utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), cells=rows, contrasts=contrasts,
     registered_main_contrasts=registered_main_count, inputs=evidence,
     bootstrap=dict(draws=10000,seed=20261013,numpy_version=np.__version__,
                    generator='numpy.default_rng / PCG64',unit='same paired question resampled jointly across all 19 fixed models',
                    interval='pointwise percentile 2.5/97.5%; no familywise coverage claim',
                    scope='Conditional on these trained models, two acquired pools, frozen parser and seen benchmark; not training-seed or procurement-population uncertainty'),
     full_B_by_T_interaction_available=False, J_available=False,
     missing_design_corners=['D1/p0/B1/T8/breadth','D1/p0/B1/T8/depth'],
     original_N2_passed=False,post_hoc_engineering_deviation=True,
     secondary_parser_sensitivity='pending separate uniformly applied reviewed implementation',
     final_CPU_integrity_complete=False,external_review='pending',
     new_model_calls=0,new_raw_scoring=0,analysis_script_sha256=sha(__file__),
     paired_question_core_sha256=sha('scripts/p008_paired_question_analysis.py'),
     protocol_sha256=sha('docs/experiments/P008_v3_1_protocol.md')))
dump(out/'MANIFEST.json',manifest(out))
print(json.dumps(dict(output=str(out),cells=len(rows),contrasts=len(contrasts),external_review='pending')))
