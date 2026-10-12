"""Explicit P007B known-output recovery; never invent an original settlement."""
from collections import defaultdict
from .policy_contract import Policy
from .wallet import Wallet
from experiments.sft_allocation_midpoint.common import read,verify,digest


def restore(prefix, parent_root, ordered_ids):
    if (prefix['status']!='interrupted_prefix_verified_not_completed' or prefix['unknown']!=0
            or prefix['next_batch_index']!=12 or prefix['raw_outputs_verified']!=192):
        raise ValueError('Only the independently verified known prefix is admissible')
    verify(parent_root,prefix['observed_manifest'])
    cfg=prefix['config'];policy=Policy(ordered_ids,cfg['target_usable'])
    records=[];seen=defaultdict(dict);eligible=defaultdict(dict)
    for i in range(prefix['next_batch_index']):
        name=f'batch_{i:04d}';intent=read(parent_root/'intents'/f'{name}.json')
        proposal=intent['proposal'];policy.begin(name,proposal)
        scored=read(parent_root/'scored'/f'{name}.json')
        if any(type(x['usable']) is not bool for x in scored):raise ValueError('Unknown return cannot be replayed or imputed')
        policy.complete(name,scored);records.extend(scored)
        for x in scored:
            seen[x['problem_id']].setdefault(x['normalized_text_sha256'],x['candidate_id'])
            if x['usable']:eligible[x['problem_id']].setdefault(x['normalized_text_sha256'],x['candidate_id'])
    if (policy.ordered_ids[:policy.cursor]!=prefix['acquired_ids'] or policy.records!=prefix['parent_outcomes']
            or policy.active!=prefix['active_parents']):raise ValueError('Rebuilt roster differs')
    wallet=Wallet(cfg['cap_nanodollars'],cfg['hourly_nanodollars'],cfg['problem_nanodollars'],prefix['original_active_start_ns'])
    wallet.acquired=set(prefix['acquired_ids']);wallet.attempted_batches=set(policy.attempted_batches)
    if wallet.spent(prefix['charged_end_ns'])!=prefix['charged_spent_nanodollars']:
        raise ValueError('Conservative charge does not carry forward')
    if prefix['charged_last_action_seconds']<cfg['max_action_seconds']:
        raise ValueError('Failed action cannot receive a cost discount')
    return policy,wallet,seen,eligible,records
