"""C015: extract an immutable engineering subset only after source publication."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from scripts.audit_family_matching import verified_tokenizer
from scripts.run_relation_cpu_audit import write_archive
from src.relation_engineering import CONFIG, provenance, original_worlds, materialize, dump
from src.sft_data import sha256_file


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tokenizer-dir', required=True)
    a = p.parse_args()
    cfg = json.loads(CONFIG.read_text())
    folder = Path(cfg['data_dir'])
    if folder.exists():
        raise FileExistsError('Immutable engineering output already exists')
    source = provenance()
    tokenizer, tokenizer_record = verified_tokenizer(Path(a.tokenizer_dir))
    start = time.monotonic()
    folder.mkdir(parents=True, exist_ok=False)
    dump(folder/'initial.json', {**source, 'phase': 'C015', 'gpu_seconds_added': 0,
         'started_at_utc': datetime.now(timezone.utc).isoformat(), 'config_sha256': sha256_file(CONFIG)})
    try:
        worlds = original_worlds(cfg)
        train, evaluation, encoded, schedule, budget = materialize(worlds, cfg, tokenizer)
        write_archive(folder/'worlds.json', worlds)
        dump(folder/'schedule.json', schedule)
        dump(folder/'budget.json', budget)
        manifest = {**source, 'phase': 'C015', 'status': 'prepared_cpu_only',
            'config_sha256': sha256_file(CONFIG), 'c014_summary_sha256': cfg['c014_summary_sha256'],
            'tokenizer': tokenizer_record, 'train_worlds': cfg['train_count'], 'train_references': len(train),
            'dev_worlds': cfg['dev_count'], 'final_generation_prompts': sum(map(len, evaluation.values())),
            'baseline_generation_prompts': cfg['dev_count'], 'selection': 'fixed_seed_prefix_no_output_filter',
            'scientific_dataset': False, 'gpu_seconds_added': 0, 'wall_seconds': time.monotonic()-start,
            'files_sha256': {x.name: sha256_file(x) for x in sorted(folder.iterdir()) if x.is_file()}}
        dump(folder/'manifest.json', manifest)
        print(json.dumps({k: manifest[k] for k in ('status', 'train_worlds', 'train_references', 'dev_worlds', 'wall_seconds')}))
    except Exception as exc:
        dump(folder/'failure.json', {'exception_type': type(exc).__name__, 'message': str(exc),
                                   'gpu_seconds_added': 0, 'wall_seconds': time.monotonic()-start})
        raise


if __name__ == '__main__':
    main()
