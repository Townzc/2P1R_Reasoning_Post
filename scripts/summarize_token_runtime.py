"""Describe saved runtime receipts and passive GPU samples; no model calls."""
import argparse
import csv
import io
import json
from pathlib import Path
from statistics import mean, median

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest


def summarize(root):
    root = Path(root)
    runs = {}
    for policy in ('breadth', 'depth'):
        for price in (0, 4):
            for seed in (17, 23):
                run = f'{policy}_p{price}_s{seed}'
                export = root / 'student_exports' / run
                receipt = root / 'students' / f'{run}_run_r1' / 'result.json'
                envelope = read(receipt)
                oracle = read(export / 'LOCAL_ORACLE_AUDIT.json')
                result = envelope['result']
                files = envelope['artifact_manifest']
                assert envelope['receipt']['status'] == 'completed'
                assert digest(files) == oracle['artifact_digest']
                assert oracle['outputs_independently_rescored'] == 1319
                assert oracle['updates_verified'] == 256
                assert oracle['supervised_tokens_verified'] == 524287
                samples = export / 'gpu_samples.jsonl'
                assert samples.stat().st_size == files['gpu_samples.jsonl']['bytes']
                assert sha(samples) == files['gpu_samples.jsonl']['sha256']
                rows, errors = [], []
                for line in samples.read_text().splitlines():
                    record = json.loads(line)
                    if 'csv' not in record:
                        errors.append(record)
                        continue
                    fields = next(csv.reader(io.StringIO(record['csv']), skipinitialspace=True))
                    assert len(fields) == 7 and 'H100' in fields[0]
                    rows.append(dict(epoch=record['epoch'], gpu_util_percent=float(fields[1]),
                                     memory_used_mib=float(fields[3]), memory_total_mib=float(fields[4]),
                                     power_watts=float(fields[5])))
                assert rows and all(a['epoch'] < b['epoch'] for a, b in zip(rows, rows[1:]))
                runs[run] = dict(
                    receipt_sha256=sha(receipt), samples_sha256=sha(samples),
                    committed_updates=result['committed_updates'],
                    training_update_seconds=result['train_seconds'],
                    worker_wall_seconds=result['wall_seconds'],
                    other_worker_seconds=result['wall_seconds'] - result['train_seconds'],
                    runtime_rate_estimate_usd=result['runtime_rate_estimate_usd'],
                    valid_samples=len(rows), sample_errors=errors,
                    sample_gpu_util_mean_percent=mean(x['gpu_util_percent'] for x in rows),
                    sample_gpu_util_median_percent=median(x['gpu_util_percent'] for x in rows),
                    sample_memory_max_mib=max(x['memory_used_mib'] for x in rows),
                    sample_power_mean_watts=mean(x['power_watts'] for x in rows))
    training = sum(x['training_update_seconds'] for x in runs.values())
    wall = sum(x['worker_wall_seconds'] for x in runs.values())
    return dict(schema='p007b_saved_runtime_descriptive_v1', runs=runs,
                training_update_gpu_minutes=training / 60, summed_worker_gpu_hours=wall / 3600,
                training_update_seconds_fraction=training / wall,
                runtime_rate_estimate_usd=sum(x['runtime_rate_estimate_usd'] for x in runs.values()),
                limitations=[
                    'Only these eight corrected students; not all project spending or a provider invoice.',
                    'Train seconds sum recorded optimizer-update durations; checkpoint saving is outside that sum.',
                    'Other worker time includes setup, evaluation, checkpoint and evidence I/O. It is not purely evaluation.',
                    'Recorded wall time ends before final manifest/envelope work; it is not the total billed lifecycle.',
                    'Roughly 60-second passive samples mix phases; their arithmetic means are not time-weighted utilization or FLOPS efficiency.',
                    'No comparison GPU or inference backend was benchmarked; this does not prove which hardware is optimal.'],
                new_model_calls=0)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    result = summarize(a.root)
    dump(a.out, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'runs'}))
