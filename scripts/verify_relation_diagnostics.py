"""Read-only C016 reconstruction from C015; does not import the new builder."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import time

from scripts.audit_family_matching import verified_tokenizer
from scripts.verify_relation_cpu_audit import load_archive, render_from_existing_header
from src.relation_engineering import load_frozen, dump
from src.relation_transport import allocation_schedule
from src.relation_verifier import parse_prompt, solve, STEP
from src.relation_diagnostic_verifier import (ROUTE_MARKER, required_route,
    check_diagnostic, token_fields, FIELDS)
from src.sft_data import encode_row, budget_report, sha256_file

CONFIG = Path('configs/diagnostics/relation_c016.json')
PROPOSAL = Path('configs/diagnostics/relation_c016_gpu_proposal.json')


def distribution(values):
    counts = Counter(map(str, values))
    return {str(i): counts[str(i)] for i in range(5)}


def audit_payload(rows, schedules, budgets, assignment, worlds, legacy_train,
                  legacy_schedule, legacy_budget, cfg, tokenizer):
    """Check exact parent lineage, all retained rows, schedules and exposed facts."""
    train_ids = [w['world_id'] for w in worlds[:cfg['train_worlds']]]
    dev_ids = [w['world_id'] for w in worlds[cfg['train_worlds']:]]
    if len(train_ids) != 32 or len(dev_ids) != 16 or len(set(train_ids+dev_ids)) != 48:
        raise ValueError('Wrong fixed parent population')
    if len({w['audit']['orbit']['key'] for w in worlds}) != 48:
        raise ValueError('Parent conservative group overlap')
    # The first occurrence in the already archived E011 schedule is round zero.
    # Recover each training anchor from that artifact, not C016 construction.
    anchor = {}
    for update in legacy_schedule:
        for index in update:
            old = legacy_train[index]
            anchor.setdefault(old['problem_id'], int(old['path_id']))
    anchor.update(allocation_schedule(dev_ids, cfg['assignment_seed'], 1)['assignment'])
    if assignment != anchor:
        raise ValueError('Anchor assignment differs from original round zero')
    wanted = {(arm, w['world_id'], step) for w in worlds for arm in cfg['arms']
              for step in (range(4) if arm == 'single_step' else [None])}
    actual = [(r['arm'], r['parent_world_id'], r['step_position']) for r in rows]
    if len(actual) != len(set(actual)) or set(actual) != wanted:
        raise ValueError('Missing, extra or repeated derived row')
    if set(schedules) != set(cfg['arms']) or set(budgets) != set(cfg['arms']):
        raise ValueError('Missing or extra arm accounting')
    parents = {w['world_id']: w for w in worlds}; checks = Counter()
    for r in rows:
        w = parents[r['parent_world_id']]; arm = r['arm']; selected = anchor[w['world_id']]
        split = 'train' if w['world_id'] in train_ids else 'engineering_dev'
        if (r['split'], r['parent_orbit_key'], r['selected_route'], r['path_id']) != (
                split, w['audit']['orbit']['key'], selected, str(selected)):
            raise ValueError('Derived lineage, split or selected reference differs')
        original = parse_prompt(w['prompt']); q = parse_prompt(r['prompt'])
        lines = w['responses'][selected].splitlines()
        if arm == 'single_step':
            pos = r['step_position']; m = STEP.fullmatch(lines[pos])
            edge, u, before, v, after = map(int, m.groups())
            expected = {'source': u, 'state': before, 'target': v,
                        'edges': [e for e in original['edges'] if e['id'] == edge]}
            expected_text = render_from_existing_header(w['prompt'], expected)
            response = lines[pos] + f'\nAnswer : {after}'
            pid = f"{w['world_id']}:step{pos}"
            if q != expected or r['prompt'] != expected_text or r['answer'] != after:
                raise ValueError('One-step query differs from original transition')
        else:
            response = w['responses'][selected]; pid = w['world_id']
            if q != original or r['answer'] != w['answer']:
                raise ValueError('Full-graph facts/query changed')
            if arm == 'fixed_reference' and r['prompt'] != w['prompt']:
                raise ValueError('Fixed-reference prompt changed')
            if arm == 'given_route':
                route = required_route(r['prompt'])
                expected = [(s[0], s[1], s[3]) for s in
                            (tuple(map(int, STEP.fullmatch(line).groups())) for line in lines[:-1])]
                if route != expected:
                    raise ValueError('Supplied route differs from fixed reference')
                header, facts = r['prompt'].split('\nEdges:\n')
                if header.split(ROUTE_MARKER)[0] + '\nEdges:\n' + facts != w['prompt']:
                    raise ValueError('Changes beyond the route hint')
        if r['response'] != response or r['problem_id'] != pid:
            raise ValueError('Reference text or row identity changed')
        if solve(q) != [r['answer']] or not check_diagnostic(r['prompt'], response, arm)['valid']:
            raise ValueError('Exposed-facts reference/answer verification failed')
        checks['valid_references'] += 1
        encoded = encode_row(r, tokenizer, cfg['max_length'])
        if r['tokens'] != {k: encoded[k] for k in ('n_prompt', 'n_supervised', 'n_processed')}:
            raise ValueError('Exact token accounting differs')
        if r['token_fields'] != token_fields(r, tokenizer, encoded):
            raise ValueError('Stored semantic token fields differ')
        checks['exact_serializations_and_masks'] += 1
        changed = deepcopy(q); changed['state'] = (q['state']+1) % 5
        changed_text = render_from_existing_header(r['prompt'], changed)
        answer = solve(changed)
        if len(answer) != 1 or answer[0] == r['answer'] or check_diagnostic(changed_text, response, arm)['valid']:
            raise ValueError('Source-state counterfactual is not effective')
        checks['source_state_counterfactuals'] += 1
        wrong_final = response.rsplit('Answer : ', 1)[0] + f"Answer : {(r['answer']+1)%5}"
        if check_diagnostic(r['prompt'], wrong_final, arm)['valid']:
            raise ValueError('Wrong final state accepted')
        checks['wrong_final_rejections'] += 1
        first = STEP.fullmatch(response.splitlines()[0]); a, b = first.span(5)
        wrong_step = response[:a] + str((int(first.group(5))+1)%5) + response[b:]
        if check_diagnostic(r['prompt'], wrong_step, arm)['valid']:
            raise ValueError('Wrong local table application accepted')
        checks['wrong_step_rejections'] += 1
        if arm in ('fixed_reference', 'given_route'):
            for alt in range(4):
                if alt == selected: continue
                valid = check_diagnostic(r['prompt'], w['responses'][alt], arm)['valid']
                if valid != (arm == 'fixed_reference'):
                    raise ValueError('Incorrect legal-route versus required-route semantics')
                checks['alternative_routes_accepted' if valid else 'alternative_routes_rejected'] += 1
    details = {}
    for arm in cfg['arms']:
        train = [r for r in rows if r['arm'] == arm and r['split'] == 'train']
        enc = [encode_row(r, tokenizer, cfg['max_length']) for r in train]
        keys = {(r['parent_world_id'], r['step_position']): i for i, r in enumerate(train)}
        expected_schedule = [[keys[(legacy_train[i]['problem_id'], int(legacy_train[i]['path_id'])
                                    if arm == 'single_step' else None)] for i in update]
                             for update in legacy_schedule]
        if schedules[arm] != expected_schedule or len(expected_schedule) != 256:
            raise ValueError('Changed E011 parent/update order or step exposure')
        reproduced = budget_report(enc, expected_schedule, cfg['microbatch_size'])
        counts = Counter(train[i]['parent_world_id'] for u in expected_schedule for i in u)
        reproduced.update(parent_exposures=dict(counts), independent_train_parent_count=len(counts), unique_train_rows=len(train))
        reproduced['supervised_field_tokens'] = {
            name: sum(len(train[i]['token_fields'][name]) for update in expected_schedule for i in update)
            for name in FIELDS}
        if json.loads(json.dumps(reproduced)) != budgets[arm] or set(counts.values()) != {32}:
            raise ValueError('Token budget or parent exposure mismatch')
        row_counts = Counter(i for u in expected_schedule for i in u)
        if set(row_counts.values()) != ({8} if arm == 'single_step' else {32}):
            raise ValueError('Wrong row repetition dose')
        if arm == 'fixed_reference':
            for key in ('optimizer_updates', 'presentations', 'supervised_response_tokens',
                        'processed_nonpadding_tokens', 'padding_tokens', 'per_update'):
                if reproduced[key] != legacy_budget[key]:
                    raise ValueError('Fixed-reference accounting not matched to E011')
            checks['fixed_reference_e011_exact_dose_matches'] += 1
        details[arm] = {}
        for split in ('train', 'engineering_dev'):
            subset = [r for r in rows if r['arm'] == arm and r['split'] == split]
            states = [int(STEP.fullmatch(line).group(5)) for r in subset for line in r['response'].splitlines()[:-1]]
            details[arm][split] = {
                'rows': len(subset), 'parents': len({r['parent_world_id'] for r in subset}),
                'lengths': [list(v) for v in sorted({tuple(r['tokens'][k] for k in
                            ('n_prompt','n_supervised','n_processed')) for r in subset})],
                'answer_counts': distribution(r['answer'] for r in subset),
                'after_state_counts': distribution(states),
                'constant_2_after_state_correct_fraction': states.count(2)/len(states),
                'semantic_field_tokens_once_per_reference': {k: sum(len(r['token_fields'][k]) for r in subset) for k in FIELDS},
                'after_state_counts_by_certificate_position': [distribution(int(STEP.fullmatch(r['response'].splitlines()[j]).group(5))
                                                 for r in subset) for j in range(1 if arm == 'single_step' else 4)],
            }
            if arm == 'single_step':
                details[arm][split]['after_state_counts_by_original_route_position'] = [
                    distribution(r['answer'] for r in subset if r['step_position'] == j) for j in range(4)]
    singles = {split: [r for r in rows if r['arm'] == 'single_step' and r['split'] == split]
               for split in ('train', 'engineering_dev')}
    table_sets, operation_sets = {}, {}
    for split, subset in singles.items():
        qs = [parse_prompt(r['prompt']) for r in subset]
        table_sets[split] = {tuple(q['edges'][0]['table']) for q in qs}
        operation_sets[split] = {(tuple(q['edges'][0]['table']), q['state']) for q in qs}
    return {'verified': True, 'scope': 'CPU construction and token audit only; no learned-model measurement',
            'parents': 48, 'derived_rows': len(rows), 'cross_split_parent_orbit_overlap': 0,
            'checks': dict(checks), 'arms': details,
            'single_step_forward_rows': sum(parse_prompt(r['prompt'])['source'] == parse_prompt(r['prompt'])['edges'][0]['u'] for r in singles['train']+singles['engineering_dev']),
            'single_step_reverse_model_rows': 0,
            'single_step_shared_tables_across_parent_splits': len(table_sets['train'] & table_sets['engineering_dev']),
            'single_step_shared_table_input_operations_across_parent_splits': len(operation_sets['train'] & operation_sets['engineering_dev']),
            'selection': 'all_original_C015_parents_and_all_four_fixed_route_steps_no_filter_or_redraw',
            'development_is_observed_engineering_sandbox': True,
            'unseen_table_or_population_generalization_claimed': False,
            'gpu_seconds_added': 0, 'model_calls': 0}


def verify(directory, tokenizer_dir):
    started = time.monotonic(); directory = Path(directory)
    cfg = json.loads(CONFIG.read_text()); manifest = json.loads((directory/'manifest.json').read_text())
    if manifest['config_sha256'] != sha256_file(CONFIG) or manifest['parent_manifest_sha256'] != cfg['parent_manifest_sha256']:
        raise ValueError('Configuration or parent binding changed')
    for name, expected in manifest['files_sha256'].items():
        if Path(name).name != name or sha256_file(directory/name) != expected:
            raise ValueError('Prepared artifact hash mismatch')
    for name, expected in manifest['source_files_sha256'].items():
        historical = subprocess.check_output(['git', 'show', f"{manifest['source_commit']}:{name}"])
        if sha256_file(name) != expected or hashlib.sha256(historical).hexdigest() != expected:
            raise ValueError('Prepared source changed')
    parent = Path(cfg['parent_dir'])
    if sha256_file(parent/'manifest.json') != cfg['parent_manifest_sha256']:
        raise ValueError('Original C015 parent changed')
    tokenizer, tokenizer_record = verified_tokenizer(Path(tokenizer_dir))
    if tokenizer_record != manifest['tokenizer']:
        raise ValueError('Tokenizer identity mismatch')
    old_cfg, old_manifest, train, _, _, schedule, budget = load_frozen(tokenizer)
    if old_cfg['data_dir'] != cfg['parent_dir']:
        raise ValueError('Wrong original input directory')
    report = audit_payload(load_archive(directory/'rows.json'),
        json.loads((directory/'schedules.json').read_text()), json.loads((directory/'budgets.json').read_text()),
        json.loads((directory/'assignment.json').read_text()), load_archive(parent/'worlds.json'),
        train, schedule, budget, cfg, tokenizer)
    if report != json.loads((directory/'audit.json').read_text()):
        raise ValueError('Independent reconstruction differs from stored audit')
    proposal = json.loads(PROPOSAL.read_text())
    caps = len(proposal['order'])*(proposal['max_seconds_per_arm']+proposal['guard_seconds_per_arm'])
    if caps != proposal['maximum_all_three_reservation_seconds'] or caps > proposal['remaining_before_phase_seconds']:
        raise ValueError('Prospective complete-phase budget does not fit')
    for arm in cfg['arms']:
        if max(x[1] for x in report['arms'][arm]['train']['lengths']) > proposal['max_new_tokens'][arm]:
            raise ValueError('Prospective decode cap cannot contain gold plus EOS')
    return {'status': 'verified_cpu_only', 'data_manifest_sha256': sha256_file(directory/'manifest.json'),
            'audit_sha256': sha256_file(directory/'audit.json'), 'source_commit': manifest['source_commit'],
            'verification_checkout_commit': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'original_e011_runtime_sources_unchanged': True, 'parent_worlds': 48, 'derived_rows': len(load_archive(directory/'rows.json')),
            'all_stored_audit_fields_reproduced': True, 'max_proposed_reservation_seconds': caps,
            'proposal_is_not_a_launch_authorization': True, 'gpu_seconds_added': 0, 'model_calls': 0,
            'wall_seconds': time.monotonic()-started}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--data-dir', default='runs/relation_diagnostics_c016_r1')
    p.add_argument('--tokenizer-dir', required=True); p.add_argument('--output', required=True)
    args = p.parse_args()
    if Path(args.output).exists(): raise FileExistsError('Immutable verification receipt exists')
    result = verify(args.data_dir, args.tokenizer_dir); dump(args.output, result)
    print(json.dumps(result))


if __name__ == '__main__': main()
