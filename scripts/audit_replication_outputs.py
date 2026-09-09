"""Verify a completed Paths/GCM pair and audit its frozen development outputs.

No inference or holdout evaluation. Missing/incomplete jobs fail without a result
artifact. The original four-arm queue is accepted for regression tests, but only
its Paths and GCM comparison jobs are ever audited. All strata are inherited
from the seed17 CPU report, never selected using replication outcomes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from scripts.verify_pilot_outputs import verify
from src.evaluation import summarize
from src.metrics import macro_pass_at_k
from src.sft_data import read_jsonl, sha256_file
from src.trace_audit import audit_trace

DEFAULT_QUEUE = Path('configs/pilot_replication_seed23/queue.json')
PARENT_DATA = Path('runs/pilot_v1_20260908_r3')
PARENT_MANIFEST_SHA256 = '45c51cec657eff48e271a67d99439b5f390bc661562fab3bd3d920c450c03e6b'
LABELS = Path('reports/pilot_v1_structure_bias_20260909/per_problem.jsonl')
LABELS_SHA256 = '7ea6f0cb0b39a2df41440c49534b036ef4440953965943c6cb91cd67fe8dbdd0'
DEV_SHA256 = {
    'dev_matched.jsonl': 'c83bfcf156b53f6c75f443981d79045b1394f1d7383d17ba46d3200d23181cd3',
    'dev_broad.jsonl': '88ac632dfa1d4d5ac3e757021162156c8ac8891d6124cc040db97f38b4f81e73',
    'dev_blocks.json': 'a7bcab5f9773aa59c605bc2ff3c8594464d131f3c49467e4c328fc7206069091',
}
FILES = {
    'final_dev_greedy.jsonl': 64,
    'final_dev_broad_greedy.jsonl': 64,
    'final_train_sample16_greedy.jsonl': 16,
    'final_dev_sampled.jsonl': 256,
}
CODE = (
    'scripts/audit_replication_outputs.py', 'scripts/verify_pilot_outputs.py',
    'src/trace_audit.py', 'src/evaluation.py', 'src/metrics.py',
    'src/countdown_smoke.py', 'src/pilot_runtime.py', 'src/pilot_data.py',
    'src/sft_data.py', 'tests/test_replication_outputs.py',
)
LIMITATIONS = [
    'Greedy final-expression correctness remains the primary endpoint. The trace audit never replaces the official score.',
    'Trace status requires exact arithmetic, legal input consumption and an ordered-tree connection. Unknown syntax and equivalent but unconnected expressions remain unverifiable, not correct.',
    'Block, input-one and selected-reference-identity strata were fixed from the seed17 report before seed23 outputs; they were post-hoc for seed17 and are descriptive, not causal or significance tests.',
    'Selected-reference identity labels describe the four stored paths, not every possible solution. No new strata are inferred for broader development.',
    'Four stochastic generations share a problem, problems share selection blocks, and all use one trained model per arm. Counts are not independent trials or estimates of training-seed uncertainty.',
    'Only the completed Paths/GCM comparison jobs and stored train/development predictions are audited. No model inference, new sampling, holdout construction or holdout evaluation occurs. The prerequisite output verifier checks frozen allocation-file integrity without evaluating reserved groups.',
]


def read_json(path):
    return json.loads(Path(path).read_text())


def pinned_labels():
    if sha256_file(LABELS) != LABELS_SHA256:
        raise ValueError('Frozen seed17 stratum labels changed')
    labels = {}
    for row in read_jsonl(LABELS):
        if row['split'] != 'dev_matched':
            continue
        pid = row['problem_id']
        if pid in labels:
            raise ValueError('Duplicate frozen label identity')
        labels[pid] = {k: row[k] for k in ('problem_id', 'numbers', 'target', 'prompt',
                                           'block_id', 'has_input_one', 'any_reference_identity')}
    if len(labels) != 64 or Counter(row['block_id'] for row in labels.values()) != Counter({i: 4 for i in range(16)}):
        raise ValueError('Wrong frozen development blocks')
    return labels


def validate_data(cfg):
    root = Path(cfg['data_dir'])
    manifest_path = root/'manifest.json'
    if sha256_file(manifest_path) != cfg['data_manifest_sha256']:
        raise ValueError('Config data manifest hash mismatch')
    if sha256_file(PARENT_DATA/'manifest.json') != PARENT_MANIFEST_SHA256:
        raise ValueError('Frozen parent manifest changed')
    manifest = read_json(manifest_path)
    if root == PARENT_DATA:
        if cfg['seed'] != 17 or manifest['paired_seed'] != 17:
            raise ValueError('Unexpected original pilot seed')
    else:
        parent = manifest.get('parent', {})
        if (manifest.get('status') != 'FROZEN_PILOT_REPLICATION_V1'
                or parent.get('data_dir') != PARENT_DATA.as_posix()
                or parent.get('manifest_sha256') != PARENT_MANIFEST_SHA256
                or cfg['seed'] != 23 or manifest['paired_seed'] != 23):
            raise ValueError('Replication does not descend from the frozen seed17 data')
        if any(parent.get('preserved_files_sha256', {}).get(name) != digest for name, digest in DEV_SHA256.items()):
            raise ValueError('Replication parent development hashes differ')
    if cfg.get('eval_seed', cfg['seed']) != 17:
        raise ValueError('Evaluation seed must stay 17')
    for name, digest in DEV_SHA256.items():
        if (manifest['files_sha256'].get(name) != digest
                or sha256_file(root/name) != digest
                or sha256_file(PARENT_DATA/name) != digest):
            raise ValueError('Frozen development bytes differ: '+name)
    return manifest


def selected_jobs(queue_path):
    queue = read_json(queue_path)
    result = {}
    for job in queue['comparison']:
        config_path = Path(job['config'])
        cfg = read_json(config_path)
        if cfg.get('arm') not in ('paths', 'gcm'):
            continue
        arm = cfg['arm']
        if arm in result or Path(job['run_id']).name != job['run_id']:
            raise ValueError('Duplicate arm or invalid run ID')
        if sha256_file(config_path) != job['config_sha256']:
            raise ValueError('Queue config hash mismatch')
        if cfg['mode'] != 'scientific_pilot' or cfg['samples_per_problem'] != 4:
            raise ValueError('Expected a four-sample scientific pilot pair')
        manifest = validate_data(cfg)
        result[arm] = {'job': job, 'config': cfg, 'data_manifest': manifest}
    if set(result) != {'paths', 'gcm'}:
        raise ValueError('Exactly one Paths and one GCM comparison job are required')
    configs = [result[arm]['config'] for arm in ('paths', 'gcm')]
    left, right = ({key: value for key, value in cfg.items() if key != 'arm'} for cfg in configs)
    if left != right:
        differing = sorted(key for key in left.keys() | right.keys() if left.get(key) != right.get(key))
        raise ValueError('Comparison recipes differ beyond arm: '+', '.join(differing))
    return result


def paired(items, key, *, trace=False):
    counts = Counter()
    for item in items:
        a, b = (item['arms'][arm][key] for arm in ('paths', 'gcm'))
        counts['both' if a and b else 'paths_only' if a else 'gcm_only' if b else 'neither'] += 1
    suffix = 'verified' if trace else 'correct'
    return {'problems': len(items), 'both_'+suffix: counts['both'],
            'paths_only': counts['paths_only'], 'gcm_only': counts['gcm_only'],
            'neither_'+suffix: counts['neither'],
            'paths_minus_gcm_count': counts['paths_only']-counts['gcm_only']}


def problem_summary(items):
    result = {'problems': len(items), 'arms': {},
              'paired_greedy_final_expression': paired(items, 'greedy_correct'),
              'paired_greedy_complete_trace': paired(items, 'greedy_trace_verified', trace=True)}
    for arm in ('paths', 'gcm'):
        rows = [r['arms'][arm] for r in items]
        c = [r['sample_success_count'] for r in rows]
        t = [r['sample_trace_verified_count'] for r in rows]
        result['arms'][arm] = {
            'greedy_correct': sum(r['greedy_correct'] for r in rows),
            'greedy_trace_verified': sum(r['greedy_trace_verified'] for r in rows),
            'sample_success_count_histogram': {str(i): c.count(i) for i in range(5)},
            'sample_trace_verified_count_histogram': {str(i): t.count(i) for i in range(5)},
            'sample_correct_generations': sum(c), 'sample_problems_with_any_success': sum(v > 0 for v in c),
            'sample_trace_verified_generations': sum(t),
            'sample_pass_at_k': {str(k): macro_pass_at_k([(4, v) for v in c], k) for k in (1, 2, 4)},
        }
    return result


def run(queue_path, out):
    queue_path, out = Path(queue_path), Path(out)
    if out.exists():
        raise FileExistsError('Refusing to overwrite an existing output directory')
    jobs, labels = selected_jobs(queue_path), pinned_labels()
    sources = {path: sha256_file(Path(path)) for path in CODE}
    sources.update({queue_path.as_posix(): sha256_file(queue_path), LABELS.as_posix(): LABELS_SHA256,
                    (PARENT_DATA/'manifest.json').as_posix(): PARENT_MANIFEST_SHA256,
                    'configs/models.lock.json': sha256_file(Path('configs/models.lock.json'))})
    verified = {}
    # Verify both complete jobs before writing or generating any audit result.
    for arm, spec in jobs.items():
        root = Path('runs')/spec['job']['run_id']
        if not (root/'run_manifest.json').is_file():
            raise FileNotFoundError('Run has no completed outputs: '+root.as_posix())
        verified[arm] = verify(root)
        if verified[arm]['steps'] != 1024 or verified[arm]['supervised_response_tokens'] != 267456:
            raise ValueError('Completed dose differs from the fixed pilot')
        manifest = read_json(root/'run_manifest.json')
        if manifest['config'] != spec['config']:
            raise ValueError('Provided queue config differs from completed run')
        cfg = spec['config']
        relevant = [Path(spec['job']['config']), Path(cfg.get('pilot_queue', 'configs/pilot_v1/queue.json')),
                    Path(cfg['data_dir'])/'manifest.json']
        relevant += [Path(cfg['data_dir'])/name for name in spec['data_manifest']['files_sha256']]
        relevant += [root/name for name in ('run_manifest.json', 'resource_receipt.json', 'metrics.json',
                                            'train_history.jsonl', 'budget_report.json', 'actual_budget.json', *FILES)]
        for path in relevant:
            sources[path.as_posix()] = sha256_file(path)
    if verified['paths']['training_commit'] != verified['gcm']['training_commit']:
        raise ValueError('Comparison arms were trained from different source commits')
    records, evaluations = {}, {}
    for arm, spec in jobs.items():
        root = Path('runs')/spec['job']['run_id']
        records[arm], evaluations[arm] = {}, {}
        for name, expected_count in FILES.items():
            path = root/name
            predictions = read_jsonl(path)
            if len(predictions) != expected_count:
                raise ValueError('Wrong prediction count: '+path.as_posix())
            audits = []
            for index, p in enumerate(predictions, 1):
                a = audit_trace(p['text'], p['numbers'], p['target'])
                if any(a['final_expression'][field] != p[field] for field in ('parsed', 'correct', 'expression')):
                    raise ValueError('Independent final-expression audit disagrees: '+path.as_posix())
                if name in ('final_dev_greedy.jsonl', 'final_dev_sampled.jsonl'):
                    label = labels[p['problem_id']]
                    if any(p[field] != label[field] for field in ('numbers', 'target', 'prompt')):
                        raise ValueError('Prediction differs from frozen stratum identity')
                if type(p['sample_index']) is not int or (name == 'final_dev_sampled.jsonl' and p['sample_index'] not in range(4)):
                    raise ValueError('Sample indices must be 0,1,2,3')
                audits.append({'run_id': root.name, 'arm': arm, 'source': path.as_posix(),
                               'source_line': index, 'problem_id': p['problem_id'], 'sample_index': p['sample_index'],
                               'text_sha256': hashlib.sha256(p['text'].encode()).hexdigest(), 'audit': a})
            records[arm][name] = audits
            evaluations[arm][name] = {
                'generations': len(audits), 'official_scores': summarize(predictions, (1, 2, 4) if 'sampled' in name else ()),
                **{key: dict(sorted(Counter(r['audit'][key] for r in audits).items())) for key in
                   ('local_equations_status', 'resource_derivation_status', 'answer_connection_status', 'complete_trace_status')},
                'among_final_correct_complete_trace_status': dict(sorted(Counter(r['audit']['complete_trace_status'] for r in audits if r['audit']['final_expression']['correct']).items())),
            }
        if sum(len(rows) for rows in records[arm].values()) != 400:
            raise ValueError('Expected exactly 400 stored generations per arm')
    per_problem = []
    for pid, label in labels.items():
        item = {**label, 'arms': {}}
        for arm in ('paths', 'gcm'):
            greedy = [r for r in records[arm]['final_dev_greedy.jsonl'] if r['problem_id'] == pid]
            sampled = sorted([r for r in records[arm]['final_dev_sampled.jsonl'] if r['problem_id'] == pid], key=lambda r: r['sample_index'])
            if len(greedy) != 1 or [r['sample_index'] for r in sampled] != list(range(4)):
                raise ValueError('Wrong fixed matched-dev identities or sample indices')
            g = greedy[0]['audit']
            item['arms'][arm] = {
                'greedy_correct': g['final_expression']['correct'], 'greedy_trace_status': g['complete_trace_status'],
                'greedy_trace_verified': g['complete_trace_status'] == 'verified',
                'sample_success_count': sum(r['audit']['final_expression']['correct'] for r in sampled),
                'sample_trace_verified_count': sum(r['audit']['complete_trace_status'] == 'verified' for r in sampled),
            }
        per_problem.append(item)
    broader = []
    for arm in ('paths', 'gcm'):
        by_id = {r['problem_id']: r['audit'] for r in records[arm]['final_dev_broad_greedy.jsonl']}
        if arm == 'paths':
            broader = [{'problem_id': pid, 'arms': {}} for pid in by_id]
        if {item['problem_id'] for item in broader} != set(by_id):
            raise ValueError('Broader development pairing differs')
        for item in broader:
            a = by_id[item['problem_id']]
            item['arms'][arm] = {'greedy_correct': a['final_expression']['correct'],
                                 'greedy_trace_verified': a['complete_trace_status'] == 'verified'}
    strata = {}
    for field in ('has_input_one', 'any_reference_identity', 'block_id'):
        strata[field] = {str(value).lower(): problem_summary([r for r in per_problem if r[field] == value])
                         for value in sorted({r[field] for r in per_problem})}
    summary = {
        'schema_version': 1, 'status': 'COMPLETED_PAIR_VERIFIED_AND_AUDITED_ON_CPU',
        'queue': queue_path.as_posix(), 'training_seed': jobs['paths']['config']['seed'], 'eval_seed': 17,
        'run_ids': {arm: spec['job']['run_id'] for arm, spec in jobs.items()},
        'generations_per_arm': {arm: 400 for arm in jobs}, 'total_generations': 800,
        'official_final_scores_preserved': True, 'frozen_development_hashes_verified': DEV_SHA256,
        'frozen_label_sha256': LABELS_SHA256, 'output_verification': verified,
        'evaluations': evaluations, 'matched_overall': problem_summary(per_problem), 'matched_strata': strata,
        'broader_paired_greedy_final_expression': paired(broader, 'greedy_correct'),
        'broader_paired_greedy_complete_trace': paired(broader, 'greedy_trace_verified', trace=True),
        'source_sha256': dict(sorted(sources.items())), 'limitations': LIMITATIONS,
    }
    # Guard against a source/input changing between validation and serialization.
    if any(sha256_file(Path(path)) != digest for path, digest in sources.items()):
        raise ValueError('A source/input changed during the audit')
    out.mkdir(parents=True)
    output_hashes = {}
    def write_lines(relative, rows):
        path = out/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as stream:
            for row in rows:
                stream.write(json.dumps(row, sort_keys=True)+'\n')
        output_hashes[relative] = sha256_file(path)
    for arm in ('paths', 'gcm'):
        for name in FILES:
            write_lines(f'{arm}/{name.removesuffix(".jsonl")}.audit.jsonl', records[arm][name])
    write_lines('per_problem.jsonl', per_problem)
    summary['audit_files_sha256'] = output_hashes
    with (out/'summary.json').open('x') as stream:
        stream.write(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue', type=Path, default=DEFAULT_QUEUE)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.queue, args.out)
    except (FileNotFoundError, FileExistsError, ValueError, KeyError) as error:
        parser.exit(2, 'Audit refused: '+str(error)+'\n')
    print(json.dumps({'status': result['status'], 'run_ids': result['run_ids'],
                      'matched_overall': result['matched_overall']}, indent=2))


if __name__ == '__main__':
    main()
