"""Post-run E016 descriptive tables and complete ledger reconciliation; no models.

This does not replace the frozen raw-token auditor or change any score/gate.
Run from the repository root with the independently retained current ledger.
"""
import argparse
import hashlib
import json
from pathlib import Path

from analyses.e016 import decisions
from analyses.gsm8k_answer_audit import score


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', required=True, type=Path)
    parser.add_argument('--out-dir', required=True, type=Path)
    args = parser.parse_args()
    names = ('summary.json', 'paired_answers.jsonl', 'ledger_verification.json')
    if any((args.out_dir / name).exists() for name in names):
        raise FileExistsError('Keep existing E016 analysis outputs immutable')
    run = Path('runs/gsm8k_capability_e016_r1')
    manifest = read(run / 'run_manifest.json')
    assert manifest['status'] == 'completed'
    raw = {name: lines(run / (name + '.jsonl')) for name in ('base', 'e015')}
    marked = {name: [score(r, r['text'], r['score']['ended_with_eos'],
                          r['score']['truncated']) for r in rows]
              for name, rows in raw.items()}
    result = decisions(marked)
    assert result == read(run / 'metrics.json')
    pairs = []
    for index, (base, tuned) in enumerate(zip(raw['base'], raw['e015'], strict=True)):
        for key in ('problem_id', 'group_id', 'development_rank', 'prompt', 'answer'):
            assert base[key] == tuned[key]
        pairs.append({
            'problem_id': base['problem_id'], 'development_rank': base['development_rank'],
            'gold_answer': base['answer'],
            **{name: {'original_strict': rows[index]['score'], 'marked': marked[name][index]}
               for name, rows in raw.items()},
        })
    ledger = read(args.ledger)
    assert ledger['authorized_gpu_seconds'] == 7200
    assert len(ledger['jobs']) == 20
    assert len({job['run_id'] for job in ledger['jobs']}) == 20
    receipts = []
    for job in ledger['jobs']:
        path = Path('runs') / job['run_id'] / 'resource_receipt.json'
        assert read(path) == job, job['run_id']
        assert job['status'] not in ('running', 'reserved')
        assert type(job['charged_seconds']) is int
        receipts.append({'run_id': job['run_id'], 'charged_seconds': job['charged_seconds'],
                         'receipt_sha256': sha(path)})
    assert sum(r['charged_seconds'] for r in receipts) == 6921
    proof = {'phase': 'E016_LEDGER_RECONCILIATION', 'status': 'passed', 'receipts': receipts,
             'jobs': 20, 'used_seconds': 6921, 'remaining_seconds': 279, 'reservations': 0,
             'authorized_process_seconds': 7200, 'history_reset': False,
             'comparison': 'Every complete public receipt equals its private ledger job',
             'private_ledger_sha256': sha(args.ledger)}
    summary = {
        'phase': 'E016_POST_RUN_DESCRIPTIVE_SUMMARY', 'new_model_calls': 0,
        'execution_source_commit': manifest['source_commit'], 'result': result,
        'original_strict': {name: {
            key: sum(row['score'][key] for row in rows)
            for key in ('answer_correct', 'terminated_correct', 'ended_with_eos', 'truncated')
        } for name, rows in raw.items()},
        'base_gate_components': {'clean_correct_at_least_8': True,
                                 'parsed_at_least_48': True,
                                 'truncated_at_most_8': False},
        'gate_interpretation': 'Base fails the registered truncation requirement despite '
                              'measurable numeric capability. Both registered screens fail; '
                              'do not silently enter the base-pass conditional branch.',
        'raw_files': {str(run / (name + '.jsonl')): sha(run / (name + '.jsonl')) for name in raw},
        'scores_changed': False, 'reasoning_proofs_verified': False,
        'observed_development_parents_after_e016': 80,
        'remaining_reserved_development_parents': 432,
    }
    assert summary['base_gate_components'] == {
        'clean_correct_at_least_8': result['metrics']['base']['clean_correct'] >= 8,
        'parsed_at_least_48': result['metrics']['base']['parse_status'].get('parsed', 0) >= 48,
        'truncated_at_most_8': result['metrics']['base']['truncated'] <= 8,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, value in (('summary.json', summary), ('ledger_verification.json', proof)):
        with (args.out_dir / name).open('x') as stream:
            stream.write(json.dumps(value, indent=2, sort_keys=True) + '\n')
    with (args.out_dir / 'paired_answers.jsonl').open('x') as stream:
        stream.writelines(json.dumps(row, sort_keys=True) + '\n' for row in pairs)
    print(json.dumps({'status': 'passed', 'pairs': len(pairs), 'used_seconds': 6921,
                      'remaining_seconds': 279, 'new_model_calls': 0}))


if __name__ == '__main__':
    main()
