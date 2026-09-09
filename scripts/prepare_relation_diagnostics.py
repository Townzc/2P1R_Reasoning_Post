"""C016 CPU-only entrypoint; no model-loading, SSH, GPU, or launch functionality."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import signal
import time

from scripts.audit_family_matching import verified_tokenizer
from scripts.run_relation_cpu_audit import write_archive
from scripts.verify_relation_cpu_audit import load_archive
from scripts.verify_relation_diagnostics import audit_payload
from src.relation_diagnostics import CONFIG, NEW_SOURCES, prepare
from src.relation_engineering import provenance, load_frozen, dump
from src.sft_data import sha256_file


def main():
    p = argparse.ArgumentParser(); p.add_argument('--tokenizer-dir', required=True); args = p.parse_args()
    cfg = json.loads(CONFIG.read_text()); folder = Path(cfg['output_dir']); parent = Path(cfg['parent_dir'])
    if folder.exists(): raise FileExistsError('Immutable C016 attempt exists; no overwrite')
    if folder.name != cfg['attempt_id'] or sha256_file(parent/'manifest.json') != cfg['parent_manifest_sha256']:
        raise ValueError('Registered attempt or original parent mismatch')
    source = provenance(NEW_SOURCES)
    tokenizer, tokenizer_record = verified_tokenizer(Path(args.tokenizer_dir))
    start = time.monotonic(); folder.mkdir(parents=True, exist_ok=False)
    initial = {**source, 'phase': 'C016', 'config_sha256': sha256_file(CONFIG),
        'started_at_utc': datetime.now(timezone.utc).isoformat(), 'gpu_seconds_added': 0, 'model_calls': 0,
        'environment': {'python': platform.python_version(),
            **{p: importlib.metadata.version(p) for p in ('transformers','tokenizers','numpy','scipy')}}}
    dump(folder/'initial.json', initial)
    def deadline(*_): raise TimeoutError('Frozen C016 CPU wall deadline reached')
    old_handler = signal.signal(signal.SIGALRM, deadline); signal.alarm(cfg['cpu_wall_deadline_seconds'])
    try:
        _, _, legacy_train, _, _, legacy_schedule, legacy_budget = load_frozen(tokenizer)
        worlds = load_archive(parent/'worlds.json')
        rows, schedules, assignment, budgets = prepare(worlds, cfg, tokenizer)
        write_archive(folder/'rows.json', rows)
        for name, obj in (('schedules',schedules),('assignment',assignment),('budgets',budgets)):
            dump(folder/f'{name}.json', obj)
        report = audit_payload(rows, schedules, budgets, assignment, worlds,
                               legacy_train, legacy_schedule, legacy_budget, cfg, tokenizer)
        dump(folder/'audit.json', report)
        manifest = {**source, 'phase': 'C016', 'status': 'prepared_cpu_only',
            'config_sha256': sha256_file(CONFIG), 'parent_manifest_sha256': cfg['parent_manifest_sha256'],
            'tokenizer': tokenizer_record, 'parent_worlds': len(worlds), 'derived_rows': len(rows),
            'selection': report['selection'], 'scientific_dataset': False, 'model_calls': 0, 'gpu_seconds_added': 0,
            'files_sha256': {p.name: sha256_file(p) for p in sorted(folder.iterdir()) if p.is_file()},
            'wall_seconds': time.monotonic()-start}
        dump(folder/'manifest.json', manifest)
        print(json.dumps({k: manifest[k] for k in ('status','parent_worlds','derived_rows','wall_seconds')}))
    except Exception as exc:
        dump(folder/'failure.json', {'exception_type': type(exc).__name__, 'message': str(exc),
             'gpu_seconds_added': 0, 'model_calls': 0, 'wall_seconds': time.monotonic()-start})
        raise
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM, old_handler)


if __name__ == '__main__': main()
