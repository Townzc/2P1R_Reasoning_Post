"""Claude independent replay of reports/p007_audit/token_tariff_v1 (does not import token_contract)."""
import json, sys, collections
from fractions import Fraction
R = sys.argv[1].rstrip('/') + '/'
P = json.load(open(R + 'prefix_simulation.json'))
A = {(a['cell'], a['candidate_id']): a for a in map(json.loads, open('reports/p007_audit/policy_all_v1/attempts.jsonl'))}
plen = P['prompt_lengths']
cap = Fraction(211257)
mean = Fraction(191151, 512)
assert mean == Fraction(373341796875, 10**9)
out = {}
for cell in ['breadth_p0', 'depth_p0', 'breadth_p4', 'depth_p4']:
    tr = json.load(open(R + f'{cell}_trace.json'))
    # cross-check trace rows against the earlier audited all-cell packet
    mism = 0
    for b in tr:
        for x in b:
            a = A[(cell, x['candidate_id'])]
            if a['usable'] != x['usable'] or a['text_token_count'] + (1 if a['eos'] else 0) != x['stop']['token_count'] or a['batch_id'] != x['batch_id']:
                mism += 1
            if plen[x['problem_id']] != x['prompt_tokens']: mism += 1
    price = 4 * mean if cell.endswith('p4') else Fraction(0)
    target = 1 if cell.startswith('breadth') else 4
    # own policy: active parents (frozen order of first appearance), retire by own counters
    order = []
    for b in tr:
        for x in b:
            if x['attempt'] == 1 and x['problem_id'] not in order: order.append(x['problem_id'])
    spent = Fraction(0); seen = set(); nb = 0; used = []
    for b in tr:
        new = [x['problem_id'] for x in b if x['attempt'] == 1]
        reserve = price * len(new) + sum(plen[x['problem_id']] for x in b) + 16 * 1024
        if len(b) != 16 or spent + reserve > cap: break
        spent += price * len(new) + sum(x['prompt_tokens'] + x['stop']['token_count'] for x in b)
        used += b; nb += 1
    us = [x for x in used if x['usable']]
    sim = P['cells'][cell]
    L = sum(A[(cell, x['candidate_id'])]['text_token_count'] + 1 for x in us)
    out[cell] = dict(trace_vs_audited_packet_mismatches=mism, batches=nb, attempts=len(used), usable=len(us),
                     parents_with_usable=len({x['problem_id'] for x in us}), charge=float(spent),
                     unused=round(float((cap - spent) / cap), 4),
                     matches_packet=[x['candidate_id'] for x in used] == sim['accepted_candidates'],
                     exposures_per_pair=round(524287 / L, 2))
print(json.dumps(out, indent=1))
