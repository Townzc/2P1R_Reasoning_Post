"""Exploratory reward-switch diagnostic on published training rolls, not training.

Only JSON is read. No candidate program, model, evaluator, or reference is run.
Reward on a base failure is zero under either rule; missing extra scores for a
base PASS invalidate the record rather than becoming negative supervision.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def load_joined(path, expected_seed):
    rolls, extra = {}, {}
    with Path(path).open() as f:
        for lineno, line in enumerate(f, 1):
            row = json.loads(line)
            if row.get('seed') != expected_seed or row.get('arm') != 'leaky':
                raise ValueError(f'wrong run identity at line {lineno}')
            kind = row.get('kind')
            if kind not in ('roll', 'plus'):
                raise ValueError(f'unknown record kind {kind}')
            dest = rolls if kind == 'roll' else extra
            uid = row['uid']
            if uid in dest:
                raise ValueError(f'duplicate {kind} uid {uid}')
            dest[uid] = row
    if not rolls or set(extra) - set(rolls):
        raise ValueError('empty rolls or orphan extra verdict')
    joined = []
    for uid, row in rolls.items():
        if row.get('scoring_error') or type(row.get('base')) is not bool:
            raise ValueError(f'invalid base verdict {uid}')
        e = extra.get(uid)
        if e and e.get('run_gen') != row.get('run_gen'):
            raise ValueError('cross-generation join')
        if row['base']:
            if e is None or type(e.get('plus')) is not bool:
                raise ValueError(f'unresolved extra verdict {uid}')
            union = e['plus']
        else:
            if e is not None:
                raise ValueError('unexpected extra event on rejected base')
            union = False  # conjunction is known; extra pass/fail itself is unknown
        joined.append(dict(row, union=union))
    return joined, {'roll_records': len(rolls), 'extra_records': len(extra),
                    'base_pass_extra_complete': True}


def grouped(rows, group_size=8):
    calls = defaultdict(list)
    for r in rows:
        calls[(r['run_gen'], r['call'])].append(r)
    groups = []
    for _, batch in sorted(calls.items()):
        batch.sort(key=lambda r: int(r['uid'].rsplit('-', 1)[1]))
        indexes = [int(r['uid'].rsplit('-', 1)[1]) for r in batch]
        if indexes != list(range(len(batch))) or len(batch) != 2 * group_size:
            raise ValueError('incomplete/nonstandard generation batch')
        if len({r['gstep'] for r in batch}) != 1:
            raise ValueError('mixed policy step in batch')
        for start in range(0, len(batch), group_size):
            group = batch[start:start+group_size]
            if len({r['task_id'] for r in group}) != 1:
                raise ValueError('cannot identify contiguous task group')
            groups.append(group)
    return groups


def center_signs(values):
    n, total = len(values), sum(values)
    return tuple((n*v > total) - (n*v < total) for v in values)


def summarize(rows, groups):
    flips = [r for r in rows if r['base'] and not r['union']]
    by_task = Counter(r['task_id'] for r in flips)
    table = Counter()
    changed, signs_changed = 0, 0
    for g in groups:
        b = [int(r['base']) for r in g]
        u = [int(r['union']) for r in g]
        def status(v):
            return 'all_fail' if sum(v) == 0 else 'all_pass' if sum(v) == len(v) else 'mixed'
        table[status(b)+' -> '+status(u)] += 1
        changed += b != u
        signs_changed += center_signs(b) != center_signs(u)
    n = len(rows)
    bp = sum(r['base'] for r in rows)
    return {'rollouts': n, 'groups': len(groups), 'tasks': len({r['task_id'] for r in rows}),
            'base_pass': bp, 'union_pass': sum(r['union'] for r in rows),
            'reward_flips': len(flips), 'flip_fraction_all': len(flips)/n,
            'flip_fraction_base_pass': len(flips)/bp if bp else None,
            'tasks_with_flip': len(by_task),
            'top10_tasks_share_of_flips': sum(v for _,v in by_task.most_common(10))/len(flips) if flips else None,
            'groups_reward_vector_changed': changed,
            'groups_centered_reward_sign_changed': signs_changed,
            'group_transition_counts': dict(sorted(table.items()))}


def analyze(paths, train_ids):
    result = []
    all_rows, all_groups = [], []
    for seed, path in enumerate(paths):
        rows, checks = load_joined(path, seed)
        if {r['task_id'] for r in rows} - set(train_ids):
            raise ValueError('unexpected non-training task')
        if len(rows) != 6400 or sorted({r['gstep'] for r in rows}) != list(range(400)):
            raise ValueError('not the declared complete 400-update public run')
        groups = grouped(rows)
        by_window = {}
        for lo, hi in ((0,64), (64,128), (128,400), (0,400)):
            subset = [r for r in rows if lo <= r['gstep'] < hi]
            gs = [g for g in groups if lo <= g[0]['gstep'] < hi]
            by_window[f'{lo}:{hi}'] = summarize(subset,gs)
        b = Path(path).read_bytes()
        result.append({'seed':seed, 'sha256':hashlib.sha256(b).hexdigest(),
                       'checks':checks, 'windows':by_window})
        all_rows.extend(rows); all_groups.extend(groups)
    return {'analysis':'exploratory deterministic replay of rewards on published base-trained rollouts',
            'source_model':'Qwen2.5-Coder-1.5B-Instruct',
            'source_commit':'9b6c86abeb4b837418b009d5354f81b43a28f84b',
            'new_model_generations':0, 'new_optimizer_updates':0,
            'new_candidate_program_executions':0,
            'seed_results':result, 'pooled':summarize(all_rows,all_groups),
            'limits':['No stricter-policy rollouts or new training are simulated.',
                      'Base and extra verdicts are author-reported, not independently re-executed.',
                      'Suite rejection is not semantic ground truth.',
                      'Centered-reward signs are not parameter gradients or an effect estimate.',
                      'No rollout-iid inferential intervals; five runs and repeated tasks are dependent.',
                      'Training tasks only; no new held-out benchmark exposure.',
                      'Source logs truncate code; do not use these copies as exact-code rerun artifacts.']}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--sources',type=Path,required=True)
    p.add_argument('--split',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise FileExistsError('refusing to overwrite prior analysis')
    sp=json.loads(a.split.read_text())
    result=analyze([a.sources/f'runs__grid__leaky_s{s}__rollout_scores.jsonl' for s in range(5)],sp['train_ids'])
    result['split_sha256']=hashlib.sha256(a.split.read_bytes()).hexdigest()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result['pooled'],indent=2))

if __name__=='__main__':main()
