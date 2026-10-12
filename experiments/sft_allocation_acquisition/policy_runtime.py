"""Execute a finite *actual* procurement wallet, never a prorated pilot tape.

No dispatch or recovery here. Each batch has an immutable intent before generate.
A hard wall-time watchdog preserves ambiguous attempts instead of resampling them.
The common wallet counts problem purchases and continuous active host time.
"""
from collections import defaultdict
import hashlib
import importlib.metadata
import json
import os
import threading
import time

from experiments.sft_allocation_midpoint.common import dump, read, sha, verify
from .contract import SAMPLING, REVISION, messages, completion, assess
from .policy_contract import Policy
from .wallet import Wallet


def choose_action(policy, wallet, batch_id, now_ns, max_action_ns):
    """Largest affordable number of new parents in the frozen order, no outcomes."""
    full = policy.propose()
    for count in range(len(full['new_problem_ids']), -1, -1):
        proposal = policy.propose(count)
        if not proposal['items']:
            continue
        reservation = wallet.admit(batch_id, proposal['new_problem_ids'], now_ns, max_action_ns)
        if reservation is not None:
            policy.begin(batch_id, proposal)
            return proposal, reservation
    return None


def run(teacher_assets, inputs, out, journal, config):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    expected = {'torch':'2.8.0+cu128','transformers':'4.56.2',
                'tokenizers':'0.22.1','numpy':'2.3.2'}
    actual = {k:importlib.metadata.version(k) for k in expected}
    if actual != expected or not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError('Pinned single GPU runtime differs')
    gpu = torch.cuda.get_device_properties(0)
    if 'H100' not in gpu.name or gpu.total_memory < 75*2**30:
        raise ValueError('Expected an H10080GB')
    dump(out/'environment.json', dict(versions=actual,gpu=gpu.name,memory_bytes=gpu.total_memory,
         torch_cuda=torch.version.cuda,parameter_dtype='bfloat16',attention='sdpa'))
    verify(inputs, read(inputs/'manifest.json')['files'])
    parents = [json.loads(s) for s in (inputs/'fresh_parents.jsonl').read_text().splitlines()]
    if len(parents) != 1024 or len({p['group_id'] for p in parents}) != 1024:
        raise ValueError('Fresh parent pool differs')
    lookup = {p['id']:p for p in parents}
    source = read(teacher_assets/'result.json')
    if source['model_revision'] != REVISION:
        raise ValueError('Teacher revision differs')
    verify(teacher_assets, source['files'])
    tick = time.monotonic_ns()
    tok = AutoTokenizer.from_pretrained(teacher_assets/'model',local_files_only=True,
                                       padding_side='left',trust_remote_code=False)
    tok.pad_token_id = SAMPLING['pad_token_id']
    model = AutoModelForCausalLM.from_pretrained(teacher_assets/'model',local_files_only=True,
        trust_remote_code=False,torch_dtype=torch.bfloat16,attn_implementation='sdpa').cuda().eval()
    prompts = {p['id']:tok.apply_chat_template(messages(p),tokenize=False,add_generation_prompt=True)
               for p in parents}
    lengths = {k:len(tok.encode(v,add_special_tokens=False)) for k,v in prompts.items()}
    if max(lengths.values())+SAMPLING['max_new_tokens'] > 4096:
        raise ValueError('Untruncated input exceeds context')
    dump(out/'prompt_manifest.json', {p:dict(sha256=hashlib.sha256(v.encode()).hexdigest(),tokens=lengths[p])
                                     for p,v in prompts.items()})
    journal.commit()
    setup_ns = time.monotonic_ns()-tick
    policy = Policy([p['id'] for p in parents], config['target_usable'])
    wallet = Wallet(config['cap_nanodollars'], config['hourly_nanodollars'],
                    config['problem_nanodollars'], time.monotonic_ns())
    seen, usable_seen = defaultdict(dict), defaultdict(dict)
    records, settlements = [], []
    max_action_ns = config['max_action_seconds']*10**9
    stopped = None
    for index in range(config['max_batches']):
        journal.check()
        name = f'batch_{index:04d}'
        now = time.monotonic_ns()
        action = choose_action(policy,wallet,name,now,max_action_ns)
        if action is None:
            stopped = 'wallet_cannot_reserve_next_bounded_action' if policy.propose()['items'] else 'pool_exhausted'
            break
        proposal, reservation = action
        # The watchdog includes prompt packing, remote intent, generation, scoring,
        # durable raw/scored evidence and settlement. On expiry do not invent scores.
        timer = threading.Timer(max(0, (reservation['deadline_ns']-time.monotonic_ns())/1e9),
                                lambda:os._exit(124))
        timer.daemon = True
        timer.start()
        try:
            items = [dict(**r,candidate_id=f"{r['problem_id']}::attempt{r['attempt']:02d}")
                     for r in proposal['items']]
            seed = config['sampling_seed']+index
            packed = tok([prompts[r['problem_id']] for r in items],return_tensors='pt',
                         padding=True,truncation=False,add_special_tokens=False).to('cuda')
            prefix = packed['input_ids'].cpu().tolist()
            width = packed['input_ids'].shape[1]
            intent = dict(batch_id=name,items=items,seed=seed,sampling=SAMPLING,
                proposal=proposal,reservation=reservation,active_start_ns=wallet.start_ns,
                prompt_token_ids=prefix,attention_mask=packed['attention_mask'].cpu().tolist(),
                started_epoch=time.time())
            journal.begin(name,intent)
            journal.commit()
            torch.manual_seed(seed)
            torch.cuda.synchronize()
            tick = time.monotonic_ns()
            with torch.inference_mode(): returned = model.generate(**packed,**SAMPLING,use_cache=True)
            torch.cuda.synchronize()
            generation_ns = time.monotonic_ns()-tick
            tokens = returned.cpu().tolist()
            if len(tokens) != len(items) or any(t[:width] != p for t,p in zip(tokens,prefix)):
                raise ValueError('Backend changed prompt or roster')
            raw = dict(batch_id=name,items=items,batch_output_ids=tokens,prompt_width=width,
                       generation_ns=generation_ns,returned_epoch=time.time())
            rawfile = out/'raw'/f'{name}.json'
            dump(rawfile,raw)
            journal.commit()
            tick = time.monotonic_ns()
            scored = []
            for item, ids in zip(items,tokens):
                pid = item['problem_id']
                stop = completion(ids[width:])
                text = tok.decode(stop['text_token_ids'],skip_special_tokens=False)
                judgement = assess(lookup[pid],text,stop,seen[pid],usable_seen[pid])
                row = dict(**item,text=text,stop=stop,**judgement,prompt_tokens=lengths[pid],
                           batch_id=name,batch_size=len(items))
                seen[pid].setdefault(judgement['normalized_text_sha256'],item['candidate_id'])
                if judgement['usable']:
                    usable_seen[pid].setdefault(judgement['normalized_text_sha256'],item['candidate_id'])
                scored.append(row)
            checker_ns = time.monotonic_ns()-tick
            scorefile = out/'scored'/f'{name}.json'
            dump(scorefile,scored)
            journal.commit()
            policy.complete(name,scored)
            done = dict(count=len(items),candidate_ids=[r['candidate_id'] for r in scored],
                raw_sha256=sha(rawfile),scored_sha256=sha(scorefile),generation_ns=generation_ns,
                checker_ns=checker_ns,usable=sum(r['usable'] for r in scored))
            journal.end(name,done)
            journal.commit()
            # End of durable scientific action; all intervening activity is charged.
            settlement = wallet.settle(name,time.monotonic_ns())
        finally:
            timer.cancel()
        dump(out/'settlements'/f'{name}.json',settlement)
        journal.commit()
        records.extend(scored)
        settlements.append(settlement)
        print(json.dumps(dict(batch=name,**policy.summary(),spent_nanodollars=wallet.spent(time.monotonic_ns()))),flush=True)
    if stopped is None:
        stopped = 'finite_batch_limit'
    ended_ns = time.monotonic_ns()
    spent = wallet.spent(ended_ns)
    if spent > wallet.cap_nanodollars:
        raise ValueError('Actual continuous acquisition time exceeded wallet; preserve failed result')
    if wallet.pending or policy.pending:
        raise ValueError('Unresolved action')
    # End-of-run envelope/hashing/export are closing overhead, separately measured
    # by the wrapper; all raw/scored and per-batch settlement persistence above count.
    result = dict(status='completed',**policy.summary(),policy=config['policy'],
        model_revision=REVISION,student_updates=0,cap_nanodollars=wallet.cap_nanodollars,
        problem_nanodollars=wallet.problem_nanodollars,hourly_nanodollars=wallet.hourly_nanodollars,
        active_start_ns=wallet.start_ns,active_end_ns=ended_ns,active_ns=ended_ns-wallet.start_ns,
        spent_nanodollars=spent,unspent_nanodollars=wallet.cap_nanodollars-spent,
        unspent_fraction=(wallet.cap_nanodollars-spent)/wallet.cap_nanodollars,
        setup_ns=setup_ns,stop_reason=stopped,physical_outputs=len(records),
        acquired_ids=policy.ordered_ids[:policy.cursor],parent_outcomes=policy.records,
        sampling_seed=config['sampling_seed'],provider_invoice_usd=None,
        question_prices_are_hypothetical=True,reasoning_validated=False)
    return result
