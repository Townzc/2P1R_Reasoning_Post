"""Inspect by default; explicitly execute one fixed E011 job on an owner-started A800."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

from scripts.audit_family_matching import verified_tokenizer
from src.relation_engineering import CONFIG, RELEASE, load_frozen, provenance, dump
from src.sft_data import sha256_file


def check_ledger(cfg, path, budget):
    path = Path(path)
    if not path.is_file():
        raise ValueError('Restore the current ledger; never initialize a replacement ledger')
    raw = path.read_bytes()
    ledger = json.loads(raw)
    if ledger['budget_id'] != budget['budget_id'] or ledger['authorized_gpu_seconds'] != 7200 or budget['authorized_gpu_seconds'] != 7200 or budget['gpus'] != 1:
        raise ValueError('Original single-GPU authorization differs')
    jobs = ledger['jobs']
    if any(x['status'] == 'reserved' or type(x['charged_seconds']) is not int or x['charged_seconds'] < 0 for x in jobs):
        raise ValueError('Invalid charge or unresolved reservation')
    if len({x['run_id'] for x in jobs}) != len(jobs) or cfg['run_id'] in {x['run_id'] for x in jobs}:
        raise ValueError('Duplicate or already-used run identity')
    used = sum(x['charged_seconds'] for x in jobs)
    if len(jobs) != cfg['expected_prior_jobs'] or used != cfg['expected_prior_used_seconds'] or hashlib.sha256(raw).hexdigest() != cfg['expected_ledger_sha256']:
        raise ValueError('Stale or modified prior ledger; independently reconcile before a new phase')
    reservation = cfg['max_seconds'] + cfg['guard_seconds']
    if cfg['guard_seconds'] != 15 or 7200-used < reservation:
        raise ValueError('Cannot reserve the complete fixed job plus guard')
    if (Path('runs')/cfg['run_id']).exists():
        raise FileExistsError('Immutable run directory already exists')
    return {'used_seconds': used, 'remaining_seconds': 7200-used,
            'maximum_reservation_seconds': reservation, 'unreserved_after_maximum': 7200-used-reservation,
            'prior_jobs': len(jobs), 'reservations': 0, 'ledger_sha256': hashlib.sha256(raw).hexdigest()}


def verify_snapshot(root):
    lock = json.loads(Path('configs/models.lock.json').read_text())['main']
    records = []
    for item in lock['files']:
        path = Path(root)/item['rfilename']
        size = path.stat().st_size
        if size != item['size']:
            raise ValueError('Pinned model file size mismatch')
        h = hashlib.sha256() if item.get('lfs') else hashlib.sha1(f'blob {size}\0'.encode())
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(8*1024*1024), b''):
                h.update(chunk)
        expected = item['lfs']['sha256'] if item.get('lfs') else item['blobId']
        if h.hexdigest() != expected:
            raise ValueError('Pinned original base snapshot differs')
        records.append({'file': item['rfilename'], 'bytes': size, 'digest': h.hexdigest()})
    return {'repo_id': lock['repo_id'], 'revision': lock['revision'], 'all_files_verified': True, 'files': records}


def server_preflight(cfg, snapshot):
    import torch
    if sys.platform != 'linux' or sys.version_info[:2] != (3, 12) or torch.__version__ != '2.8.0+cu128':
        raise ValueError('Require the recorded Linux/Python3.12/PyTorch2.8.0+cu128 recipe')
    packages = {'transformers': '4.56.2', 'tokenizers': '0.22.1', 'huggingface-hub': '0.34.4',
                'accelerate': '1.10.1', 'safetensors': '0.6.2', 'numpy': '2.3.2'}
    if any(importlib.metadata.version(k) != v for k, v in packages.items()):
        raise ValueError('Training dependency versions differ from the recorded recipe')
    timeout = shutil.which('timeout')
    if not timeout or 'GNU coreutils' not in subprocess.check_output([timeout, '--version'], text=True):
        raise ValueError('GNU timeout watchdog is mandatory')
    gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'], text=True).strip().splitlines()
    active = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'], text=True).strip()
    if len(gpu) != 1 or 'A800' not in gpu[0] or int(gpu[0].split(',')[1].strip()) < 75000 or active:
        raise ValueError('One idle A800 80GB is required')
    free = shutil.disk_usage('runs').free/1024**3
    if free < cfg['min_free_gib']:
        raise ValueError('Less than 12 GiB free after cache setup; preserve backups before cleanup/expansion')
    return {'gpu': gpu[0], 'active_compute_processes': 0, 'free_gib': free, 'packages': packages,
            'torch': torch.__version__, 'python': sys.version.split()[0], 'model': verify_snapshot(snapshot)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ledger', default='.local/resource_ledger.json')
    p.add_argument('--tokenizer-dir')
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    cfg = json.loads(CONFIG.read_text())
    source = provenance([str(RELEASE), *[str(p) for p in Path(cfg['data_dir']).iterdir() if p.is_file()]])
    accounting = check_ledger(cfg, a.ledger, json.loads(Path('configs/resource_budget.json').read_text()))
    if a.tokenizer_dir:
        snapshot = Path(a.tokenizer_dir)
    else:
        from huggingface_hub import snapshot_download
        lock = json.loads(Path('configs/models.lock.json').read_text())['main']
        snapshot = Path(snapshot_download(lock['repo_id'], revision=lock['revision'], local_files_only=True))
    tokenizer, _ = verified_tokenizer(snapshot)
    cfg, manifest, _, _, _, _, budget = load_frozen(tokenizer)
    report = {'phase': 'E011', 'status': 'not_run', 'execute_requested': a.execute, 'accounting': accounting,
              'source_commit': source['source_commit'], 'data_manifest_sha256': sha256_file(Path(cfg['data_dir'])/'manifest.json'),
              'optimizer_updates': budget['optimizer_updates'], 'supervised_tokens': budget['supervised_response_tokens'],
              'processed_tokens': budget['processed_nonpadding_tokens'], 'model_execution_performed': False}
    print(json.dumps(report, indent=2), flush=True)
    if not a.execute:
        return 0
    preflight = server_preflight(cfg, snapshot)
    preflight_path = Path('.local')/f"e011_preflight_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.json"
    dump(preflight_path, {**report, 'server': preflight, 'checked_at_utc': datetime.now(timezone.utc).isoformat()})
    # Recheck immediately before reservation; no shortened job, retry or queue fallback.
    check_ledger(cfg, a.ledger, json.loads(Path('configs/resource_budget.json').read_text()))
    command = [sys.executable, '-m', 'scripts.run_bounded', '--run-id', cfg['run_id'],
               '--max-seconds', str(cfg['max_seconds']), '--ledger', a.ledger,
               '--expected-ledger-sha256', cfg['expected_ledger_sha256'], '--require-full-cap', '--',
               sys.executable, '-m', 'src.relation_experiment', '--snapshot', str(snapshot),
               '--preflight', str(preflight_path)]
    return subprocess.call(command)


if __name__ == '__main__':
    sys.exit(main())
