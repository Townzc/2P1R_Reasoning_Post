"""Independent artifact checks without running a model or opening holdout answers."""
import argparse
from collections import Counter
import json
from pathlib import Path

from src.countdown_smoke import safe_parse
from src.pilot_data import allocate_groups, verify_row, make_arms, paired_schedule
from src.pilot_runtime import load_pilot_inputs
from src.sft_data import read_jsonl, sha256_file


def verify(cfg, tokenizer):
    root = Path(cfg['data_dir'])
    manifest = json.loads((root/'manifest.json').read_text())
    rows, dev, broad, schedule, audit = load_pilot_inputs(cfg, tokenizer)
    allocation = json.loads((root/'split_allocation.json').read_text())
    expected = allocate_groups(allocation['seed'], {'train': 4096, 'dev': 2048, 'holdout_reserved': 2048})
    actual = {k: [tuple(g) for g in v] for k, v in allocation['groups'].items()}
    if actual != expected:
        raise ValueError('Raw split allocation changed')
    allocated = {k: set(v) for k, v in actual.items()}
    observed = [{tuple(sorted(r['numbers'])) for r in s} for s in [rows, dev, broad]]
    if [len(s) for s in observed] != [256, 64, 64]:
        raise ValueError('Unexpected split size')
    if not observed[0] <= allocated['train'] or not (observed[1] | observed[2]) <= allocated['dev']:
        raise ValueError('Selected group crosses the presolver split boundary')
    if any(s & allocated['holdout_reserved'] for s in observed):
        raise ValueError('Reserved holdout contamination')
    for r in dev + broad:
        verify_row(r)
    for name, digest in manifest['source_files_sha256'].items():
        if sha256_file(name) != digest:
            raise ValueError('Preparation source hash mismatch: ' + name)
    if manifest['status'] == 'FROZEN_PILOT_REPLICATION_V1':
        parent = manifest['parent']
        parent_root = Path(parent['data_dir'])
        if sha256_file(parent_root/'manifest.json') != parent['manifest_sha256']:
            raise ValueError('Original pilot manifest changed')
        for name, digest in parent['preserved_files_sha256'].items():
            if sha256_file(parent_root/name) != digest or sha256_file(root/name) != digest:
                raise ValueError('Replication changed a frozen problem file: ' + name)
        blocks = json.loads((root/'train_blocks.json').read_text())
        if schedule != paired_schedule(len(blocks), manifest['cycles'], manifest['paired_seed']):
            raise ValueError('Replication schedule does not reproduce from its paired seed')
        expected_arms = make_arms(blocks, manifest['paired_seed'])
        for arm, expected_rows in expected_arms.items():
            if read_jsonl(root/f'train_{arm}.jsonl') != expected_rows:
                raise ValueError('Replication assignment does not reproduce: ' + arm)
    operators = {}
    for arm in ('repeat', 'surface', 'paths', 'gcm'):
        values = read_jsonl(root/f'train_{arm}.jsonl')
        counts = Counter()
        def count(tree):
            if tree[0] != 'n':
                counts[tree[0]] += 1
                count(tree[1]); count(tree[2])
        for r in values:
            count(safe_parse(r['expression']))
        operators[arm] = dict(counts)
    if operators['paths'] != operators['gcm']:
        raise ValueError('Binary operator exposure mismatch')
    return {'status': 'CPU_VERIFIED_NO_GPU_RUN', 'data_manifest_sha256': sha256_file(root/'manifest.json'),
            'split_groups': {'train': 256, 'dev_matched': 64, 'dev_broad': 64, 'holdout_reserved_unsolved': 2048},
            'raw_allocation_reproduced': True, 'source_hashes_verified': True,
            'all_references_verified': True, 'all_per_example_tokens_equal': audit['all_per_example_tokens_equal'],
            'all_per_update_structures_equal': audit['all_per_update_structures_paths_gcm_equal'],
            'budget_per_arm': {k: audit['arms']['paths'][k] for k in ['optimizer_updates', 'presentations', 'supervised_response_tokens', 'processed_nonpadding_tokens', 'padding_tokens']},
            'binary_operator_counts_per_arm_cycle': operators,
            'gpu_seconds_added': 0}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default='configs/pilot_v1/calibration.json')
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    from transformers import AutoTokenizer
    t = AutoTokenizer.from_pretrained(a.tokenizer_dir, local_files_only=True)
    result = verify(json.loads(Path(a.config).read_text()), t)
    with a.out.open('x') as f:
        f.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
