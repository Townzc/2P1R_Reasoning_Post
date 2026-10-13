"""Pure restoration of the fully reconciled D2 prefix, not a run admission.

This narrow version accepts only a clean round boundary with all original
physical returns and wallet completions present. It never synthesizes output,
changes a label or authorizes a model call. Exact immutable source/input binding
and an externally reviewed finite child would be required separately.
"""
from collections import defaultdict
from .contract import stable_seed


def restore(wallets, cache, events, states, reconciliation):
    if (not reconciliation.get('passed') or reconciliation.get('physical_raw_unknown') != 0
            or reconciliation.get('pending_wallets') or reconciliation.get('unattempted_pending_candidate_ids')
            or reconciliation.get('parent_terminal', {}).get('status') != 'failed'):
        raise ValueError('Only fully reconciled failed-parent clean boundary')
    names = {w.name for w in wallets}
    if len(names) != 8 or names != set(events) or names != set(states) or any(w.draw != 2 for w in wallets):
        raise ValueError('Original eight D2 wallets required')
    if not 0 < len(cache) == reconciliation['physical_attempts'] <= 16384:
        raise ValueError('Original physical count changed')
    seen = defaultdict(dict); accepted = defaultdict(dict); counts = defaultdict(int)
    for cid,row in sorted(cache.items(),key=lambda x:(x[1]['problem_id'],x[1]['attempt'])):
        pid = row['problem_id']; attempt = row['attempt']
        if (cid != f'd2::{pid}::{attempt}' or row['candidate_id'] != cid or row['draw'] != 2
                or attempt != counts[pid]+1 or not 1 <= attempt <= 8
                or row['seed'] != stable_seed('teacher',2,pid,attempt)
                or type(row['usable']) is not bool or not 0 < row['completion_tokens'] <= 1024
                or row['completion_tokens'] != row['stop']['token_count']):
            raise ValueError('Original identity, attempt prefix, label or token count changed')
        counts[pid] += 1
        seen[pid].setdefault(row['normalized_text_sha256'],cid)
        if row['usable']:accepted[pid].setdefault(row['normalized_text_sha256'],cid)
    returned = sum(row['completion_tokens'] for row in cache.values())
    if returned != reconciliation['returned_tokens']:
        raise ValueError('Original token count changed')
    consumed = set()
    for w in wallets:
        if w.pending is not None or w.settlements or w.consumed:
            raise ValueError('Restoration may run only on pristine wallets')
        for event in events[w.name]:
            intent = event['intent']; done = event['done']
            if done is None or w.propose() != intent:
                raise ValueError('Pending or altered original action')
            w.begin(intent)
            ids = [f"d2::{x['problem_id']}::{x['attempt']}" for x in intent['action']['items']]
            if any(cid not in cache for cid in ids):
                raise ValueError('Missing original return; never regenerate')
            if w.settle([cache[cid] for cid in ids]) != done:
                raise ValueError('Original charge changed')
            consumed.update(ids)
        proposal = w.propose()
        if states[w.name] != dict(summary=w.summary(),published_pending=None,next_proposal=proposal):
            raise ValueError('Original end state changed')
    if consumed != set(cache):
        raise ValueError('Foreign/unconsumed original output')
    unfinished = sorted(w.name for w in wallets if w.propose() is not None)
    if unfinished != sorted(reconciliation['unfinished_wallets']):
        raise ValueError('Remaining wallet set changed')
    return dict(cache=dict(cache),seen=seen,accepted=accepted,
                batch_index=reconciliation['physical_batches'],attempted=len(cache),
                returned_tokens=returned,events=defaultdict(list,{k:list(v) for k,v in events.items()}))
