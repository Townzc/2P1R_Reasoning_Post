"""Four fresh-base,128-update full-parameter runs with checked rolling recovery."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import gc
import json
from pathlib import Path
import random
import time
import uuid

import torch

from .checkpoints import CheckpointStore, capture_rng, restore_rng
from .data import load_inputs
from .losses import ARMS, compute_loss
from .preflight import (PHASE, drop_model, host_available_bytes, json_hash, load_base,
                        seed_all, sha, training_batch, write_json)
from .runtime_common import ensure_record, read, stop_due
from .runtime_prepare import prepare_identity


def frozen_batches(rows):
    if len(rows) != 4096 or len({r['problem_id'] for r in rows}) != 4096:
        raise ValueError('Training requires4096 unique frozen rows')
    order = list(range(len(rows))); random.Random(17).shuffle(order)
    return [[rows[i] for i in order[j:j+32]] for j in range(0,4096,32)]


def training_contract(identity, batches, mask_sha, learning_rates):
    if len(learning_rates)!=128 or learning_rates[-1]!=0:
        raise ValueError('Frozen128-step learning-rate schedule required')
    return dict(schema=1, scientific_identity=identity, arms=list(ARMS),
        training_seed=17, order_algorithm='Python random.Random(17).shuffle of release tokenized_pilot order',
        batches=[[r['problem_id'] for r in batch] for batch in batches],
        denominators=[sum(len(r['response_ids']) for r in b) for b in batches],
        learning_rates=learning_rates, mask_manifest_sha256=mask_sha,
        optimizer=dict(name='AdamW',betas=[.9,.999],eps=1e-8,weight_decay=0.,max_grad_norm=1.),
        microbatch=2,gradient_accumulation=16,training_length_cap=2048,packing=False,
        checkpoints=[32,64,96,128],scientific_endpoints=[64,128],formal_endpoint=128,
        inference_not_interleaved_with_training=True,
        implementation_sha256={n:sha(Path(__file__).with_name(n))
            for n in ('losses.py','tokenization.py','preflight.py','checkpoints.py','runtime_train.py')})


def validate_history(history, contract, arm, upto):
    if len(history)!=upto: raise ValueError('Committed training history length differs')
    for i,r in enumerate(history):
        if (r['arm']!=arm or r['step']!=i+1 or r['row_ids']!=contract['batches'][i]
                or r['supervised_tokens']!=contract['denominators'][i]
                or r['learning_rate']!=contract['learning_rates'][i]
                or r['microbatch']!=2 or r['gradient_accumulation']!=16
                or len(r['microbatch_audits'])!=16):
            raise ValueError('Committed training dose/order/LR differs')
        if sum(a['microbatch_supervised_tokens'] for a in r['microbatch_audits'])!=r['supervised_tokens']:
            raise ValueError('Committed token denominator differs')
        if any(a['update_denominator']!=r['supervised_tokens'] or a['arm']!=arm or not a['weights_detached']
               for a in r['microbatch_audits']):
            raise ValueError('Microbatch loss contract differs')
    return sum(contract['denominators'][:upto])


def store_for(out, volumes, contract, arm):
    return CheckpointStore(Path(out)/'checkpoints'/arm,volumes,phase=PHASE,arm=arm,
        config_hash=json_hash(dict(contract=contract,arm=arm)))


def manifests_for(store):
    """Follow committed ancestry; never adopt a manifest orphaned before publish."""
    result=[];manifest=store.latest_manifest();seen=set()
    while manifest is not None:
        checkpoint_id=manifest['checkpoint_id']
        if checkpoint_id in seen:raise ValueError('Cyclic checkpoint ancestry')
        seen.add(checkpoint_id);result.append(manifest)
        parent=manifest['metadata']['parent_checkpoint_id']
        manifest=read(store.control/'commits'/(parent+'.json')) if parent else None
    return result


def checked_masks(out, rows, identity):
    out=Path(out); manifest=read(out/'MASK_MANIFEST.json');prepared=read(out/'PREPARATION_COMPLETE.json')
    if (prepared['identity']!=identity or not prepared['technical_audit_passed']
            or prepared['mask_manifest_sha256']!=sha(out/'MASK_MANIFEST.json')
            or prepared['audit_sha256']!=sha(out/'MASK_AUDIT.json')
            or prepared['dev_complete_sha256']!=sha(out/'generation'/'Base-dev'/'COMPLETE.json')
            or manifest['count']!=4096 or manifest['identity']!=identity):
        raise ValueError('Formal preparation is incomplete or changed')
    masks={}
    by_id={r['problem_id']:r for r in rows}
    for rec in manifest['records']:
        path=out/'annotations'/rec['path']
        if sha(path)!=rec['sha256']:raise ValueError('Frozen annotation SHA differs')
        value=read(path);ann=value['annotation'];pid=rec['id']
        if value['identity']!=identity or value['id']!=pid or ann['response_ids']!=by_id[pid]['response_ids']:
            raise ValueError('Frozen mask response identity differs')
        if json_hash(ann['mask'])!=rec['mask_sha256'] or ann['K']!=sum(ann['mask']):
            raise ValueError('Frozen mask selection differs')
        if pid in masks:raise ValueError('Duplicate mask')
        masks[pid]=ann['mask']
    if set(masks)!=set(by_id):raise ValueError('Incomplete mask coverage')
    return masks


def train_arm(args, contract, batches, masks, arm):
    out=Path(args.output); store=store_for(out,args.volume_root,contract,arm)
    latest=store.latest_manifest()
    if latest and latest['terminal']:
        for r in latest['files'].values():store._verify_file(r)
        validate_history(latest['metadata']['history'],contract,arm,128)
        return dict(arm=arm,status='already_complete',step=128)
    if stop_due(args.deadline_unix,300):return dict(arm=arm,status='paused_before_load')
    attempt=uuid.uuid4().hex
    attempt_dir=out/'training'/arm/attempt;attempt_dir.mkdir(parents=True)
    write_json(attempt_dir/'START.json',dict(arm=arm,source_commit=args.source_commit,
        contract_sha256=json_hash(contract),initial_checkpoint=latest['checkpoint_id'] if latest else None,
        started_at_utc=datetime.now(timezone.utc).isoformat()))
    model=load_base(args.base,training=True)
    optimizer=torch.optim.AdamW(model.parameters(),lr=5e-5,betas=(.9,.999),eps=1e-8,weight_decay=0)
    history=[];step=0;token_step=0
    if latest:
        restored=store.load_latest()
        model.load_state_dict(restored['model_state'],strict=True)
        optimizer.load_state_dict(restored['optimizer_state'])
        history=restored['metadata']['history'];step=restored['step'];token_step=restored['token_step']
        if validate_history(history,contract,arm,step)!=token_step:raise ValueError('Recovery token count differs')
        if restored['scheduler_state']!=dict(next_update=step+1,learning_rates=contract['learning_rates']):
            raise ValueError('Recovery learning-rate state differs')
        restore_rng(restored['rng_state']);del restored;gc.collect()
    else:
        seed_all(17)
    initial_step=step;saved_step=step
    try:
        while step<128 and not stop_due(args.deadline_unix,180):
            group=batches[step];denominator=contract['denominators'][step];lr=contract['learning_rates'][step]
            for param_group in optimizer.param_groups:param_group['lr']=lr
            write_json(attempt_dir/f'update_{step+1:03d}.reservation.json',dict(arm=arm,step=step+1,
                row_ids=contract['batches'][step],parent_committed_checkpoint=latest['checkpoint_id'] if latest else None,
                current_uncommitted_prefix=[x['step'] for x in history[saved_step:]],
                reserved_at_utc=datetime.now(timezone.utc).isoformat()))
            optimizer.zero_grad(set_to_none=True);torch.cuda.reset_peak_memory_stats();began=time.monotonic();audits=[]
            for offset in range(0,32,2):
                two=group[offset:offset+2]
                selected=[masks[r['problem_id']] for r in two] if arm=='QDW_v0' else None
                batch,labels,qmask=training_batch(two,masks=selected)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    logits=model(**batch,use_cache=False).logits
                    loss,audit=compute_loss(logits,labels,arm,denominator,
                        qdw_mask=qmask if arm=='QDW_v0' else None,attention_mask=batch['attention_mask'])
                loss.backward();audits.append(audit)
                del batch,labels,qmask,logits,loss
            norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
            optimizer.step();torch.cuda.synchronize();step+=1;token_step+=denominator
            if step==1:
                if any(value.dtype!=torch.float32 for st in optimizer.state.values()
                       for key,value in st.items() if key!='step' and isinstance(value,torch.Tensor)):
                    raise ValueError('AdamW master states must be FP32')
            entry=dict(arm=arm,step=step,row_ids=contract['batches'][step-1],supervised_tokens=denominator,
                cumulative_supervised_tokens=token_step,learning_rate=lr,seconds=time.monotonic()-began,
                grad_norm_before_clipping=float(norm),max_memory_allocated=torch.cuda.max_memory_allocated(),
                microbatch=2,gradient_accumulation=16,microbatch_audits=audits,
                weighted_loss=sum(x['weighted_numerator'] for x in audits)/denominator,
                raw_ce=sum(x['unweighted_numerator'] for x in audits)/denominator,
                attempt=attempt,source_commit=args.source_commit)
            write_json(attempt_dir/f'update_{step:03d}.completed.json',entry);history.append(entry)
            print(json.dumps(dict(event='formal_update_done',arm=arm,step=step,seconds=entry['seconds'],
                raw_ce=entry['raw_ce'],weighted_loss=entry['weighted_loss'])),flush=True)
            if step%32==0 or stop_due(args.deadline_unix,200):
                if host_available_bytes()<48*2**30:raise RuntimeError('Insufficient RAM for verified checkpoint')
                if validate_history(history,contract,arm,step)!=token_step:raise ValueError('Training history mismatch')
                began=time.monotonic()
                latest=store.save(model.state_dict(),optimizer.state_dict(),step=step,token_step=token_step,
                    scheduler_state=dict(next_update=step+1,learning_rates=contract['learning_rates']),
                    rng_state=capture_rng(),metadata=dict(history=history,contract_sha256=json_hash(contract),
                        parent_checkpoint_id=latest['checkpoint_id'] if latest else None,
                        initial_public_base_sha256=contract['scientific_identity']['model_sha256']),
                    scientific=step in (64,128),terminal=step==128)
                saved_step=step
                print(json.dumps(dict(event='checkpoint_committed',arm=arm,step=step,
                    seconds=time.monotonic()-began,model_sha256=latest['files']['model']['sha256'])),flush=True)
        if step>saved_step:
            latest=store.save(model.state_dict(),optimizer.state_dict(),step=step,token_step=token_step,
                scheduler_state=dict(next_update=step+1,learning_rates=contract['learning_rates']),rng_state=capture_rng(),
                metadata=dict(history=history,contract_sha256=json_hash(contract),
                    parent_checkpoint_id=latest['checkpoint_id'] if latest else None,
                    initial_public_base_sha256=contract['scientific_identity']['model_sha256']),
                scientific=step in (64,128),terminal=step==128)
        result=dict(arm=arm,status='complete' if step==128 else 'paused_at_boundary',step=step,
            initial_step=initial_step,token_step=token_step,source_commit=args.source_commit)
        write_json(attempt_dir/'END.json',result)
        return result
    finally:
        drop_model(model,optimizer);del optimizer,model;gc.collect();torch.cuda.empty_cache()


def run(args):
    out=Path(args.output)
    with (out/'GPU.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        torch.set_num_threads(8)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        _,identity,_=prepare_identity(args.base,args.release,args.inputs)
        released=load_inputs(args.release);rows=released['tokenized_pilot'];batches=frozen_batches(rows)
        masks=checked_masks(out,rows,identity)
        lr=read(Path(__file__).with_name('EXECUTION_CONTRACT.json'))['learning_rates']
        contract=training_contract(identity,batches,sha(out/'MASK_MANIFEST.json'),lr)
        ensure_record(out/'TRAIN_CONTRACT.json',contract)
        results=[]
        for arm in ARMS:
            result=train_arm(args,contract,batches,masks,arm);results.append(result)
            if result['status'] not in ('complete','already_complete'):return dict(status='paused',arms=results)
        endpoints={}
        for arm in ARMS:
            store=store_for(out,args.volume_root,contract,arm)
            manifests=manifests_for(store)
            endpoints[arm]={str(step):next(m for m in manifests if m['step']==step and m['scientific'])
                for step in (64,128)}
            for m in endpoints[arm].values():store._verify_file(m['files']['model'])
        ensure_record(out/'TRAINING_COMPLETE.json',dict(contract_sha256=json_hash(contract),
            formal_updates=512,unique_questions_per_arm=4096,supervised_tokens_per_arm=sum(contract['denominators']),
            endpoints=endpoints,public_base_fresh_each_arm=True))
        return dict(status='four_arm_training_complete',formal_updates=512)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','release','inputs','output','source-commit'):p.add_argument('--'+name,required=True)
    p.add_argument('--volume-root',action='append',required=True)
    p.add_argument('--deadline-unix',type=float,required=True)
    print(json.dumps(run(p.parse_args()),sort_keys=True),flush=True)
