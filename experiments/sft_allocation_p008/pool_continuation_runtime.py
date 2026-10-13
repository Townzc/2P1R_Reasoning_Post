"""Prepared remaining-only D2 runtime; no dispatcher or implicit admission.

The original procurement/generation loop is byte-for-byte unchanged. Only its
initial state is restored from an independently reconciled clean parent prefix.
Cumulative caps cover parent and child; output names continue the old indices.
A future reviewed worker must provide the finite timer and fresh guard journal.
"""
from pathlib import Path
import importlib.metadata
import json
import time
from collections import defaultdict
from experiments.sft_allocation_midpoint.common import dump,read,sha
from experiments.sft_allocation_acquisition.contract import completion,assess,messages,REVISION
from src.sft_data import read_jsonl
from .contract import stable_seed
from .procurement import Wallet,pending_union
from .pool_continuation_prefix import load_prefix


def run(config,inputs,assets,out,journal,prefix):
    from vllm import LLM,SamplingParams
    from transformers import AutoTokenizer
    if (config['draw'] != 2 or config['high_multiple'] != 8 or config['max_physical_attempts'] != 16384
            or config['role'] != 'pool_continuation' or config['run_id'] != 'pool_d2_remaining'
            or config['max_seconds'] != 7200):
        raise ValueError('Unadmitted draw scope')
    if importlib.metadata.version('vllm')!='0.11.0':raise ValueError('Teacher backend changed')
    parents=read_jsonl(Path(inputs)/'eligible_parents.jsonl')
    if len(parents)!=6973 or len({p['id'] for p in parents})!=6973:raise ValueError('Fixed main pool changed')
    draw=config['draw'];parents=sorted(parents,key=lambda p:stable_seed('question_order',draw,p['id']))
    lookup={p['id']:p for p in parents};ids=list(lookup)
    tok=AutoTokenizer.from_pretrained(assets/'model',local_files_only=True)
    prompts={p['id']:tok.apply_chat_template(messages(p),tokenize=True,add_generation_prompt=True) for p in parents}
    lengths={p:len(tokens) for p,tokens in prompts.items()}
    wallets=[Wallet(ids,lengths,draw,b,price,policy) for b in (1,config['high_multiple']) for price in (0,4) for policy in ('breadth','depth')]
    dump(out/'frozen_wallets.json',dict(draw=draw,teacher_revision=REVISION,parent_order=ids,prompt_lengths=lengths,
       wallets=[w.name for w in wallets],max_physical_attempts=config['max_physical_attempts']))
    state,lineage=load_prefix(prefix,config,wallets,ids,lengths)
    dump(out/'parent_lineage.json',lineage)
    journal.check();tick=time.monotonic()
    model=LLM(model=str(assets/'model'),tokenizer=str(assets/'model'),dtype='bfloat16',tensor_parallel_size=1,
       max_model_len=2048,max_num_seqs=32,max_num_batched_tokens=4096,gpu_memory_utilization=.65,
       enforce_eager=True,enable_prefix_caching=False,seed=20261013,disable_log_stats=True)
    dump(out/'model_loaded.json',dict(seconds=time.monotonic()-tick))
    cache=state['cache'];seen=state['seen'];accepted=state['accepted']
    batch_index=state['batch_index'];attempted=state['attempted'];events=state['events']
    physical_token_bound=config['max_physical_attempts']*1024;returned_tokens=state['returned_tokens']
    while True:
        journal.check();active=[]
        for w in wallets:
            p=w.propose()
            if p is None:continue
            name=w.name+'_'+p['batch'];journal.begin(name,p);w.begin(p);active.append(w)
        if not active:break
        journal.commit()  # Publish every wallet intent together BEFORE any cache read/generation.
        missing=pending_union(active,cache)
        if attempted+len(missing)>config['max_physical_attempts']:
            dump(out/'supply_censored.json',dict(attempted=attempted,missing=len(missing),reason='physical_attempt_cap',
               pending=[w.pending for w in active]));journal.commit()
            raise RuntimeError('Physical cap reached; preserve committed virtual reservations, no student dispatch')
        for start in range(0,len(missing),32):
            part=missing[start:start+32];name=f'physical_batch_{batch_index:05d}';batch_index+=1
            for r in part:r['seed']=stable_seed('teacher',draw,r['problem_id'],r['attempt'])
            journal.begin(name,dict(items=part,maximum_new_tokens=1024));journal.commit();attempted+=len(part)
            params=[SamplingParams(n=1,temperature=.8,top_p=.95,top_k=-1,max_tokens=1024,repetition_penalty=1.,
                seed=r['seed'],stop_token_ids=[151645,151643],ignore_eos=False) for r in part]
            tick=time.monotonic();outputs=model.generate([dict(prompt_token_ids=prompts[r['problem_id']]) for r in part],params,use_tqdm=False)
            seconds=time.monotonic()-tick
            if len(outputs)!=len(part):raise ValueError('Missing physical return')
            raw=[]
            for r,g in zip(part,outputs):
                if list(g.prompt_token_ids)!=prompts[r['problem_id']] or len(g.outputs)!=1:raise ValueError('Request identity mismatch')
                y=g.outputs[0];raw.append(dict(candidate_id=r['candidate_id'],prompt_token_ids=list(g.prompt_token_ids),token_ids=list(y.token_ids),
                     backend_text=y.text,finish_reason=y.finish_reason,stop_reason=y.stop_reason))
            rawpath=out/(name+'_raw.json');dump(rawpath,dict(seconds=seconds,outputs=raw));journal.commit()
            scored=[]
            for r,y in zip(part,raw):
                stop=completion(y['token_ids']);text=tok.decode(stop['text_token_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
                pid=r['problem_id'];v=assess(lookup[pid],text,stop,seen[pid],accepted[pid])
                record=dict(**r,text=text,prompt_tokens=lengths[pid],completion_tokens=stop['token_count'],stop=stop,**v)
                if record['candidate_id'] in cache:raise ValueError('Cache entry already exists')
                cache[record['candidate_id']]=record;seen[pid].setdefault(v['normalized_text_sha256'],r['candidate_id'])
                if v['usable']:accepted[pid].setdefault(v['normalized_text_sha256'],r['candidate_id'])
                scored.append(record);returned_tokens+=stop['token_count']
            if returned_tokens>physical_token_bound:raise ValueError('Physical token bound exceeded')
            sp=out/(name+'_scored.json');dump(sp,scored)
            journal.end(name,dict(count=len(part),seconds=seconds,raw_sha256=sha(rawpath),scored_sha256=sha(sp)))
            journal.commit()
        for w in active:
            intent=w.pending
            keys=[f"d{draw}::{r['problem_id']}::{r['attempt']}" for r in intent['action']['items']]
            done=w.settle([cache[k] for k in keys]);journal.end(w.name+'_'+done['batch'],done)
            events[w.name].append(dict(intent=intent,done=done))
        journal.commit()
        print(json.dumps(dict(draw=draw,physical_attempts=attempted,virtual_attempts=sum(len(w.consumed) for w in wallets))),flush=True)
    summaries={w.name:w.summary() for w in wallets}
    for w in wallets:
        dump(out/(w.name+'_events.json'),events[w.name]);dump(out/(w.name+'_summary.json'),summaries[w.name])
    # Compact ordered cache enables independent G1 reconstruction without rerunning teacher.
    dump(out/'candidate_cache.json',cache);journal.commit()
    result=dict(draw=draw,physical_attempts=attempted,physical_outputs=len(cache),returned_tokens=returned_tokens,
         physical_batches=batch_index,wallets=summaries,unknown=0,new_student_updates=0)
    result.update(parent_lineage=lineage,
        child_physical_attempts=attempted-lineage['parent_physical_attempts'],
        child_physical_outputs=len(cache)-lineage['parent_physical_attempts'],
        child_returned_tokens=returned_tokens-lineage['parent_returned_tokens'],
        child_physical_batches=batch_index-lineage['parent_physical_batches'],
        cumulative_parent_plus_child=True,original_parent_status='failed')
    return result
