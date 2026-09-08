"""Append-only snapshot of the finite pilot queue, including missing/failed runs."""
import argparse
import csv
import json
from pathlib import Path

from src.sft_data import read_jsonl


def collect(queue):
    records = []
    completed = {}
    for phase in ('calibration', 'comparison'):
        for job in queue[phase]:
            cfg = json.loads(Path(job['config']).read_text())
            root = Path('runs')/job['run_id']
            def optional(name):
                return json.loads((root/name).read_text()) if (root/name).exists() else {}
            manifest, metrics, receipt, budget = map(optional, ['run_manifest.json', 'metrics.json', 'resource_receipt.json', 'actual_budget.json'])
            status = receipt.get('status', manifest.get('status', 'not_run'))
            row = {'run_id': job['run_id'], 'phase': phase, 'arm': cfg['arm'], 'status': status,
                   'git_commit': manifest.get('git_commit'), 'steps': metrics.get('steps'),
                   'supervised_tokens': budget.get('supervised_response_tokens'),
                   'charged_seconds': receipt.get('charged_seconds'),
                   'dev_accuracy': metrics.get('dev', {}).get('accuracy_macro'),
                   'dev_broad_accuracy': metrics.get('dev_broad', {}).get('accuracy_macro'),
                   'dev_pass_at_4': metrics.get('dev_sampled', {}).get('pass_at_k', {}).get('4'),
                   'peak_allocated_mib': metrics.get('throughput', {}).get('peak_allocated_mib'),
                   'config_sha256': job['config_sha256'], 'data_manifest_sha256': cfg['data_manifest_sha256']}
            records.append(row)
            if phase == 'comparison' and status == 'completed' and row['steps'] == cfg['steps']:
                completed[cfg['arm']] = root
    comparison = {'status': 'incomplete', 'interpretation': 'One paired seed, development-only, restricted arithmetic pilot; no population or seed-level significance claim.'}
    if set(completed) == {'repeat', 'surface', 'paths', 'gcm'}:
        rows = [r for r in records if r['phase'] == 'comparison']
        if len({r['supervised_tokens'] for r in rows}) != 1 or len({r['steps'] for r in rows}) != 1:
            raise ValueError('Completed arms have unmatched training doses')
        predictions = {arm: {p['problem_id']: p['correct'] for p in read_jsonl(root/'final_dev_greedy.jsonl')} for arm, root in completed.items()}
        if any(set(v) != set(predictions['paths']) for v in predictions.values()):
            raise ValueError('Development problem sets differ')
        comparison['status'] = 'complete'
        comparison['paired_counts_paths_vs_gcm'] = {
            'both_correct': sum(predictions['paths'][p] and predictions['gcm'][p] for p in predictions['paths']),
            'paths_only': sum(predictions['paths'][p] and not predictions['gcm'][p] for p in predictions['paths']),
            'gcm_only': sum(not predictions['paths'][p] and predictions['gcm'][p] for p in predictions['paths']),
            'both_wrong': sum(not predictions['paths'][p] and not predictions['gcm'][p] for p in predictions['paths'])}
    return {'runs': records, 'comparison': comparison}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--queue', default='configs/pilot_v1/queue.json')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = collect(json.loads(Path(a.queue).read_text()))
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    with (a.out/'results.tsv').open('x') as f:
        writer = csv.DictWriter(f, fieldnames=list(result['runs'][0]), delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(result['runs'])
    print(json.dumps(result['comparison']))


if __name__ == '__main__':
    main()
