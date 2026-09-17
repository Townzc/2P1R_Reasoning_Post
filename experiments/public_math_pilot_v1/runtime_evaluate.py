"""Full frozen public evaluation, balanced by dataset/draw, with immutable outputs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import gc
import json
from pathlib import Path
import time

import torch

from .data import load_inputs
from .losses import ARMS
from .preflight import drop_model, json_hash, load_base, sha
from .runtime_common import PhysicalLedger, ensure_record, generate_rows, read, require_time
from .runtime_prepare import prepare_identity
from .runtime_train import store_for, manifests_for
from .tokenization import encode_prompt


def evaluation_jobs():
    states=['Base',*ARMS];jobs=[]
    # Fixed independent of scores: cover every state on GSM first, then every
    # state at each MATH draw. An overnight pause therefore has explicit coverage.
    for arm in states:
        jobs.append(dict(arm=arm,step=0 if arm=='Base' else 128,dataset='gsm8k',seed=None,
            name=arm+'-GSM8K',batch_size=128))
    for draw in range(8):
        for arm in states:
            jobs.append(dict(arm=arm,step=0 if arm=='Base' else 128,dataset='math500',
                seed=2026091800+draw,name=f'{arm}-MATH500-draw{draw}',batch_size=256))
    for arm in ARMS:
        for step in (64,128):
            jobs.append(dict(arm=arm,step=step,dataset='dev',seed=None,
                name=f'{arm}-step{step}-dev',batch_size=16))
    return jobs


def model_identity(base_identity, manifest, arm, step, contract_hash):
    if arm=='Base':
        if step!=0:raise ValueError('Base has no trained endpoint')
        return base_identity
    if manifest['step']!=step or not manifest['scientific'] or (step==128 and not manifest['terminal']):
        raise ValueError('Wrong evaluation endpoint')
    return dict(base_identity,model_sha256=manifest['files']['model']['sha256'],
        arm=arm,step=step,training_contract_sha256=contract_hash)


def wait_endpoint(out,volumes,contract,arm,step,deadline):
    """Only consume a published checkpoint on the trainer's committed ancestry."""
    if arm=='Base':return None
    while True:
        require_time(deadline,300)
        # Do not create checkpoint directories while the trainer is establishing
        # ownership; wait for its first atomic latest pointer.
        if (Path(out)/'checkpoints'/arm/'latest.json').exists():
            store=store_for(out,volumes,contract,arm)
            for manifest in manifests_for(store):
                if manifest['step']==step and manifest['scientific']:return manifest
        time.sleep(2)


def wait_generation_memory(dataset,deadline):
    required=(64 if dataset=='math500' else 32 if dataset=='gsm8k' else 22)*2**30
    waiting=False
    while True:
        require_time(deadline,300)
        free,total=torch.cuda.mem_get_info()
        if free>=required:return
        if not waiting:
            print(json.dumps(dict(event='waiting_for_generation_memory',dataset=dataset,
                free_bytes=free,required_bytes=required)),flush=True);waiting=True
        time.sleep(2)


def run(args):
    out=Path(args.output)
    with (out/'GPU.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        torch.set_num_threads(8)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        tokenizer,base_identity,_=prepare_identity(args.base,args.release,args.inputs)
        while not (out/'TRAIN_CONTRACT.json').exists():
            require_time(args.deadline_unix,300);time.sleep(2)
        contract=read(out/'TRAIN_CONTRACT.json')
        if contract['scientific_identity']!=base_identity:
            raise ValueError('Training/public base identity differs')
        released=load_inputs(args.release)
        rows={name:[dict(id=r['problem_id'],prompt_ids=encode_prompt(tokenizer,r['question']))
            for r in released[name]] for name in ('gsm8k','math500','dev')}
        if [len(rows[n]) for n in ('gsm8k','math500','dev')]!=[1319,500,512]:
            raise ValueError('Benchmark denominators differ')
        jobs=evaluation_jobs();ledger=PhysicalLedger(args.ledger)
        ensure_record(out/'EVALUATION_CONTRACT.json',dict(schema=1, jobs=jobs,
            base_identity=base_identity,training_contract_sha256=json_hash(contract),
            model_identities_bound_per_run_before_generation=True,
            concurrency='one separately locked trainer and one generator; immutable checkpoints only',
            prompt_sha256={name:[json_hash(r['prompt_ids']) for r in rr] for name,rr in rows.items()},
            public_generations=26595,dev_generations_including_base=4608,total_generations=31203,
            checkpoint_selection='step128 fixed before results; step64 diagnostic only',
            source_commit=args.source_commit,implementation_sha256={n:sha(Path(__file__).with_name(n))
                for n in ('runtime_evaluate.py','runtime_common.py','preflight.py','tokenization.py')}))
        done=[]
        for job in jobs:
            name=job['name'];folder=out/'generation'/name
            manifest=wait_endpoint(out,args.volume_root,contract,job['arm'],job['step'],args.deadline_unix)
            identity=model_identity(base_identity,manifest,job['arm'],job['step'],json_hash(contract))
            already_complete=(folder/'COMPLETE.json').exists()
            model=None
            if not already_complete:
                require_time(args.deadline_unix,300)
                wait_generation_memory(job['dataset'],args.deadline_unix)
                model=load_base(args.base,training=False)
                if job['arm']!='Base':
                    store=store_for(out,args.volume_root,contract,job['arm'])
                    path=store._verify_file(manifest['files']['model'])
                    state=torch.load(path,map_location='cpu',weights_only=True)
                    model.load_state_dict(state,strict=True);del state;gc.collect()
                print(json.dumps(dict(event='evaluation_state_loaded',name=name,model=identity)),flush=True)
            try:
                generate_rows(model,tokenizer,rows[job['dataset']],folder,model_identity=identity,
                    logical_name=name,ledger=ledger,deadline=args.deadline_unix,
                    batch_size=job['batch_size'],seed=job['seed'],allow_new_calls=not already_complete)
            finally:
                if model is not None:
                    drop_model(model);del model;gc.collect();torch.cuda.empty_cache()
            done.append(dict(name=name,completion_sha256=sha(folder/'COMPLETE.json')))
            print(json.dumps(dict(event='evaluation_run_complete',name=name,completed_runs=len(done),total_runs=len(jobs))),flush=True)
        complete=read(out/'TRAINING_COMPLETE.json')
        if complete['formal_updates']!=512 or complete['contract_sha256']!=json_hash(contract):
            raise ValueError('Training closeout differs')
        ensure_record(out/'EVALUATION_COMPLETE.json',dict(contract_sha256=sha(out/'EVALUATION_CONTRACT.json'),
            runs=done,base_dev_sha256=sha(out/'generation'/'Base-dev'/'COMPLETE.json'),
            total_generations=31203,scoring_not_implied=True))
        # Retain every full128 recovery. Scientific64 models may be pruned only
        # after their exact512 dev outputs and verified terminal recovery exist.
        for arm in ARMS:
            store=store_for(out,args.volume_root,contract,arm)
            store.prune_scientific_temp(complete['endpoints'][arm]['64'],evaluation_complete=True)
        return dict(status='generation_complete',total_generations=31203)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','release','inputs','output','ledger','source-commit'):p.add_argument('--'+name,required=True)
    p.add_argument('--volume-root',action='append',required=True)
    p.add_argument('--deadline-unix',type=float,required=True)
    print(json.dumps(run(p.parse_args()),sort_keys=True),flush=True)
