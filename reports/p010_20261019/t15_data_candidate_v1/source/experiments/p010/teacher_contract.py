"""P010 teacher selection, exact request identities and finite admission math."""
import hashlib
import math
from decimal import Decimal
from experiments.p010.common import MODELS, budget_check, digest

SYSTEM = r'Please reason step by step, and put your final answer within \boxed{}.'
SLOTS = {
    't15': dict(seconds=3600, gpus=1, cpu=4, memory_gib=32, reserve='5.50', prior='1.00'),
    't7': dict(seconds=5400, gpus=1, cpu=4, memory_gib=32, reserve='8.00', prior='6.50'),
    't72': dict(seconds=4500, gpus=4, cpu=8, memory_gib=64, reserve='24.00', prior='14.50'),
}


def seed_for(candidate):
    return int(hashlib.sha256(('p009-math-teacher-seed17:'+candidate).encode()).hexdigest()[:16],16) % 2**31


def sampling(row):
    return dict(n=1,temperature=.8,top_p=.95,top_k=-1,repetition_penalty=1.,
        max_tokens=1024,seed=row['seed'],stop=None,stop_token_ids=[151645,151643],
        ignore_eos=False,detokenize=True,skip_special_tokens=False,include_stop_str_in_output=True)


def rate(model):
    s=SLOTS[model]
    return s['gpus']*.001097+s['cpu']*.0000131+s['memory_gib']*.00000222


def bounded_forecast(model, elapsed, batch_seconds, remaining_batches):
    """All measured full batches; 20% margin and300s uncalibrated closing allowance.

    Only an initial paid measurement batch is exempt from extrapolation. The
    worker hard timer and monetary reserve apply from entry, including setup.
    This is an engineering scenario, not a host bound or probability claim.
    """
    if not batch_seconds or any(not math.isfinite(v) or v<=0 for v in batch_seconds):
        raise ValueError('No valid measured full-batch cost')
    future=1.2*(max(batch_seconds)*remaining_batches+300)
    total=elapsed+future
    cost=(total+600)*rate(model)
    if total>SLOTS[model]['seconds']-15:
        raise TimeoutError('Observed batch scenario exceeds original worker window')
    budget=budget_check('G',SLOTS[model]['prior'],SLOTS[model]['reserve'],cost)
    return dict(elapsed_seconds=elapsed,remaining_batches=remaining_batches,
        maximum_observed_full_batch_seconds=max(batch_seconds),future_seconds=future,
        projected_usd=cost,budget=budget,allowance_calibrated=False)


def canonical_request(pid,attempt,model,prompt_ids):
    cid=f'{pid}::attempt{attempt:02d}'
    if not 1<=attempt<=16 or model not in SLOTS or len(prompt_ids)+1024>2048:
        raise ValueError('Request outside frozen scope/context')
    return dict(candidate_id=cid,problem_id=pid,attempt=attempt,model=model,
        seed=seed_for(cid),prompt_token_ids=list(prompt_ids))


def validate_queue(rows,model):
    ids=set()
    for r in rows:
        wanted=canonical_request(r['problem_id'],r['attempt'],model,r['prompt_token_ids'])
        if any(r[k]!=v for k,v in wanted.items()) or r['candidate_id'] in ids:
            raise ValueError('Duplicate/foreign request or wrong frozen seed')
        ids.add(r['candidate_id'])
    return ids


def first_usable(pid,records):
    for attempt in range(1,5):
        item=records.get(f'{pid}::attempt{attempt:02d}')
        if item and item['usable']: return item
    return None
