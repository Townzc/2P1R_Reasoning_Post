"""CPU candidate audit for exact four-arm matching; not a frozen benchmark.

No model outcomes or final test files are read. A restricted, deterministic
search can demonstrate feasibility, but failure is not an impossibility proof.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import itertools
import json
from pathlib import Path
import random

from src.countdown_smoke import canonical, expression, render_trace, solve_all, verify_expression
from src.sft_data import encode_row


def candidate(item):
    numbers, seed = item
    answers = solve_all(list(numbers))
    eligible = []
    for target, trees in sorted(answers.items()):
        if len({canonical(t, structure_only=True) for t in trees}) >= 4:
            eligible.append((target, trees))
    if not eligible:
        return None
    target, trees = random.Random(seed).choice(eligible)
    key = json.dumps([numbers, target], separators=(',', ':'))
    return {'problem_id': hashlib.sha256(key.encode()).hexdigest()[:20],
            'numbers': list(numbers), 'target': target,
            'prompt': f'Use the numbers {", ".join(map(str, numbers))} exactly once each with +, -, *, / and parentheses to make {target}. Show calculations, then write Answer: followed by one expression.',
            'trees': sorted(trees, key=canonical)}


def matching_blocks(inventories, limit, require_muldiv=False):
    """Each key is (response tokens, four complete structure signatures)."""
    support = defaultdict(list)
    for index, inventory in enumerate(inventories):
        for length, by_structure in inventory.items():
            # A declared search cap controls combinatorial cost; no coarsening.
            for structures in itertools.combinations(sorted(by_structure)[:12], 4):
                if require_muldiv and not any('*' in s or '/' in s for s in structures):
                    continue
                support[(length, *structures)].append(index)
    used, blocks = set(), []
    for key, indices in sorted(support.items(), key=lambda item: (-len(item[1]), item[0])):
        available = [i for i in indices if i not in used]
        for start in range(0, len(available)-3, 4):
            chosen = available[start:start+4]
            used.update(chosen)
            blocks.append({'response_tokens': key[0], 'structures': list(key[1:]), 'indices': chosen})
            if len(blocks) == limit:
                return blocks, len(support)
    return blocks, len(support)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--candidates', type=int, default=1024)
    p.add_argument('--blocks', type=int, default=64)
    p.add_argument('--max-number', type=int, default=40)
    p.add_argument('--seed', type=int, default=20260905)
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--require-muldiv', action='store_true',
                   help='Sensitivity audit: require a multiply/divide structure in every selected block')
    a = p.parse_args()
    if min(a.candidates, a.blocks, a.workers) <= 0 or a.max_number < 4:
        p.error('Positive candidate/block/worker counts and at least four numbers are required')
    a.out.mkdir(parents=True, exist_ok=False)
    rng = random.Random(a.seed)
    groups = sorted({tuple(sorted(rng.sample(range(1, a.max_number+1), 4))) for _ in range(a.candidates*3)})
    rng.shuffle(groups)
    groups = groups[:a.candidates]
    if len(groups) != a.candidates:
        raise ValueError('Not enough unique candidate groups')
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        raw = list(pool.map(candidate, [(nums, a.seed+i) for i, nums in enumerate(groups)]))
    problems = [x for x in raw if x is not None]
    from transformers import AutoTokenizer
    lock = json.loads(Path('configs/models.lock.json').read_text())['main']
    tokenizer = AutoTokenizer.from_pretrained(lock['repo_id'], revision=lock['tokenizer_revision'], local_files_only=True)
    inventories = []
    for problem in problems:
        by_length = defaultdict(dict)
        for tree in problem.pop('trees'):
            row = {**problem, 'path_id': canonical(tree), 'structure_id': canonical(tree, structure_only=True),
                   'response': render_trace(tree), 'expression': expression(tree)}
            if not verify_expression(row['expression'], row['numbers'], row['target']):
                raise ValueError('Invalid candidate expression')
            encoded = encode_row(row, tokenizer, 384)
            by_length[encoded['n_supervised']].setdefault(row['structure_id'], row)
        inventories.append(dict(by_length))
    blocks, keys = matching_blocks(inventories, a.blocks, a.require_muldiv)
    chosen = []
    for block in blocks:
        chosen.append({**{k: block[k] for k in ['response_tokens', 'structures']},
                       'problems': [{'problem': problems[i], 'paths': [inventories[i][block['response_tokens']][s] for s in block['structures']]}
                                    for i in block['indices']]})
    encoded_blocks = json.dumps(chosen, sort_keys=True, separators=(',', ':'))
    (a.out/'candidate_blocks.json').write_text(json.dumps(chosen, indent=2)+'\n')
    update_checks, surface_distinct = [], []
    for block in chosen:
        for update in range(4):
            arms = {'paths': [], 'gcm': [], 'repeat': [], 'surface': []}
            for i, problem in enumerate(block['problems']):
                anchor = problem['paths'][0]
                surface = {**anchor, 'response': anchor['response'].replace('Step ', ['Step ', 'Stage ', 'Part ', 'Line '][update])}
                arms['paths'].append(problem['paths'][(i+update) % 4])
                arms['gcm'].append(problem['paths'][i])
                arms['repeat'].append(anchor)
                arms['surface'].append(surface)
            totals = {name: sum(encode_row(row, tokenizer, 384)['n_supervised'] for row in rows) for name, rows in arms.items()}
            hist = {name: Counter(row['structure_id'] for row in rows) for name, rows in arms.items()}
            equal = len(set(totals.values())) == 1 and hist['paths'] == hist['gcm']
            update_checks.append({'supervised_tokens': totals, 'exact_match': equal})
        for problem in block['problems']:
            text = problem['paths'][0]['response']
            surface_distinct.append(len({text.replace('Step ', name) for name in ['Step ', 'Stage ', 'Part ', 'Line ']}) == 4)
    selected = [p['problem'] for b in chosen for p in b['problems']]
    record = {'status': 'CPU_CANDIDATE_AUDIT_ONLY_NOT_REVIEWED_OR_FROZEN', 'seed': a.seed,
              'git_commit': __import__('subprocess').check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'domain': {'distinct_inputs': 4, 'min_number': 1, 'max_number': a.max_number, 'target_min': 10, 'target_max': 100},
              'candidate_groups': len(raw), 'eligible_groups': len(problems), 'matching_keys_searched': keys,
              'require_multiply_or_divide_per_block': a.require_muldiv,
              'requested_blocks': a.blocks, 'selected_blocks': len(chosen), 'selected_problems': len(selected),
              'selection_fraction': len(selected)/len(raw), 'all_updates_exact': bool(chosen) and all(x['exact_match'] for x in update_checks),
              'distinct_surface_responses': bool(chosen) and all(surface_distinct),
              'selected_target_histogram': dict(sorted(Counter(x['target'] for x in selected).items())),
              'candidate_target_histogram': dict(sorted(Counter(x['target'] for x in problems).items())),
              'model': {'repo_id': lock['repo_id'], 'tokenizer_revision': lock['tokenizer_revision']},
              'candidate_blocks_canonical_sha256': hashlib.sha256(encoded_blocks.encode()).hexdigest(),
              'update_checks': update_checks,
              'limitations': ['Restricted to the first 12 sorted full structures at each token length; failure would not prove impossibility.',
                             'Each candidate uses one seeded eligible target; the shared-inventory selection changes the task distribution.',
                             'Surface variants change only the step label, a weak rendering control requiring review.',
                             'Exact supervised-token and global-structure matching does not match padding, FLOPs, or cognitive strategies.',
                             'No development/holdout split or scientific training is launched by this audit.']}
    (a.out/'audit.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k: record[k] for k in ['selected_blocks', 'selected_problems', 'all_updates_exact', 'distinct_surface_responses']}))


if __name__ == '__main__':
    main()
