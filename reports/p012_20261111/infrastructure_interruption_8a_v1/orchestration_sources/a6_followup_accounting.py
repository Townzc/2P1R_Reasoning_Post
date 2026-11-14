from pathlib import Path
import hashlib, json

ROOT = Path('.local/p012_20261111')
PUBLIC = Path('reports/p012_20261111')
AUTHORITY = '18f64e2df34944da9b8fc6378609ccbdeed1c587'
CROSS = '46694f515ff2c6d1f78931761f3f8e47dd0de2cb'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())

def accounting():
    components = []
    # v2 explicitly includes all saved v1 attempts; count this construction once.
    for model, version in [('9b', 'v2'), ('4b', 'v1')]:
        d = ROOT/'a6_length_v1'/f'a6_2_tinker_lora_{model}_m512_20261113_{version}'
        completed = (d/'result/COMPLETE.json').exists()
        if completed:
            assert read(d/'result/COMPLETE.json')['self_checks_passed']
        value = read(d/'result/USAGE.json')['upper_token_cost_usd'] if completed else 3.0
        components.append({'run_id': d.name, 'group': 'A6-2', 'kind': 'construction',
                           'complete': completed, 'usd': value,
                           'usage_sha256': sha(d/'result/USAGE.json') if completed else None})
    for d in sorted((ROOT/'a6_runs_v1').iterdir()):
        if not (d/'request.json').exists():
            continue
        r = read(d/'request.json')
        if r['mode'] != 'train':
            continue
        assert r['forecast']['admitted']
        ev = d.with_name(d.name.replace('_s17_', '_s17_greedy_'))
        for out, kind in [(d, 'training'), (ev, 'evaluation')]:
            done = (out/'result/COMPLETE.json').exists()
            if done:
                assert read(out/'result/COMPLETE.json')['success']
                value = read(out/'result/USAGE.json')['upper_token_cost_usd'] + (.1 if kind == 'training' else 0)
            elif kind == 'training':
                value = r['cpu_counts']['full_training_input_tokens'] * r['prices_per_million']['train']/1e6*1.25+.1
            else:
                value = r['forecast']['reserved_greedy_usd']
            components.append({'run_id': out.name, 'group': r['A6_group'], 'kind': kind,
                               'complete': done, 'usd': value,
                               'usage_sha256': sha(out/'result/USAGE.json') if done else None})
    failure_pointer = ROOT/'amendment7_v1/INTERRUPTION_LEDGER.json'
    if failure_pointer.exists():
        pointer = read(failure_pointer)
        assert sha(pointer['path']) == pointer['sha256']
        components.extend(x for x in read(pointer['path'])['components'] if x['group'] in ('A6-2','A6-3'))
    totals = {g: sum(x['usd'] for x in components if x['group'] == g) for g in ['A6-2', 'A6-3']}
    pointer = read(ROOT/'amendment6_v1/ORIGINAL_T_LEDGER_CURRENT.json')
    ledger = Path(pointer['path']); assert sha(ledger) == pointer['sha256'], 'Original-T ledger binding changed'
    original = read(ledger)[pointer['value_field']]
    assert 0 <= original <= 340
    return {'components': components, 'A6_2_accounted_and_reserved_usd': totals['A6-2'],
            'A6_3_accounted_and_reserved_usd': totals['A6-3'], 'original_T_reserved_usd': original,
            'combined_reserved_usd': original+sum(totals.values()), 'original_T_ledger_source': pointer,
            'caps_usd': {'A6-2': 50, 'A6-3': 35, 'original_T': 340, 'combined': 425}}

def require_9b_a6_3_complete():
    for cell in ['e4', 'e8', 'l64']:
        d = ROOT/'a6_runs_v1'/f'a6_3_tinker_lora_9b_math_{cell}_s17_greedy_20261113_v1'
        assert read(d/'result/COMPLETE.json')['success'], cell
        assert read(d/'result/generation/GENERATION_COMPLETE.json')['draws'] == 5000, cell

def ensure_budget(snapshot, amount, group='A6-2'):
    key = 'A6_2_accounted_and_reserved_usd' if group == 'A6-2' else 'A6_3_accounted_and_reserved_usd'
    assert snapshot[key]+amount <= snapshot['caps_usd'][group], (group, snapshot[key], amount)
    assert snapshot['combined_reserved_usd']+amount <= 425
