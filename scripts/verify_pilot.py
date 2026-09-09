"""Independent artifact checks without running a model or opening holdout answers."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

from src.countdown_smoke import safe_parse
from src.pilot_data import allocate_groups, verify_row, make_arms, paired_schedule
from src.pilot_runtime import load_pilot_inputs
from src.sft_data import read_jsonl, sha256_file


# These exact historical manifests recorded dirty preparation worktrees. Their
# source bytes were subsequently published in the verified GPU execution tree;
# this binding does not retroactively make preparation clean or prepublished.
LATER_PUBLISHED_SOURCE_SNAPSHOTS = {
    '45c51cec657eff48e271a67d99439b5f390bc661562fab3bd3d920c450c03e6b': {
        'commit': '6128e4266d62f14f063585d4c8e94dbe3ad8c711',
        'manifest_path': 'runs/pilot_v1_20260908_r3/manifest.json'},
    '0959c217feb4b0c51aebf85c1f08e341e1b6c8034657ee028acb263a2ee18ad4': {
        'commit': '6128e4266d62f14f063585d4c8e94dbe3ad8c711',
        'manifest_path': 'runs/pilot_replication_seed23_20260909_r1/manifest.json'},
}


def _repository_path(name):
    if (not isinstance(name, str) or re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', name) is None
            or any(part in ('.', '..') for part in name.split('/'))):
        raise ValueError('Invalid repository-relative preparation source path')
    return name


def _commit_id(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{40}', value) is None:
        raise ValueError('Invalid preparation source commit')
    return value


def _snapshot_file(repo, commit, name):
    _commit_id(commit)
    _repository_path(name)
    try:
        return subprocess.check_output(['git', 'show', commit + ':' + name], cwd=repo, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as error:
        raise ValueError('Preparation source snapshot or file is missing: ' + name) from error


def verify_preparation_sources(manifest_bytes, repo=None):
    """Verify recorded byte hashes against an explicit immutable Git snapshot.

    Only the two byte-pinned legacy manifests may use the later-publication
    exception. Unknown dirty preparations are refused, even if today's files
    happen to match. A clean commit is byte provenance, not proof of when it
    was published. Current working-tree evolution does not affect this check.
    """
    repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[1]
    manifest = json.loads(manifest_bytes)
    recorded = _commit_id(manifest['source_commit'])
    dirty = manifest['source_worktree_dirty']
    if type(dirty) is not bool:
        raise ValueError('Preparation worktree status must be explicit')
    sources = manifest['source_files_sha256']
    if not isinstance(sources, dict) or not sources:
        raise ValueError('Nonempty preparation source inventory required')
    for name, digest in sources.items():
        _repository_path(name)
        if not isinstance(digest, str) or re.fullmatch(r'[0-9a-f]{64}', digest) is None:
            raise ValueError('Invalid preparation source digest')
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    binding = LATER_PUBLISHED_SOURCE_SNAPSHOTS.get(manifest_hash)
    if binding is not None:
        snapshot = _commit_id(binding['commit'])
        published_manifest = _snapshot_file(repo, snapshot, binding['manifest_path'])
        if hashlib.sha256(published_manifest).hexdigest() != manifest_hash:
            raise ValueError('Historical manifest differs from its bound published snapshot')
        basis = 'explicit_manifest_sha256_binding_to_later_published_snapshot'
    else:
        if dirty:
            raise ValueError('Unknown dirty preparation has no verified source snapshot binding')
        snapshot = recorded
        basis = 'recorded_clean_preparation_commit'
    for name, digest in sources.items():
        if hashlib.sha256(_snapshot_file(repo, snapshot, name)).hexdigest() != digest:
            raise ValueError('Preparation source hash mismatch in verified snapshot: ' + name)
    return {
        'recorded_preparation_commit': recorded,
        'recorded_source_worktree_dirty': dirty,
        'verified_source_snapshot': snapshot,
        'source_snapshot_basis': basis,
        'later_publication': binding is not None,
        'prepublication_claimed': False,
        'publication_timing_note': (
            'Source bytes match a later published snapshot; dirty preparation and its recorded commit remain unchanged.'
            if binding is not None else 'Source bytes match the recorded clean commit; publication timing is not inferred.'),
        'source_files_sha256': dict(sorted(sources.items())),
    }


def verify(cfg, tokenizer):
    root = Path(cfg['data_dir'])
    manifest_bytes = (root/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    source_provenance = verify_preparation_sources(manifest_bytes)
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
            'source_provenance': source_provenance,
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
