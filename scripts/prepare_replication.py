"""Freeze a new paired seed on the identical pilot problems, CPU only.

No solving, holdout materialization, training or outcome-based selection occurs.
The original files stay immutable. All four arms are regenerated for the audit;
the separate reviewed queue selects only Paths/GCM for the GPU replication.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from src.pilot_data import make_arms, paired_schedule, audit_arms, canonical_hash
from src.pilot_runtime import load_pilot_inputs
from src.sft_data import sha256_file


PRESERVED = ('split_allocation.json', 'train_blocks.json', 'train_selection_audit.json',
             'dev_blocks.json', 'dev_matched.jsonl', 'dev_broad.jsonl')
SOURCES = ('scripts/prepare_replication.py', 'src/pilot_data.py', 'src/pilot_runtime.py',
           'scripts/audit_exact_matching.py', 'src/countdown_smoke.py', 'src/sft_data.py')


def dump(path, value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value, indent=2) + '\n')


def prepare(parent_config, out, tokenizer_dir, seed=23):
    cfg = json.loads(Path(parent_config).read_text())
    parent = Path(cfg['data_dir'])
    _, _, _, old_schedule, _ = load_pilot_inputs(cfg)
    old = json.loads((parent/'manifest.json').read_text())
    if seed == old['paired_seed'] or seed < 0:
        raise ValueError('Replication must have a new nonnegative paired seed')
    if old['status'] != 'FROZEN_PILOT_V1_NO_MODEL_OUTCOMES':
        raise ValueError('Replication must derive directly from the original frozen pilot')
    for name, digest in old['source_files_sha256'].items():
        if sha256_file(name) != digest:
            raise ValueError('Original preparation source changed: ' + name)
    lock = json.loads(Path('configs/models.lock.json').read_text())['main']
    content = (Path(tokenizer_dir)/'tokenizer.json').read_bytes()
    digest = hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
    expected = next(f['blobId'] for f in lock['files'] if f['rfilename'] == 'tokenizer.json')
    if digest != expected or digest != old['model']['tokenizer_git_blob']:
        raise ValueError('Tokenizer differs from the pinned original pilot')
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir, local_files_only=True)
    source_hashes = {name: sha256_file(name) for name in SOURCES}
    parent_manifest_sha = sha256_file(parent/'manifest.json')
    preserved = {name: sha256_file(parent/name) for name in PRESERVED}
    blocks = json.loads((parent/'train_blocks.json').read_text())
    arms = make_arms(blocks, seed=seed)
    schedule = paired_schedule(len(blocks), cycles=old['cycles'], seed=seed)
    if schedule == old_schedule:
        raise ValueError('New seed did not change the presentation schedule')
    if arms['gcm'] == make_arms(blocks, seed=old['paired_seed'])['gcm']:
        raise ValueError('New seed did not change the GCM assignment')
    audit = audit_arms(arms, schedule, tokenizer, cfg['max_length'])
    old_audit = json.loads((parent/'matching_audit.json').read_text())
    budget_keys = ('optimizer_updates', 'presentations', 'supervised_response_tokens',
                   'processed_nonpadding_tokens', 'padding_tokens')
    for arm in arms:
        if any(audit['arms'][arm][k] != old_audit['arms'][arm][k] for k in budget_keys):
            raise ValueError('Replication changed the original training dose: ' + arm)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    for name in PRESERVED:
        shutil.copyfile(parent/name, out/name)
    for arm, rows in arms.items():
        with (out/f'train_{arm}.jsonl').open('x') as f:
            for row in rows:
                f.write(json.dumps(row, separators=(',', ':'))+'\n')
    schedule_file = f'schedule_seed{seed}.json'
    dump(out/schedule_file, schedule)
    dump(out/'matching_audit.json', audit)
    manifest = {
        'schema_version': 2, 'status': 'FROZEN_PILOT_REPLICATION_V1',
        'preparation_timing': 'After seed17 outcomes; before any seed23 model outcomes.',
        'seed': old['seed'], 'paired_seed': seed, 'cycles': old['cycles'],
        'schedule_file': schedule_file, 'schedule_canonical_sha256': canonical_hash(schedule),
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'source_worktree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip()),
        'source_files_sha256': source_hashes,
        'parent': {'data_dir': str(parent), 'manifest_sha256': parent_manifest_sha,
                   'paired_seed': old['paired_seed'], 'preserved_files_sha256': preserved},
        'model': old['model'], 'splits': old['splits'],
        'group_disjoint_before_augmentation': True,
        'limitations': old['limitations'] + [
            'Joint assignment/order replication; does not isolate those factors.',
            'Same selected problems; not an independent training-data replication.',
            'Four arms materialized for checks; only Paths/GCM selected for training.'],
        'files_sha256': {p.name: sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()}}
    if source_hashes != {name: sha256_file(name) for name in SOURCES}:
        raise RuntimeError('Preparation source changed during execution')
    if parent_manifest_sha != sha256_file(parent/'manifest.json'):
        raise RuntimeError('Original manifest changed during execution')
    if any(sha256_file(parent/n) != h or sha256_file(out/n) != h for n, h in preserved.items()):
        raise RuntimeError('Preserved problem files changed during preparation')
    dump(out/'manifest.json', manifest)
    return {'status': manifest['status'], 'paired_seed': seed,
            'data_manifest_sha256': sha256_file(out/'manifest.json'),
            'preserved_parent_files': list(PRESERVED),
            'budget_per_arm': {k: audit['arms']['paths'][k] for k in budget_keys},
            'gpu_seconds_added': 0}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--parent-config', default='configs/pilot_v1/paths.json')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--seed', type=int, default=23)
    a = p.parse_args()
    print(json.dumps(prepare(a.parent_config, a.out, a.tokenizer_dir, a.seed)))


if __name__ == '__main__':
    main()
