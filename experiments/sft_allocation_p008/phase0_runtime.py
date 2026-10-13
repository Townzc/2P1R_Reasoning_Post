"""Bounded Phase0 roles. No main procurement or scientific endpoint dispatch."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import subprocess
import time
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,verify
from experiments.sft_allocation_p008.contract import PHASE0_ROLES
from src.sft_data import read_jsonl


def gpu_probe(config,out,store,key,volume,check):
    text=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,uuid','--format=csv,noheader'],text=True)
    if len(text.strip().splitlines())!=1 or 'H100' not in text:
        raise ValueError('Exactly one real H100 required')
    role=config['run_id'];start=time.time();base=out.parent
    # Unique deterministic non-secret payload for each role; never shared mutable files.
    block=hashlib.sha256(role.encode()).digest();blob=block*(config['probe_bytes']//len(block))
    with (out/'io_probe.bin').open('xb') as f:f.write(blob)
    volume.commit()
    ready=dict(role=role,epoch=time.time(),gpu=text,sha256=sha(out/'io_probe.bin'))
    if not store.put(key+'/ready/'+role,ready,skip_if_exists=True):raise ValueError('Duplicate ready event')
    deadline=time.time()+config['barrier_seconds'];observed={}
    while time.time()<deadline:
        check();observed={r:store.get(key+'/ready/'+r) for r in PHASE0_ROLES}
        if all(observed.values()):break
        time.sleep(2)
    else:
        result=dict(status='concurrency_not_achieved',reason='readiness_timeout',
            gpu=text,interval=[start,time.time()],ready=observed,acks={},verified={})
        dump(out/'concurrency.json',result);volume.commit();return result
    if len({x['gpu'].strip().split(',')[-1].strip() for x in observed.values()})!=4:
        raise ValueError('Four distinct physical GPU UUIDs required')
    volume.reload();verified={}
    for r,record in observed.items():
        p=base/r/'io_probe.bin'
        if p.stat().st_size!=config['probe_bytes'] or sha(p)!=record['sha256']:
            raise ValueError('Concurrent shared-volume payload differs')
        verified[r]=record['sha256']
    ack=dict(role=role,epoch=time.time(),read_sha256=verified)
    if not store.put(key+'/ack/'+role,ack,skip_if_exists=True):raise ValueError('Duplicate ack')
    acks={r:None for r in PHASE0_ROLES}
    while time.time()<deadline:
        check();acks={r:store.get(key+'/ack/'+r) for r in PHASE0_ROLES}
        if all(acks.values()):break
        time.sleep(2)
    else:
        result=dict(status='concurrency_not_achieved',reason='ack_timeout',
            gpu=text,interval=[start,time.time()],ready=observed,acks=acks,verified=verified)
        dump(out/'concurrency.json',result);volume.commit();return result
    # Every role stays alive until all four have read every committed probe.
    result=dict(status='four_gpu_verified',reason=None,gpu=text,interval=[start,time.time()],ready=observed,acks=acks,verified=verified)
    dump(out/'concurrency.json',result);volume.commit();return result


def teacher(inputs,assets,out,journal):
    from vllm import LLM,SamplingParams
    from transformers import AutoTokenizer
    from experiments.sft_allocation_acquisition.contract import completion,assess,messages,REVISION
    requests=read_jsonl(inputs/'calibration_requests.jsonl')
    if len(requests)!=1024 or len({x['candidate_id'] for x in requests})!=1024:
        raise ValueError('Frozen 1024 attempts required')
    versions={p:importlib.metadata.version(p) for p in ('vllm','torch','transformers','tokenizers','numpy')}
    if versions['vllm']!='0.11.0' or versions['torch'].split('+')[0]!='2.8.0' or versions['transformers']!='4.56.2' or versions['tokenizers']!='0.22.1':
        raise ValueError('Unpinned teacher runtime')
    dump(out/'software.json',dict(versions=versions,revision=REVISION,
         freeze=subprocess.check_output(['python','-m','pip','freeze'],text=True)))
    journal.check();tick=time.monotonic()
    model=LLM(model=str(assets/'model'),tokenizer=str(assets/'model'),dtype='bfloat16',
       tensor_parallel_size=1,max_model_len=2048,max_num_seqs=32,max_num_batched_tokens=4096,
       gpu_memory_utilization=.65,enforce_eager=True,enable_prefix_caching=False,seed=20261013,
       disable_log_stats=True)
    tok=AutoTokenizer.from_pretrained(assets/'model',local_files_only=True)
    dump(out/'model_loaded.json',dict(seconds=time.monotonic()-tick))
    seen={};usable_seen={};all_records=[]
    for start in range(0,1024,32):
        part=requests[start:start+32];unit=f'teacher_batch_{start:04d}';prompts=[];params=[]
        for r in part:
            ids=tok.apply_chat_template(messages(r['parent']),tokenize=True,add_generation_prompt=True)
            if ids!=r['prompt_token_ids']:raise ValueError('Teacher prompt IDs changed')
            prompts.append(dict(prompt_token_ids=ids))
            params.append(SamplingParams(n=1,temperature=.8,top_p=.95,top_k=-1,max_tokens=1024,
               repetition_penalty=1.,seed=r['seed'],stop_token_ids=[151645,151643],ignore_eos=False))
        journal.begin(unit,dict(candidate_ids=[r['candidate_id'] for r in part],seeds=[r['seed'] for r in part]))
        tick=time.monotonic();generated=model.generate(prompts,params,use_tqdm=False)
        seconds=time.monotonic()-tick
        if len(generated)!=len(part):raise ValueError('Missing teacher request result')
        raw=[]
        for r,g in zip(part,generated):
            if list(g.prompt_token_ids)!=r['prompt_token_ids'] or len(g.outputs)!=1:raise ValueError('Request/return mismatch')
            y=g.outputs[0];raw.append(dict(candidate_id=r['candidate_id'],prompt_token_ids=list(g.prompt_token_ids),
              token_ids=list(y.token_ids),backend_text=y.text,finish_reason=y.finish_reason,stop_reason=y.stop_reason))
        rawpath=out/(unit+'_raw.json');dump(rawpath,dict(seconds=seconds,outputs=raw));journal.commit()
        scored=[]
        for r,y in zip(part,raw):
            stop=completion(y['token_ids']);text=tok.decode(stop['text_token_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
            pid=r['problem_id'];s=seen.setdefault(pid,{});u=usable_seen.setdefault(pid,{})
            verdict=assess(r['parent'],text,stop,s,u)
            record=dict(candidate_id=r['candidate_id'],problem_id=pid,attempt=r['attempt'],seed=r['seed'],text=text,
               prompt_tokens=len(r['prompt_token_ids']),completion_tokens=stop['token_count'],stop=stop,**verdict)
            s.setdefault(verdict['normalized_text_sha256'],r['candidate_id'])
            if verdict['usable']:u.setdefault(verdict['normalized_text_sha256'],r['candidate_id'])
            scored.append(record)
        scoredpath=out/(unit+'_scored.json');dump(scoredpath,scored)
        journal.end(unit,dict(count=32,seconds=seconds,raw_sha256=sha(rawpath),scored_sha256=sha(scoredpath)))
        journal.commit();all_records.extend(scored)
        print(json.dumps(dict(role='teacher_calibration',completed=len(all_records))),flush=True)
    return dict(outputs=len(all_records),usable=sum(x['usable'] for x in all_records),
                generated_tokens=sum(x['completion_tokens'] for x in all_records),engineering_only=True)


def smoke(inputs,assets,out,journal,identity):
    from experiments.sft_allocation_midpoint import runtime as rt
    from experiments.sft_allocation_p008.contract import lrs
    environment=rt.environment(expected_gpu='H100');dump(out/'software.json',environment)
    recipe=read(inputs/'smoke_recipe.json')
    if recipe['lrs']!=lrs(2048)[:8] or recipe['schedule']!=[[i] for i in range(8)]:raise ValueError('Smoke recipe changed')
    model,tok=rt.new_model(assets/'model',17);rows=read_jsonl(inputs/'smoke_train.jsonl');encoded=rt.encode(rows,tok)
    if len(rows)!=8 or sum(r['n_supervised'] for r in encoded)!=recipe['supervised_targets']:raise ValueError('Smoke dose mismatch')
    dump(out/'recipe.json',dict(identity=identity,recipe=recipe))
    opt=rt.optimizer_for(model)
    history,targets,processed=rt.train(model,tok,opt,encoded,recipe['schedule'],recipe['lrs'],out,journal,identity,save_steps=(8,))
    evalrows=read_jsonl(inputs/'smoke_eval.jsonl')
    if len(evalrows)!=16:raise ValueError('Smoke eval roster changed')
    evaluation=rt.evaluate(model,tok,evalrows,out,'engineering_eval16',journal,
        config=dict(max_new_tokens=512,max_length=2048,eval_batch_size=16))
    return dict(updates=len(history),targets=targets,processed=processed,evaluation=evaluation,engineering_only=True)
