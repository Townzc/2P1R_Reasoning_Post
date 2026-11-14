"""Candidate A7 evidence adapter; real statistical execution awaits Claude review.

The reviewed p012_registered bootstrap core is imported unchanged. This adapter
binds Tinker requests, data, training state, sampler, labels and raw outputs.
It neither calls models nor changes any verdict. All comparisons are exploratory.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import zipfile

from analysis.p012_registered import (
    POLICY, bootstrap_delta, bound_file, differences, digest, outcomes,
    two_seed_contrast,
)

AUTHORITY = '2289056089f9ff3467d490efe93a92a07effb063'
A6_AUTHORITY = '18f64e2df34944da9b8fc6378609ccbdeed1c587'
ACCEPTED_A7_ANALYSIS_REVIEW = '8a8fac5c8ae75170e5c505f4215b5f1f9f0948d4'
CORE_SHA = 'b6973ad67c8eff3cec08806a553754911113944a044c9248bdb45aa1ac8d0b06'
RUNNER_SHA = '050a9f43d81c7a610dfc9ca30c901103e145fff28384d2efd1f13247fc60f5ee'
SCORER_SHA = '2183b0a13c55456a8c74b68f851dd1b01710904d33096ea57c6ce8c03eae74ed'
TERM_SHA = '21f869258be53f4b0d192fd7bcb5f8813dd4cda2cf790fc035c70251140a6c6d'
INPUT_SHA = '19019b07cca9bedc519149cef9fad8765cc40cb0fc1129b28485dab0d750848d'
MODELS = {
    '9b': ('Qwen/Qwen3.5-9B', 'c202236235762e1c871ad0ccb60c8ee5ba337b9a', 0.00047297908091376354),
    '4b': ('Qwen/Qwen3.5-4B', '851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a', 0.0004905250962784578),
    '9b_base': ('Qwen/Qwen3.5-9B-Base', '68c46c4b3498877f3ef123c856ecfde50c39f404', 0.00047297908091376354),
}
DATA_SHA = {
    '9b': {
        'short': '7f6dd97fc3a58276f607f6123b82c36413b6eb62a626d334add404796eca943d',
        'long': '2d597318d53c922400089a9e14df58c13c906854ad629468b51cce17118252c6',
        'concise': '090ef4576c05498e2a35bfd7ccd2e621bbee418cba2156d55d06a074b60819f9',
    },
    '4b': {
        'short': '55dc02f35c3d546e9b6df0b04fa31dde4f40ffb2e33b08c7562730fd2130e1d9',
        'long': 'bf4dd2d417518ca73db17ce67fa9652ba90653f69f211f7039956538cfc6f0b8',
        'concise': 'd60568ff56b7a8d486b6a24da05453d2e2f22b1432037813064d9f244e5f8a22',
    },
}
CONTRASTS = {'long_minus_short': ('long', 'short'),
             'long_minus_concise': ('long', 'concise'),
             'concise_minus_short': ('concise', 'short')}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def byte_sha(data):
    return hashlib.sha256(data).hexdigest()


def run_id(model, arm, seed):
    require(model in MODELS and arm in ('short', 'long', 'concise'), 'Unknown model or arm')
    require(seed in ((17,) if model == '9b_base' else (17, 29)), 'Unapproved training seed')
    prefix = 'a7_1' if arm == 'concise' else 'a7_2' if seed == 29 else 'a6_2'
    return f'{prefix}_tinker_lora_{model}_math_{arm}_s{seed}_20261113_v1'


def validate_training(request, model, arm, seed):
    repo, revision, lr = MODELS[model]
    expected_id = run_id(model, arm, seed)
    require((request['run_id'], request['model'], request['seed']) == (expected_id, repo, seed),
            'Training arm, model or seed changed')
    require(request.get('A7_arm', request.get('A6_arm')) == arm, 'Training arm changed')
    data_key = '9b' if model == '9b_base' else model
    require(request['dataset']['sha256'] == DATA_SHA[data_key][arm], 'Frozen training data changed')
    require((request['asset']['repo'], request['asset']['revision']) == (repo, revision), 'Model revision changed')
    require(request['mode'] == 'train' and request['cell'] == 'L', 'Training mode or cell changed')
    require((request['rank'], request['learning_rate']) == (32, lr), 'Training rank or learning rate changed')
    dose = request['dose']
    expected = {'parents': 512, 'distinct_rows': 512, 'paths_per_parent': 1, 'epochs': 2,
                'presentations': 1024, 'effective_batch': 8, 'expected_updates': 128}
    require(all(dose[k] == v for k, v in expected.items()), 'Training dose changed')
    require(request['source_sha256'] == RUNNER_SHA, 'Training source changed')
    prediction = AUTHORITY if expected_id.startswith('a7_') else A6_AUTHORITY
    require(request['prediction_commit'] == prediction, 'Training prediction changed')


def validate_generation(training, evaluation, generation, sampler, member_hashes):
    require(evaluation['mode'] == 'generate' and evaluation['model'] == training['model'] and
            evaluation['seed'] == training['seed'] and evaluation['source_sha256'] == RUNNER_SHA,
            'Evaluation model, seed or source changed')
    require(evaluation['asset'] == training['asset'], 'Evaluation asset changed')
    binding = evaluation['training_evidence']
    require(binding['run_id'] == training['run_id'] and binding['updates'] == 128,
            'Evaluation training identity changed')
    for field, member in [('train_loss_sha256', 'training/train_loss.jsonl'),
                          ('row_order_sha256', 'training/ROW_ORDER.json'),
                          ('state_manifest_sha256', 'training/STATE.json'),
                          ('sampler_manifest_sha256', 'training/SAMPLER.json')]:
        require(binding[field] == member_hashes[member], 'Training evidence cross-wired: ' + field)
    require(evaluation['sampler_path'] == sampler['path'], 'Sampler cross-wired')
    cfg = generation['config']
    expected = {'protocol': 'omi2', 'task': 'math', 'n': 1, 'temperature': 0.0,
                'top_p': 1.0, 'max_tokens': 4096, 'max_model_len': 8192, 'seed': training['seed']}
    require(all(cfg[k] == v for k, v in expected.items()) and
            generation['renderer'] == 'qwen3_5_disable_thinking', 'Greedy protocol changed')
    require(evaluation['evaluation']['sha256'] == generation['input_sha256'] == INPUT_SHA,
            'Evaluation questions changed')


def interval_fields(result):
    # Do not carry the main-grid 3pp/noticeable classification into exploratory A7.
    return {k: result[k] for k in ('n_questions', 'delta_pp', 'lower95_pp', 'upper95_pp',
                                   'ci_excludes_zero', 'draws_sha256')}


def validate_result_identity(result, training, request_hash):
    require(result['model'] == training['model'] and result['seed'] == training['seed'] and
            result['arm'] == training.get('A7_arm', training.get('A6_arm')) and
            result['cell'] == training['cell'] and result['dose'] == training['dose'],
            'Published result training identity changed')
    if training['run_id'].startswith('a7_'):
        require(result['training_run_id'] == training['run_id'] and
                result['training_request_sha256'] == request_hash and
                result['dataset']['sha256'] == training['dataset']['sha256'],
                'Published A7 request or dataset changed')
    else:
        # Legacy A6 results bind the same information through their evidence archive.
        require(result['dataset_sha256'] == training['dataset']['sha256'],
                'Published A6 dataset changed')


def read_endpoint(spec, model, arm, seed, input_ids):
    archive = bound_file(spec['archive'])
    result = json.loads(bound_file(spec['result']).read_text())
    dataset = bound_file(spec['training_data'])
    require(digest(dataset) == DATA_SHA['9b' if model == '9b_base' else model][arm], 'Manifest data changed')
    with zipfile.ZipFile(archive) as z:
        require(len(z.namelist()) == len(set(z.namelist())), 'Duplicate evidence member')
        get = lambda name: json.loads(z.read(name))
        train = get('training/REQUEST.json')
        validate_training(train, model, arm, seed)
        ev, gm = get('evaluation/REQUEST.json'), get('evaluation/generation/MANIFEST.json')
        members = ['training/train_loss.jsonl', 'training/ROW_ORDER.json', 'training/STATE.json', 'training/SAMPLER.json']
        hashes = {name: byte_sha(z.read(name)) for name in members}
        validate_generation(train, ev, gm, get('training/SAMPLER.json'), hashes)
        request_hash = byte_sha(z.read('training/REQUEST.json'))
        require(spec['training_request_sha256'] == request_hash, 'Manifest training request changed')
        validate_result_identity(result, train, request_hash)
        losses = [json.loads(x) for x in z.read('training/train_loss.jsonl').splitlines()]
        order = get('training/ROW_ORDER.json')
        require([x['step'] for x in losses] == list(range(1, 129)), 'Missing training updates')
        require([i for x in losses for i in x['row_indices']] == order and
                sorted(order) == sorted(list(range(512))*2), 'Training row order changed')
        require(all(get(part+'/COMPLETE.json')['success'] for part in ('training', 'evaluation')),
                'Incomplete endpoint')
        sm, term, pred = get('scores/MANIFEST.json'), get('TERMINATION.json'), get('PREDICTION_BEFORE_SCORE.json')
        labels = z.read('scores/labels.jsonl')
        values = outcomes((json.loads(x) for x in labels.splitlines()), input_ids)
        require(byte_sha(labels) == result['labels_sha256'] == sm['labels_sha256'] == term['labels_sha256'],
                'Label hashes disagree')
        require(sm['scorer_sha256'] == SCORER_SHA and term['source_sha256'] == TERM_SHA,
                'Scoring or termination source changed')
        require(sm['generation_manifest_sha256'] == byte_sha(z.read('evaluation/generation/MANIFEST.json')) and
                sm['input_sha256'] == INPUT_SHA, 'Score input binding changed')
        require(pred['prediction_commit'] == train['prediction_commit'] == ev['prediction_commit'],
                'Prediction commit mismatch')
        if train['run_id'].startswith('a7_'):
            timestamp = datetime.datetime.fromisoformat(pred['utc'])
            require(timestamp.utcoffset() == datetime.timedelta(0), 'A7 prediction needs UTC')
        details = {(r['id'], r['draw']): r for r in term['per_response']}
        require(len(details) == len(input_ids) and set(details) == {(i, 0) for i in input_ids},
                'Termination questions changed')
        h = hashlib.sha256()
        seen, normal_tokens = set(), []
        caps = normal_correct = 0
        with z.open('evaluation/generation/raw.jsonl') as f:
            for line in f:
                h.update(line)
                row = json.loads(line)
                key = (row['id'], row['draw'])
                require(key in details and key not in seen, 'Duplicate or unexpected raw output')
                seen.add(key)
                normal = row['finish_reason'] == 'stop' and not row['length_capped'] and bool(row['stopped_on_terminator'] or row['string_stop'])
                detail = details[key]
                require(detail['normal_termination'] == normal and detail['length_capped'] == row['length_capped'] and
                        detail['correct'] == values[row['id']], 'Raw/label/termination disagreement')
                caps += int(row['length_capped'])
                if normal:
                    normal_tokens.append(len(row['token_ids']))
                    normal_correct += int(values[row['id']])
        require(seen == set(details), 'Missing raw outputs')
        require(h.hexdigest() == result['raw_sha256'] == sm['raw_sha256'] == term['raw_sha256'] == pred['raw_sha256'],
                'Raw hashes disagree')
        a = term['all']
        require(a == result['MATH5000'] and a['responses'] == len(input_ids) and
                a['correct'] == sum(values.values()) and a['accuracy'] == sum(values.values())/len(input_ids) and
                a['length_cap_count'] == caps and a['loop_count'] == sum(r['looping'] for r in details.values()) and
                a['normally_terminated_count'] == len(normal_tokens) and a['normally_terminated_correct'] == normal_correct,
                'Published summary disagrees with evidence')
        diagnostic = None
        if a['length_cap_rate'] > .2:
            diagnostic = json.loads(bound_file(spec['first_boxed_diagnostic']).read_text())
            require(diagnostic['raw_sha256'] == h.hexdigest() and diagnostic['diagnostic_only'],
                    'First-box diagnostic cross-wired')
    return {'outcomes': values, 'accuracy': sum(values.values())/len(values), 'termination': a,
            'normal_output_tokens': {'count': len(normal_tokens), 'sum': sum(normal_tokens),
                                    'mean': sum(normal_tokens)/len(normal_tokens) if normal_tokens else None},
            'binding': {'run_id': train['run_id'], 'model': train['model'], 'arm': arm, 'seed': seed,
                        'dataset_sha256': train['dataset']['sha256'], 'updates': 128,
                        'archive_sha256': spec['archive']['sha256'], 'raw_sha256': result['raw_sha256'],
                        'labels_sha256': result['labels_sha256']}, 'first_boxed_diagnostic': diagnostic}


def analyze(manifest):
    require(ACCEPTED_A7_ANALYSIS_REVIEW is not None and
            manifest.get('accepted_analysis_review_commit') == ACCEPTED_A7_ANALYSIS_REVIEW,
            'A7 evidence adapter awaits Claude first-use review')
    require(digest('analysis/p012_registered.py') == CORE_SHA, 'Reviewed bootstrap core changed')
    require(manifest['authority_commit'] == AUTHORITY and manifest['excluded_from_H0_H3'] is True,
            'A7 authority or scope changed')
    inputs = [json.loads(x) for x in bound_file(manifest['inputs']).read_text().splitlines()]
    require(manifest['inputs']['sha256'] == INPUT_SHA and len(inputs) == 5000 and
            len({x['id'] for x in inputs}) == 5000, 'Full frozen MATH test required')
    ids = [x['id'] for x in inputs]
    require(set(manifest['models']) == set(MODELS), 'All three approved students required')
    output = {}
    for model in MODELS:
        seeds = ('17',) if model == '9b_base' else ('17', '29')
        setting = manifest['models'][model]
        require(set(setting) == set(seeds), 'Seed set changed')
        endpoints = {}
        for s in seeds:
            require(set(setting[s]) == {'short', 'long', 'concise'}, 'All three arms required')
            endpoints[s] = {a: read_endpoint(setting[s][a], model, a, int(s), ids) for a in setting[s]}
        comparisons = {}
        for name, (high, low) in CONTRASTS.items():
            if len(seeds) == 2:
                c = two_seed_contrast({s: endpoints[s][high]['outcomes'] for s in seeds},
                                      {s: endpoints[s][low]['outcomes'] for s in seeds})
                comparisons[name] = {'by_seed': {s: interval_fields(c['by_seed'][s]) for s in seeds},
                                     'seed_mean': interval_fields(c['seed_mean']),
                                     'same_nonzero_direction': c['same_nonzero_direction']}
            else:
                comparisons[name] = {'by_seed': {'17': interval_fields(bootstrap_delta(differences(
                    endpoints['17'][high]['outcomes'], endpoints['17'][low]['outcomes'])))}}
        output[model] = {'comparisons': comparisons,
                         'endpoints': {s: {a: {k: v for k, v in e.items() if k != 'outcomes'}
                                           for a, e in arms.items()} for s, arms in endpoints.items()}}
    return {'authority_commit': AUTHORITY, 'accepted_analysis_review_commit': ACCEPTED_A7_ANALYSIS_REVIEW,
            'exploratory': True, 'excluded_from_H0_H3': True, 'models': output,
            'policy': {k: POLICY[k] for k in ('replicates', 'seed', 'generator', 'numpy_version',
                       'quantile_method', 'unit', 'order', 'interval', 'seed_uncertainty')},
            'core_source_sha256': CORE_SHA,
            'interpretation': 'Question-paired intervals conditional on the observed seeds. All three fixed contrasts are reported; no main-grid hypothesis classification.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(json.loads(args.manifest.read_text()))
    result['input_manifest_sha256'] = digest(args.manifest)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')


if __name__ == '__main__':
    main()
