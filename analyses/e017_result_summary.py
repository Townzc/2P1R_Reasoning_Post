"""Descriptive E017 closeout from audited records; no model or score changes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--prior-ledger', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    names = ('summary.json', 'paired_stop_comparison.jsonl', 'ledger_verification.json')
    assert not any((args.out_dir / name).exists() for name in names), 'Preserve prior outputs'
    run = Path('runs/gsm8k_stop_e017_r1')
    old = Path('runs/gsm8k_capability_e016_r1')
    cfg = read('configs/real_math_e017/stopping.json')
    manifest, metrics = read(run / 'run_manifest.json'), read(run / 'metrics.json')
    assert manifest['status'] == 'completed' and manifest['config'] == cfg
    for path, digest in manifest['source_files_sha256'].items():
        assert sha(path) == digest, path
    for name in ('server_record_verification.json', 'local_record_verification.json'):
        audit = read(args.out_dir / name)
        assert audit['status'] == 'passed_independent_raw_prefix_checks'
        assert audit['raw_streams_checked'] == 64 and audit['result'] == metrics
        assert audit['resource_receipt_sha256'] == sha(run / 'resource_receipt.json')
    assert (args.out_dir / 'server_record_verification.json').read_bytes() == (
        args.out_dir / 'local_record_verification.json').read_bytes()
    current, previous = lines(run / 'base.jsonl'), lines(old / 'base.jsonl')
    old_marked = lines(old / 'base_marked.jsonl')
    assert len(current) == len(previous) == len(old_marked) == 64
    pairs, cells, reason_correct = [], Counter(), Counter()
    for before, after, marked in zip(previous, current, old_marked, strict=True):
        for key in ('problem_id', 'group_id', 'development_rank', 'prompt', 'answer'):
            assert before[key] == after[key]
        earlier, retained = before['generated_ids'], after['generated_ids']
        shared = 0
        for left, right in zip(earlier, retained):
            if left != right:
                break
            shared += 1
        assert marked['problem_id'] == after['problem_id']
        old_correct = marked['score']['clean_correct']
        new_correct = after['task_score']['task_answer_correct']
        cell = ('both_correct' if old_correct and new_correct else
                'old_clean_only' if old_correct else 'new_task_only' if new_correct else 'both_wrong')
        cells[cell] += 1
        reason = after['stop']['stop_reason']
        reason_correct[reason] += int(new_correct)
        pairs.append({'problem_id': after['problem_id'], 'development_rank': after['development_rank'],
                      'old_generated_tokens': len(earlier), 'new_retained_tokens': len(retained),
                      'shared_prefix_tokens': shared,
                      'new_retained_is_old_prefix': len(earlier) >= len(retained) and shared == len(retained),
                      'old_e016_clean_correct': old_correct, 'new_e017_task_correct': new_correct,
                      'new_stop_reason': reason, 'new_actual_eos': after['stop']['actual_eos_at_stop'],
                      'post_stop_padding_tokens': after['post_stop_padding_tokens'],
                      'comparison_cell': cell})
    assert sum(x['new_e017_task_correct'] for x in pairs) == metrics['task_answer_correct']
    assert sum(x['old_e016_clean_correct'] for x in pairs) == read(old / 'metrics.json')['metrics']['base']['clean_correct']
    ledger, prior = read(args.ledger), read(args.prior_ledger)
    assert sha(args.prior_ledger) == cfg['expected_ledger_sha256']
    assert ledger['authorized_gpu_seconds'] == prior['authorized_gpu_seconds'] == 7200
    assert len(prior['jobs']) == 20 and len(ledger['jobs']) == 21
    assert ledger['jobs'][:-1] == prior['jobs'], 'Historical receipts changed'
    assert ledger['jobs'][-1] == read(run / 'resource_receipt.json')
    assert len({j['run_id'] for j in ledger['jobs']}) == len(ledger['jobs'])
    receipts = []
    for job in ledger['jobs']:
        path = Path('runs') / job['run_id'] / 'resource_receipt.json'
        assert read(path) == job and job['status'] not in ('running', 'reserved')
        assert type(job['charged_seconds']) is int and job['charged_seconds'] >= 0
        receipts.append({'run_id': job['run_id'], 'charged_seconds': job['charged_seconds'],
                         'receipt_sha256': sha(path)})
    used = sum(j['charged_seconds'] for j in ledger['jobs'])
    assert used == sum(j['charged_seconds'] for j in prior['jobs']) + ledger['jobs'][-1]['charged_seconds']
    proof = {'status': 'passed', 'jobs': len(receipts), 'receipts': receipts,
             'used_seconds': used, 'remaining_seconds': 7200 - used, 'reservations': 0,
             'authorized_process_seconds': 7200, 'history_reset': False,
             'prior_jobs_unchanged': True, 'private_ledger_sha256': sha(args.ledger),
             'prior_private_ledger_sha256': sha(args.prior_ledger)}
    old_profile, profile = read(old / 'base_profile.json'), read(run / 'base_profile.json')
    summary = {'phase': 'E017_POST_RUN_DESCRIPTIVE_SUMMARY', 'new_model_calls': 0,
               'execution_source_commit': manifest['source_commit'], 'result': metrics,
               'correct_by_stop_reason': dict(reason_correct),
               'post_stop_padding_tokens': sum(r['post_stop_padding_tokens'] for r in current),
               'all_retained_prefixes_equal_e016': all(r['new_retained_is_old_prefix'] for r in pairs),
               'retained_prefix_mismatches': sum(not r['new_retained_is_old_prefix'] for r in pairs),
               'old_clean_vs_new_task_cells': dict(cells),
               'comparison_changes_completion_contract': True,
               'old_e016_metrics_unchanged': read(old / 'metrics.json')['metrics']['base'],
               'e017_profile': profile, 'e016_base_profile': old_profile,
               'observed_generation_time_ratio_e017_over_e016': profile['generation_seconds'] / old_profile['generation_seconds'],
               'timing_interpretation': 'One run on each cloned A800 instance; not a repeated causal throughput benchmark.',
               'original_scores_changed': False, 'reasoning_proofs_verified': False,
               'observed_development_parents': 80, 'reserved_development_parents': 432,
               'new_development_parents': 0, 'official_test_evaluated': False,
               'charged_process_seconds': ledger['jobs'][-1]['charged_seconds'],
               'new_phase_allowance': 0,
               'raw_files_sha256': {str(p): sha(p) for p in (old / 'base.jsonl', run / 'base.jsonl')}}
    assert summary['post_stop_padding_tokens'] == metrics['padded_batch_output_tokens'] - metrics['retained_generated_tokens']
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, obj in (('summary.json', summary), ('ledger_verification.json', proof)):
        with (args.out_dir / name).open('x') as f:
            f.write(json.dumps(obj, indent=2, sort_keys=True) + '\n')
    with (args.out_dir / 'paired_stop_comparison.jsonl').open('x') as f:
        f.writelines(json.dumps(p, sort_keys=True) + '\n' for p in pairs)
    print(json.dumps({'status': 'passed', 'pairs': len(pairs), 'prefix_mismatches': summary['retained_prefix_mismatches'],
                      'comparison_cells': dict(cells), 'used_seconds': used, 'remaining_seconds': 7200 - used}))


if __name__ == '__main__':
    main()
