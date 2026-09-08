"""CPU-only, immutable preparation. Reserve holdout groups without solving them."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import subprocess

from scripts.audit_exact_matching import candidate, matching_blocks
from src.countdown_smoke import canonical, expression, render_trace
from src.pilot_data import allocate_groups, make_arms, paired_schedule, audit_arms, canonical_hash, surface_response
from src.sft_data import encode_row, sha256_file


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2) + '\n')


def jsonl(path, rows):
    with Path(path).open('x') as f:
        for r in rows:
            f.write(json.dumps(r, separators=(',', ':')) + '\n')


def build_split(groups, seed, block_count, tokenizer, workers, name):
    with ProcessPoolExecutor(max_workers=workers) as pool:
        raw = list(pool.map(candidate, [(nums, seed+i) for i, nums in enumerate(groups)], chunksize=8))
    problems = [p for p in raw if p is not None]
    inventories = []
    for p in problems:
        inventory = defaultdict(dict)
        for tree in p.pop('trees'):
            row = dict(p, path_id=canonical(tree), structure_id=canonical(tree, structure_only=True),
                       response=render_trace(tree), expression=expression(tree))
            length = encode_row(row, tokenizer, 384)['n_supervised']
            # Every retained anchor supports all four richer surface strings exactly.
            if any(encode_row(dict(row, response=surface_response(row['response'], v)), tokenizer, 384)['n_supervised'] != length for v in range(1, 4)):
                continue
            inventory[length].setdefault(row['structure_id'], row)
        inventories.append(dict(inventory))
    matches, keys = matching_blocks(inventories, block_count, require_muldiv=True)
    if len(matches) != block_count:
        raise RuntimeError(f'{name}: only {len(matches)}/{block_count} blocks; no automatic domain relaxation')
    blocks = [dict(response_tokens=b['response_tokens'], structures=b['structures'],
                   problems=[{'problem': problems[i], 'paths': [inventories[i][b['response_tokens']][s] for s in b['structures']]}
                             for i in b['indices']]) for b in matches]
    selected = [p['problem'] for b in blocks for p in b['problems']]
    raw_hist, chosen_hist = Counter(p['target'] for p in problems), Counter(p['target'] for p in selected)
    tv = .5 * sum(abs(raw_hist[t]/len(problems)-chosen_hist[t]/len(selected)) for t in set(raw_hist)|set(chosen_hist))
    audit = {'allocated_groups': len(groups), 'eligible_groups': len(problems), 'selected_groups': len(selected),
             'selection_fraction': len(selected)/len(groups), 'target_tv_selected_vs_eligible': tv,
             'candidate_target_histogram': dict(raw_hist), 'selected_target_histogram': dict(chosen_hist),
             'matching_keys': keys, 'first_structures_per_length_cap': 12, 'require_muldiv_per_block': True}
    print(json.dumps({'split': name, **{k: audit[k] for k in ['eligible_groups', 'selected_groups', 'selection_fraction']}}), flush=True)
    return blocks, audit, problems, inventories


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--workers', type=int, default=6)
    p.add_argument('--seed', type=int, default=20260908)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    sources = [Path('scripts/prepare_pilot.py'), Path('src/pilot_data.py'), Path('scripts/audit_exact_matching.py'), Path('src/countdown_smoke.py'), Path('src/sft_data.py')]
    source_hashes = {str(p): sha256_file(p) for p in sources}
    source_dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip())
    groups = allocate_groups(a.seed, {'train': 4096, 'dev': 2048, 'holdout_reserved': 2048})
    dump(a.out/'split_allocation.json', {'seed': a.seed, 'groups': groups, 'stage': 'before_solving_or_augmentation'})
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(a.tokenizer_dir, local_files_only=True)
    lock = json.loads(Path('configs/models.lock.json').read_text())['main']
    expected = next(f['blobId'] for f in lock['files'] if f['rfilename'] == 'tokenizer.json')
    content = (Path(a.tokenizer_dir)/'tokenizer.json').read_bytes()
    import hashlib
    digest = hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
    if digest != expected:
        raise ValueError('Tokenizer does not match the pinned official Git blob')
    train, train_audit, _, _ = build_split(groups['train'], a.seed, 64, tokenizer, a.workers, 'train')
    dump(a.out/'train_blocks.json', train)
    dump(a.out/'train_selection_audit.json', train_audit)
    dev, dev_audit, problems, inventories = build_split(groups['dev'], a.seed+100000, 16, tokenizer, a.workers, 'dev')
    dump(a.out/'dev_blocks.json', dev)
    dev_rows = [p['paths'][0] for b in dev for p in b['problems']]
    selected_ids = {r['problem_id'] for r in dev_rows}
    broad = []
    for problem, inventory in zip(problems, inventories):
        if problem['problem_id'] not in selected_ids and inventory:
            length = min(inventory)
            broad.append(inventory[length][min(inventory[length])])
            if len(broad) == 64:
                break
    if len(broad) != 64:
        raise ValueError('Insufficient broader development references')
    jsonl(a.out/'dev_matched.jsonl', dev_rows)
    jsonl(a.out/'dev_broad.jsonl', broad)
    rows = make_arms(train, seed=17)
    schedule = paired_schedule(len(train), cycles=4, seed=17)
    for arm, values in rows.items():
        jsonl(a.out/f'train_{arm}.jsonl', values)
    dump(a.out/'schedule_seed17.json', schedule)
    audit = audit_arms(rows, schedule, tokenizer)
    dump(a.out/'matching_audit.json', audit)
    manifest = {'schema_version': 1, 'status': 'FROZEN_PILOT_V1_NO_MODEL_OUTCOMES', 'seed': a.seed,
                'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'source_files_sha256': source_hashes, 'source_worktree_dirty': source_dirty,
                'model': {'repo_id': lock['repo_id'], 'tokenizer_revision': lock['tokenizer_revision'], 'tokenizer_git_blob': digest},
                'splits': {'train': train_audit, 'dev_matched': dev_audit, 'dev_broad': {'groups': len(broad), 'interpretation': 'first eligible unselected dev groups; not an IID or OOD guarantee'},
                           'holdout': {'reserved_raw_groups': 2048, 'solved': False, 'model_evaluated': False, 'selection_rule': 'same frozen candidate and block algorithm; not materialized by this entry point'}},
                'group_disjoint_before_augmentation': True, 'paired_seed': 17, 'cycles': 4,
                'schedule_canonical_sha256': canonical_hash(schedule),
                'limitations': ['Shared-structure selection defines a restricted task distribution.', 'Surface changes sentence frames, not the arithmetic program or equation order.', 'No compositional OOD or multi-seed inference.', 'Holdout reservation is logical sealing; public group IDs are not access control.']}
    manifest['files_sha256'] = {f.name: sha256_file(f) for f in sorted(a.out.iterdir()) if f.is_file()}
    if source_hashes != {str(p): sha256_file(p) for p in sources}:
        raise RuntimeError('Preparation source changed during execution')
    dump(a.out/'manifest.json', manifest)
    print(json.dumps({'status': manifest['status'], 'budget_per_arm': {k: audit['arms']['paths'][k] for k in ['optimizer_updates', 'supervised_response_tokens', 'presentations']}}))


if __name__ == '__main__':
    main()
