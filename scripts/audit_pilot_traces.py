"""CPU-only post-hoc trace audit of the four completed, frozen pilot arms.

This command has a fixed development/train input allowlist, never opens the
reserved holdout, refuses output overwrite, and never changes primary metrics.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from src.trace_audit import audit_trace

ARMS = ('repeat', 'surface', 'paths', 'gcm')
FILES = ('final_dev_greedy.jsonl', 'final_dev_broad_greedy.jsonl',
         'final_train_sample16_greedy.jsonl', 'final_dev_sampled.jsonl')
DATA = Path('runs/pilot_v1_20260908_r3')
CODE = ('src/trace_audit.py', 'scripts/audit_pilot_traces.py', 'tests/test_trace_audit.py')
LIMITATIONS = [
    'Post-hoc descriptive diagnostic after observing seed17; not a preregistered primary endpoint.',
    'The complete-trace checker supports only the four frozen pilot sentence frames and one binary operation on displayed integer/rational values per step.',
    'Unknown syntax is unverifiable, never counted as correct. Inconsistent means an explicit arithmetic/resource/answer contradiction was established.',
    'Full verification requires legal consumption of every input exactly once and an exact ordered-tree connection to the final Answer. AC-only or other equivalent forms are separately reported as unverifiable under this strict connection rule.',
    'Equal-valued inputs and intermediate results are handled by enumerating provenance alternatives. Verification proves a consistent interpretation exists, not that the model internally followed it.',
    'Locally true equations need not form a legal derivation or reach the target; final-expression accuracy and complete-trace verification are reported separately.',
    'This audits displayed arithmetic, not hidden reasoning, causal faithfulness, cognitive strategies, or natural-language reasoning quality.',
    'One paired seed on restricted development sets. Sampled generations from the same problem are dependent; generation counts are descriptive, not independent trial counts.',
    'Only stored pilot development/train predictions and frozen development/train references were read; no generation, GPU work, or holdout evaluation.',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarize(records):
    count = len(records)
    final_correct = [r for r in records if r['audit']['final_expression']['correct']]
    statuses = ('local_equations_status', 'resource_derivation_status', 'answer_connection_status', 'complete_trace_status')
    return {'generations': count, 'problems': len({r['problem_id'] for r in records}),
            'final_expression_correct': len(final_correct),
            **{name: dict(sorted(Counter(r['audit'][name] for r in records).items())) for name in statuses},
            'among_final_correct_complete_trace_status': dict(sorted(Counter(r['audit']['complete_trace_status'] for r in final_correct).items())),
            'among_final_correct_local_equations_status': dict(sorted(Counter(r['audit']['local_equations_status'] for r in final_correct).items())),
            'equation_status_counts': dict(sorted(Counter(e['status'] for r in records for e in r['audit']['equations']).items())),
            'unknown_line_count': sum(len(r['audit']['unknown_lines']) for r in records),
            'reason_counts': dict(sorted(Counter(reason for r in records for reason in r['audit']['reasons']).items()))}


def run(out):
    if out.exists():
        raise FileExistsError('Refusing to overwrite an existing audit directory')
    sources = {path: digest(Path(path)) for path in CODE}
    results, all_records, references = {}, [], {}
    for arm in ARMS:
        results[arm] = {}
        for name in FILES:
            path = Path(f'runs/pilot_v1_{arm}_seed17_r1')/name
            sources[path.as_posix()] = digest(path)
            records = []
            for line_number, prediction in enumerate(rows(path), 1):
                audit = audit_trace(prediction['text'], prediction['numbers'], prediction['target'])
                for field in ('parsed', 'correct', 'expression'):
                    if audit['final_expression'][field] != prediction[field]:
                        raise AssertionError(f'Final expression score disagreement: {path}:{line_number} {field}')
                record = {'source': path.as_posix(), 'source_line': line_number,
                          'problem_id': prediction['problem_id'], 'sample_index': prediction['sample_index'],
                          'text_sha256': hashlib.sha256(prediction['text'].encode()).hexdigest(),
                          'arm': arm, 'evaluation': name.removesuffix('.jsonl'), 'audit': audit}
                records.append(record)
            all_records.extend(records)
            results[arm][name.removesuffix('.jsonl')] = summarize(records)
    # Confirm that this conservative grammar accepts every frozen training/dev
    # reference, rather than silently favoring the canonical non-Surface arm.
    for name in [f'train_{arm}.jsonl' for arm in ARMS] + ['dev_matched.jsonl', 'dev_broad.jsonl']:
        path = DATA/name
        sources[path.as_posix()] = digest(path)
        status = Counter()
        for row in rows(path):
            result = audit_trace(row['response'], row['numbers'], row['target'])
            status[result['complete_trace_status']] += 1
        references[path.as_posix()] = dict(sorted(status.items()))
        if set(status) != {'verified'}:
            raise AssertionError(f'Frozen reference not verified: {path}: {status}')
    paired = {}
    for name in ('final_dev_greedy', 'final_dev_broad_greedy'):
        by_arm = {arm: {r['problem_id']: r for r in all_records if r['arm'] == arm and r['evaluation'] == name}
                  for arm in ('paths', 'gcm')}
        if by_arm['paths'].keys() != by_arm['gcm'].keys():
            raise AssertionError('Paired problem IDs differ')
        counts = Counter()
        for pid in by_arm['paths']:
            a = by_arm['paths'][pid]['audit']['complete_trace_status'] == 'verified'
            b = by_arm['gcm'][pid]['audit']['complete_trace_status'] == 'verified'
            counts['both_verified' if a and b else 'paths_only_verified' if a else 'gcm_only_verified' if b else 'neither_verified'] += 1
        paired[name] = dict(sorted(counts.items()))
    summary = {'schema_version': 1, 'status': 'CPU_POSTHOC_TRACE_DIAGNOSTIC',
               'created_utc': datetime.now(timezone.utc).isoformat(),
               'base_git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
               'source_sha256': sources, 'prediction_count': len(all_records),
               'final_expression_scores_match_stored_primary_scores': True,
               'frozen_reference_grammar_check': references, 'results': results,
               'paths_gcm_paired_complete_trace_verification': paired,
               'limitations': LIMITATIONS}
    # All computations and validation finish before creating immutable outputs.
    out.mkdir(parents=True)
    (out/'predictions.audit.jsonl').write_text(''.join(json.dumps(row, sort_keys=True)+'\n' for row in all_records))
    summary['audited_records_sha256'] = digest(out/'predictions.audit.jsonl')
    (out/'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    lines = ['# Pilot v1 post-hoc arithmetic trace audit', '',
             'The official final-expression metrics are unchanged. This independent CPU',
             'diagnostic checks stored generations against exact arithmetic and input-use',
             'constraints, then requires a direct ordered-tree connection to the Answer.', '',
             '| Evaluation | Arm | Generations | Final correct | All local equations consistent | Resource derivation verified | Complete trace verified | Final correct but trace inconsistent | Final correct but trace unverifiable |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for name in (x.removesuffix('.jsonl') for x in FILES):
        for arm in ARMS:
            s = results[arm][name]
            lines.append(f"| {name} | {arm} | {s['generations']} | {s['final_expression_correct']} | {s['local_equations_status'].get('consistent', 0)} | {s['resource_derivation_status'].get('verified', 0)} | {s['complete_trace_status'].get('verified', 0)} | {s['among_final_correct_complete_trace_status'].get('inconsistent', 0)} | {s['among_final_correct_complete_trace_status'].get('unverifiable', 0)} |")
    lines += ['', 'All frozen training/development reference traces pass the complete checker',
              f"({sum(sum(x.values()) for x in references.values())} reference rows across six files). All {len(all_records)} re-parsed final-expression",
              'scores agree with the saved official scores. No holdout file was opened.', '',
              'Matched Paths/GCM pairs under the stricter complete-trace diagnostic:', '',
              '```json', json.dumps(paired, indent=2), '```', '',
              '## Interpretation and limitations', '']
    lines += ['- '+item for item in LIMITATIONS]
    lines += ['', 'Each generated output has a line-level audit in `predictions.audit.jsonl`.',
              'The original text is retained in its immutable run file and linked by source',
              'path, line number, problem/sample identity, and SHA-256. `summary.json`',
              'records full source-file and audit-code hashes for exact reproduction.', '',
              'Reproduce into a fresh output directory:', '',
              '```bash', 'python -m scripts.audit_pilot_traces --out reports/new_trace_audit', '```', '']
    (out/'README.md').write_text('\n'.join(lines))
    print(json.dumps({'out': out.as_posix(), 'predictions': len(all_records), 'results': results}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    run(parser.parse_args().out)
