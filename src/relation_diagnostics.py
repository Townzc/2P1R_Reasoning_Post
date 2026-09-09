"""C016 deterministic CPU derivations from the frozen, already observed C015 set."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from src.relation_transport import allocation_schedule, render_prompt
from src.relation_verifier import STEP
from src.relation_diagnostic_verifier import ROUTE_MARKER, check_diagnostic, token_fields
from src.sft_data import encode_row, budget_report

CONFIG = Path('configs/diagnostics/relation_c016.json')
PROPOSAL = Path('configs/diagnostics/relation_c016_gpu_proposal.json')
NEW_SOURCES = [str(CONFIG), str(PROPOSAL), 'src/relation_diagnostics.py',
    'src/relation_diagnostic_verifier.py', 'scripts/prepare_relation_diagnostics.py',
    'scripts/verify_relation_diagnostics.py', 'tests/test_relation_diagnostics.py',
    'tests/test_relation_engineering.py',
    'docs/experiments/C016_relation_diagnostics.md']


def derive_rows(worlds, cfg):
    train_ids = [w['world_id'] for w in worlds[:cfg['train_worlds']]]
    dev_ids = [w['world_id'] for w in worlds[cfg['train_worlds']:]]
    if len(dev_ids) != cfg['dev_worlds']:
        raise ValueError('Wrong parent count')
    allocation = allocation_schedule(train_ids, cfg['assignment_seed'], cfg['cycles'])
    assignment = {**allocation['assignment'],
                  **allocation_schedule(dev_ids, cfg['assignment_seed'], 1)['assignment']}
    rows = []
    for world in worlds:
        wid = world['world_id']; route_id = assignment[wid]
        response = world['responses'][route_id]
        steps = [tuple(map(int, STEP.fullmatch(line).groups())) for line in response.splitlines()[:-1]]
        if len(steps) != 4:
            raise ValueError('Expected four original steps')
        base = {'parent_world_id': wid, 'parent_orbit_key': world['audit']['orbit']['key'],
                'split': 'train' if wid in train_ids else 'engineering_dev',
                'selected_route': route_id, 'path_id': str(route_id), 'step_position': None,
                'answer': world['answer'], 'response': response, 'prompt': world['prompt']}
        rows.append({**base, 'arm': 'fixed_reference', 'problem_id': wid})
        header, facts = world['prompt'].split('\nEdges:\n')
        hint = ROUTE_MARKER + '\n'.join(f'R E {e} : N {u} > N {v}' for e, u, _, v, _ in steps)
        rows.append({**base, 'arm': 'given_route', 'problem_id': wid,
                     'prompt': header + hint + '\nEdges:\n' + facts})
        by_id = {e['id']: e for e in world['question']['edges']}
        for position, (edge_id, u, before, v, after) in enumerate(steps):
            q = {'source': u, 'state': before, 'target': v, 'edges': [deepcopy(by_id[edge_id])]}
            rows.append({**base, 'arm': 'single_step', 'problem_id': f'{wid}:step{position}',
                'step_position': position, 'prompt': render_prompt(q), 'answer': after,
                'response': response.splitlines()[position] + f'\nAnswer : {after}'})
    schedules = {}
    for arm in cfg['arms']:
        train = [r for r in rows if r['arm'] == arm and r['split'] == 'train']
        indices = {(r['parent_world_id'], r['step_position']): i for i, r in enumerate(train)}
        schedules[arm] = [[indices[(wid, slot if arm == 'single_step' else None)]
                          for wid, slot in zip(update['world_ids'], update['multi'])]
                         for update in allocation['updates']]
    return rows, schedules, assignment


def prepare(worlds, cfg, tokenizer):
    rows, schedules, assignment = derive_rows(worlds, cfg)
    encoded = {}
    for row in rows:
        if not check_diagnostic(row['prompt'], row['response'], row['arm'])['valid']:
            raise ValueError('Derived reference fails exposed-prompt verifier')
        enc = encode_row(row, tokenizer, cfg['max_length'])
        row['token_fields'] = token_fields(row, tokenizer, enc)
        row['tokens'] = {k: enc[k] for k in ('n_prompt', 'n_supervised', 'n_processed')}
        encoded[(row['arm'], row['problem_id'])] = enc
    budgets = {}
    for arm in cfg['arms']:
        train = [r for r in rows if r['arm'] == arm and r['split'] == 'train']
        enc = [encoded[(arm, r['problem_id'])] for r in train]
        budget = budget_report(enc, schedules[arm], cfg['microbatch_size'])
        parents = Counter(train[i]['parent_world_id'] for update in schedules[arm] for i in update)
        if set(parents.values()) != {32} or len(parents) != 32:
            raise ValueError('Predetermined parent exposure differs')
        budget['parent_exposures'] = dict(parents)
        budget['independent_train_parent_count'] = len(parents)
        budget['unique_train_rows'] = len(train)
        budget['supervised_field_tokens'] = {
            name: sum(len(train[i]['token_fields'][name]) for update in schedules[arm] for i in update)
            for name in train[0]['token_fields']}
        budgets[arm] = budget
    return rows, schedules, assignment, json.loads(json.dumps(budgets))
