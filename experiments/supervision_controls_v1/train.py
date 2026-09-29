"""New controls using the audited pilot's exact update loop and loss formula.

The loop is adapted from public_math_pilot_v1.runtime_train.train_arm. Changes
are condition-specific masks/names, a new phase checkpoint namespace, explicit
physical-update admission, no blind replay, and only step128 as a scientific
endpoint. Model, optimizer, schedule, precision, clipping and batches stay fixed.
"""
from __future__ import annotations
from datetime import datetime, timezone
import gc
import json
import os
from pathlib import Path
import time
import uuid
import torch

from experiments.public_math_pilot_v1.checkpoints import CheckpointStore, capture_rng, restore_rng
from experiments.public_math_pilot_v1.losses import compute_loss
from experiments.public_math_pilot_v1.preflight import (drop_model, host_available_bytes, json_hash,
    load_base, seed_all, training_batch, write_json)
from experiments.public_math_pilot_v1.runtime_common import stop_due
from experiments.public_math_pilot_v1.runtime_train import (wait_for_training_memory,
    validate_history as validate_pilot_history)
from .io import PHASE, NEW_ARMS, Ledger


def store_for(out, volumes, contract, arm):
    if arm not in NEW_ARMS:
        raise ValueError('Unregistered training condition')
    return CheckpointStore(Path(out)/'checkpoints'/arm, volumes, phase=PHASE, arm=arm,
        config_hash=json_hash(dict(contract=contract,arm=arm)))


def validate_history(history, contract, arm, upto):
    if any(r['arm'] != arm for r in history):
        raise ValueError('Training condition identity differs')
    return validate_pilot_history([dict(r,arm='QDW_v0') for r in history],contract,'QDW_v0',upto)


def advise_cache(store, manifest):
    """Release only clean cache for committed owned files; no disk-byte changes."""
    if manifest is None or not hasattr(os,'posix_fadvise'):
        return
    for record in manifest['files'].values():
        path=store.roots[record['volume']]/record['path']
        with path.open('rb') as f:
            os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)


def train_arm(args, contract, batches, masks, arm):
    out=Path(args.output); store=store_for(out,args.volume_root,contract,arm)
    ledger=Ledger(out/'physical_ledger.jsonl')
    latest=store.latest_manifest()
    if latest and latest['terminal']:
        for r in latest['files'].values():store._verify_file(r)
        validate_history(latest['metadata']['history'],contract,arm,128)
        return dict(arm=arm,status='already_complete',step=128)
    committed=latest['step'] if latest else 0
    if any(e['kind']=='optimizer_update' and e['logical_id'].startswith(arm+'/') and
           int(e['logical_id'].split('/')[-1])>committed for e in ledger.events()):
        raise RuntimeError('Uncommitted historical updates require explicit reconciliation; no automatic replay')
    if stop_due(args.deadline_unix,300):return dict(arm=arm,status='paused_before_load')
    attempt=uuid.uuid4().hex
    attempt_dir=out/'training'/arm/attempt;attempt_dir.mkdir(parents=True)
    write_json(attempt_dir/'START.json',dict(arm=arm,source_commit=args.source_commit,
        contract_sha256=json_hash(contract),initial_checkpoint=latest['checkpoint_id'] if latest else None,
        started_at_utc=datetime.now(timezone.utc).isoformat()))
    wait_for_training_memory(args.deadline_unix)
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
            ledger.reserve('optimizer_update', [arm+'/'+str(step+1)])
            optimizer.zero_grad(set_to_none=True);torch.cuda.reset_peak_memory_stats();began=time.monotonic();audits=[]
            for offset in range(0,32,2):
                two=group[offset:offset+2]
                selected=[masks[r['problem_id']] for r in two]
                batch,labels,qmask=training_batch(two,masks=selected)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    logits=model(**batch,use_cache=False).logits
                    loss,audit=compute_loss(logits,labels,'QDW_v0',denominator,
                        qdw_mask=qmask,attention_mask=batch['attention_mask'])
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
                advise_cache(store, latest)
                if host_available_bytes()<48*2**30:raise RuntimeError('Insufficient RAM for verified checkpoint')
                if validate_history(history,contract,arm,step)!=token_step:raise ValueError('Training history mismatch')
                began=time.monotonic()
                latest=store.save(model.state_dict(),optimizer.state_dict(),step=step,token_step=token_step,
                    scheduler_state=dict(next_update=step+1,learning_rates=contract['learning_rates']),
                    rng_state=capture_rng(),metadata=dict(history=history,contract_sha256=json_hash(contract),
                        parent_checkpoint_id=latest['checkpoint_id'] if latest else None,
                        initial_public_base_sha256=contract['scientific_identity']['model_sha256']),
                    scientific=step==128,terminal=step==128)
                saved_step=step
                advise_cache(store, latest)
                print(json.dumps(dict(event='checkpoint_committed',arm=arm,step=step,
                    seconds=time.monotonic()-began,model_sha256=latest['files']['model']['sha256'])),flush=True)
        if step>saved_step:
            advise_cache(store, latest)
            if host_available_bytes()<48*2**30:
                raise RuntimeError('Insufficient RAM for boundary checkpoint')
            latest=store.save(model.state_dict(),optimizer.state_dict(),step=step,token_step=token_step,
                scheduler_state=dict(next_update=step+1,learning_rates=contract['learning_rates']),rng_state=capture_rng(),
                metadata=dict(history=history,contract_sha256=json_hash(contract),
                    parent_checkpoint_id=latest['checkpoint_id'] if latest else None,
                    initial_public_base_sha256=contract['scientific_identity']['model_sha256']),
                scientific=step==128,terminal=step==128)
        result=dict(arm=arm,status='complete' if step==128 else 'paused_at_boundary',step=step,
            initial_step=initial_step,token_step=token_step,source_commit=args.source_commit)
        write_json(attempt_dir/'END.json',result)
        return result
    finally:
        drop_model(model,optimizer);del optimizer,model;gc.collect();torch.cuda.empty_cache()
