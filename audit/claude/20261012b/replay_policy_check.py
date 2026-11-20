"""Claude: replay saved P007B traces through the frozen Policy class and compare each saved
batch's new purchases with the available room; then compute per-pair exposure of the
token-priced candidate corpora at the proposed 524,287 targets. Read-only, CPU only.
Run from repo root at commit 36bfa8c5."""
import json, sys, itertools
sys.path.insert(0, '.')
from experiments.sft_allocation_acquisition.policy_contract import Policy
A = [json.loads(l) for l in open('reports/p007_audit/policy_all_v1/attempts.jsonl')]
B = json.load(open('reports/p007_audit/policy_all_v1/batches.json'))
T = json.load(open('reports/p007_audit/cost_metric_review_v1/token_candidate.json'))
idx = {(a['cell'], a['candidate_id']): a for a in A}
for cell in ['breadth_p0', 'depth_p0', 'breadth_p4', 'depth_p4']:
    rows = [a for a in A if a['cell'] == cell]
    groups = [list(g) for _, g in itertools.groupby(rows, key=lambda a: a['batch_id'])]
    bs = [b for b in B if b['cell'] == cell]
    order = [p for b in bs for p in b['settlement'].get('new_problem_ids', [])]
    pol = Policy(order + [f'pad{i}' for i in range(1024 - len(order))], 1 if cell.startswith('breadth') else 4)
    nb = T['candidate'][cell]['batches']
    short = []
    for i, (b, xs) in enumerate(zip(bs[:nb], groups[:nb])):
        new = b['settlement'].get('new_problem_ids', [])
        room = min(16 - len(pol.active), len(pol.ordered_ids) - pol.cursor)
        prop = pol.propose(len(new))
        assert [(r['problem_id'], r['attempt']) for r in prop['items']] == [(x['problem_id'], x['attempt']) for x in xs]
        if len(new) < room: short.append(i)
        pol.begin(f'b{i}', prop)
        pol.complete(f'b{i}', [dict(problem_id=x['problem_id'], attempt=x['attempt'], usable=x['usable']) for x in xs])
    c = T['candidate'][cell]
    us = [idx[(cell, x)] for x in c['accepted_candidates'] if idx[(cell, x)]['usable']]
    L = sum(r['text_token_count'] + 1 for r in us)
    print(cell, dict(candidate_batches=nb, batches_with_purchases_below_room=short, usable=len(us),
                     unused=round(c['unused'], 4), exposures_per_pair_at_524287=round(524287 / L, 2)))
