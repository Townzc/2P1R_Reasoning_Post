"""Inspect E013 by default; --execute launches exactly one guarded A800 run."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from scripts.audit_family_matching import verified_tokenizer
from scripts.run_relation_engineering import check_ledger, server_preflight
from src.real_math_engineering import CONFIG, RELEASE, load_frozen, provenance, dump
from src.sft_data import sha256_file


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ledger', default='.local/resource_ledger.json')
    p.add_argument('--tokenizer-dir')
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    cfg = json.loads(CONFIG.read_text())
    source = provenance([RELEASE, *Path(cfg['data_dir']).iterdir()])
    budget = json.loads(Path('configs/resource_budget.json').read_text())
    accounting = check_ledger(cfg, a.ledger, budget)
    if a.tokenizer_dir:
        snapshot = Path(a.tokenizer_dir)
    else:
        from huggingface_hub import snapshot_download
        lock = json.loads(Path('configs/models.lock.json').read_text())['main']
        snapshot = Path(snapshot_download(lock['repo_id'], revision=lock['revision'], local_files_only=True))
    tokenizer, _ = verified_tokenizer(snapshot)
    cfg, _, _, _, _, _, tokens = load_frozen(tokenizer)
    report = {'phase': 'E013', 'status': 'not_run', 'execute_requested': a.execute,
              'source_commit': source['source_commit'], 'accounting': accounting,
              'data_manifest_sha256': sha256_file(Path(cfg['data_dir'])/'manifest.json'),
              'optimizer_updates': tokens['optimizer_updates'],
              'supervised_tokens': tokens['supervised_response_tokens'],
              'processed_tokens': tokens['processed_nonpadding_tokens'],
              'model_execution_performed': False}
    print(json.dumps(report, indent=2), flush=True)
    if not a.execute:
        return 0
    preflight = server_preflight(cfg, snapshot)
    preflight_path = Path('.local')/f"e013_preflight_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.json"
    dump(preflight_path, {**report, 'server': preflight, 'checked_at_utc': datetime.now(timezone.utc).isoformat()})
    check_ledger(cfg, a.ledger, budget)
    return subprocess.call([sys.executable, '-m', 'scripts.run_bounded', '--run-id', cfg['run_id'],
        '--max-seconds', str(cfg['max_seconds']), '--ledger', a.ledger,
        '--expected-ledger-sha256', cfg['expected_ledger_sha256'], '--require-full-cap', '--',
        sys.executable, '-m', 'src.real_math_experiment', '--snapshot', str(snapshot), '--preflight', str(preflight_path)])


if __name__ == '__main__':
    sys.exit(main())
