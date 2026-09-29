"""Finite engineering-only GPU preflight for the frozen public-math pilot.

No formal optimizer update is committed. The source and input manifests must be
published before invocation. Baseline dev/profile annotations are durable and
may be reused only under their full identity. A passed preflight does not admit
the four-arm phase: independent complete-phase time/money/export admission is
still mandatory.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import gc
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .losses import ARMS, causal_gold_log_probs, compute_loss, select_qdw_tokens, validate_response_alignment
from .tokenization import ASSISTANT_END_ID, EOS_ID, CONTEXT_LIMIT, validate_tokenizer, trim_stop_text
from .checkpoints import CheckpointStore, capture_rng, restore_rng, _same

PHASE = 'public_math_pilot_v1'
MODEL_REVISION = '4a83ca6e4526a4f2da3aa259ec36c259f66b2ab2'


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    """Publish a new immutable record; never replace a previous result."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    tmp = path.with_suffix(path.suffix + '.pending')
    with tmp.open('x') as f:
        json.dump(value, f, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def reserve_call(ledger, kind, logical_id):
    """Append a durable charge before starting work, including failed attempts."""
    path = Path(ledger); path.parent.mkdir(parents=True, exist_ok=True)
    caps = {'nonformal_optimizer_update': 8, 'generation': 31203, 'annotation_forward': 8192}
    if kind not in caps: raise ValueError('Unknown reservation kind')
    with path.open('a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX); f.seek(0)
        events = [json.loads(line) for line in f if line.strip()]
        if any(e['phase'] != PHASE for e in events): raise ValueError('Wrong budget phase')
        used = sum(e['kind'] == kind for e in events)
        if used >= caps[kind]: raise RuntimeError('Shared physical budget exhausted: ' + kind)
        event = dict(phase=PHASE, kind=kind, logical_id=logical_id, ordinal=used + 1,
                     reserved_at_utc=datetime.now(timezone.utc).isoformat())
        f.seek(0, 2); f.write(json.dumps(event, sort_keys=True) + '\n'); f.flush(); os.fsync(f.fileno())
        return event


def host_available_bytes():
    available=None
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'): available=int(line.split()[1]) * 1024
    if available is None: raise RuntimeError('Cannot measure host available RAM')
    for limit_path,used_path in (
        ('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory.current'),
        ('/sys/fs/cgroup/memory/memory.limit_in_bytes','/sys/fs/cgroup/memory/memory.usage_in_bytes')):
        if Path(limit_path).exists() and Path(used_path).exists():
            limit=Path(limit_path).read_text().strip()
            if limit != 'max': available=min(available,int(limit)-int(Path(used_path).read_text()))
    return available


def check_deadline(deadline, reserve=0):
    if time.time() + reserve >= deadline:
        raise TimeoutError('Bounded preflight deadline reached; no formal work admitted')


def seed_all(seed=17):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def training_batch(rows, device='cuda', *, force_length=None, masks=None):
    width = max(len(r['input_ids']) for r in rows) if force_length is None else force_length
    if width > 2048 or any(len(r['input_ids']) > width for r in rows):
        raise ValueError('No reference truncation is allowed')
    ids = torch.full((len(rows), width), EOS_ID, dtype=torch.long, device=device)
    labels = torch.full_like(ids, -100); attention = torch.zeros_like(ids)
    qmask = torch.zeros_like(ids, dtype=torch.bool)
    for i, row in enumerate(rows):
        n = len(row['input_ids'])
        start = row['response_start']
        if (not 0 < start < n or row['input_ids'][start:] != row['response_ids'] or
                row['labels'] != [-100] * start + row['response_ids'] or
                row['response_ids'][-1] != ASSISTANT_END_ID or len(row['labels']) != n):
            raise ValueError('Encoded sample/label identity mismatch')
        ids[i, :n] = torch.tensor(row['input_ids'], device=device)
        labels[i, :n] = torch.tensor(row['labels'], device=device)
        attention[i, :n] = 1
        if masks is not None:
            mask = masks[i]
            if len(mask) != len(row['response_ids']): raise ValueError('Response mask differs')
            qmask[i, row['response_start']:n] = torch.tensor(mask, dtype=torch.bool, device=device)
    return dict(input_ids=ids, attention_mask=attention), labels, qmask


def generation_batch(rows, device='cuda'):
    width = max(len(r['prompt_ids']) for r in rows)
    if width + 2048 > CONTEXT_LIMIT:
        raise ValueError('Actual model context exceeded')
    ids = torch.full((len(rows), width), EOS_ID, dtype=torch.long, device=device)
    attention = torch.zeros_like(ids)
    for i, r in enumerate(rows):
        n = len(r['prompt_ids']); ids[i, width-n:] = torch.tensor(r['prompt_ids'], device=device)
        attention[i, width-n:] = 1
    return dict(input_ids=ids, attention_mask=attention)


def load_base(base, *, training):
    seed_all(17)
    model = AutoModelForCausalLM.from_pretrained(base, local_files_only=True,
        torch_dtype=torch.float32, attn_implementation='sdpa')
    if model.config.max_position_embeddings != CONTEXT_LIMIT:
        raise ValueError('Model context identity mismatch')
    model.to('cuda')
    if training:
        model.train(); model.config.use_cache = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    else:
        model.eval(); model.config.use_cache = True
    if any(p.dtype != torch.float32 for p in model.parameters()):
        raise ValueError('Master parameters must remain FP32')
    return model


def drop_model(model, optimizer=None):
    if optimizer is not None: optimizer.zero_grad(set_to_none=True)
    model.to('cpu')
    gc.collect(); torch.cuda.empty_cache()


def gold_forward(model, encoded, *, blank=False):
    validate_response_alignment(encoded['input_ids'], encoded['blank_input_ids'],
        encoded['response_start'], encoded['blank_response_start'], encoded['response_ids'])
    entry = dict(encoded)
    if blank:
        entry['input_ids'] = encoded['blank_input_ids']; entry['labels'] = encoded['blank_labels']
        entry['response_start'] = encoded['blank_response_start']
    inputs, labels, _ = training_batch([entry])
    began = time.monotonic()
    with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
        logits = model(**inputs, use_cache=False).logits
        dense, valid = causal_gold_log_probs(logits, labels, attention_mask=inputs['attention_mask'])
        values = dense[valid].detach().cpu().tolist()
    torch.cuda.synchronize()
    if len(values) != len(encoded['response_ids']):
        raise ValueError('Gold response alignment differs')
    return values, dict(seconds=time.monotonic()-began, input_tokens=len(entry['input_ids']), sequence_forwards=1)


def greedy_profile(model, tokenizer, rows, output, identity, deadline, batch_size=16, ledger=None):
    if len(rows) != 32:
        raise ValueError('Preflight requires the fixed first32 dev rows')
    records = []; total = 0.; cap_count = 0
    for offset in range(0, len(rows), batch_size):
        check_deadline(deadline, reserve=120)
        group = rows[offset:offset+batch_size]
        if ledger is None: raise ValueError('A shared physical ledger is required')
        for row in group: reserve_call(ledger, 'generation', 'Base-dev/' + row['id'])
        reservation = dict(status='reserved', rows=[r['id'] for r in group], identity=identity,
            max_new_tokens=2048, started_at_utc=datetime.now(timezone.utc).isoformat())
        write_json(output/f'dev_batch_{offset:04d}.reservation.json', reservation)
        inputs = generation_batch(group)
        began = time.monotonic(); model.eval()
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.bfloat16):
            generated = model.generate(**inputs, do_sample=False, max_new_tokens=2048,
                pad_token_id=EOS_ID, eos_token_id=[ASSISTANT_END_ID, EOS_ID],
                repetition_penalty=1.0, use_cache=True, stop_strings=['</s>'], tokenizer=tokenizer)
        torch.cuda.synchronize(); elapsed = time.monotonic()-began; total += elapsed
        outputs = generated[:, inputs['input_ids'].shape[1]:].cpu().tolist(); batch = []
        if len(outputs) != len(group): raise ValueError('Generated batch row count differs')
        for row, tokens in zip(group, outputs):
            # Find the first completed string stop before a later batch padding
            # EOS. A stopped row must never count post-stop padding as output.
            first_eos = next((j for j,t in enumerate(tokens) if t in (ASSISTANT_END_ID, EOS_ID)), None)
            search_end = first_eos + 1 if first_eos is not None else len(tokens)
            first_string = None
            if '</s>' in tokenizer.decode(tokens[:search_end], skip_special_tokens=False):
                for j in range(1, search_end + 1):
                    if '</s>' in tokenizer.decode(tokens[:j], skip_special_tokens=False):
                        first_string = j; break
            if first_string is not None and (first_eos is None or first_string <= first_eos):
                tokens = tokens[:first_string]; reason='stop_string'
            elif first_eos is not None:
                tokens = tokens[:first_eos+1]; reason='eos'
            else:
                reason='length_cap'
            text = tokenizer.decode(tokens, skip_special_tokens=False)
            if reason == 'length_cap' and len(tokens) < 2048:
                raise ValueError('Unexplained short generation')
            cap_count += reason == 'length_cap'
            record=dict(id=row['id'], prompt_sha256=json_hash(row['prompt_ids']), identity=identity,
                generated_ids=tokens, raw_text=text, scored_text=trim_stop_text(text),
                output_tokens=len(tokens), stop_reason=reason, max_new_tokens=2048,
                generation_calls=1, decoding='greedy', extra_generation_rounds=0, tools=False)
            batch.append(record); records.append(record)
        write_json(output/f'dev_batch_{offset:04d}.outputs.json',dict(records=batch,seconds=elapsed))
    return dict(outputs=len(records), output_tokens=sum(r['output_tokens'] for r in records),
        seconds=total, output_tokens_per_second=sum(r['output_tokens'] for r in records)/total,
        length_caps=cap_count, batch_size=batch_size, pure_text_generation=True,
        whole_benchmark_performance_estimate=False)


def run(args):
    out=Path(args.output); out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic(); status='failed'; receipt={}
    try:
        if not torch.cuda.is_available(): raise RuntimeError('A CUDA GPU is required')
        check_deadline(args.deadline_unix, reserve=600)
        inputs=json.loads(Path(args.inputs).read_text());base=Path(args.base)
        if inputs['model_revision'] != MODEL_REVISION: raise ValueError('Base revision differs')
        if any(len(inputs[name])!=32 for name in ('train_profile','longest_profile','dev_profile')):
            raise ValueError('Frozen32 shape differs')
        for name,wanted in inputs['model_files_sha256'].items():
            if sha(base/name)!=wanted:raise ValueError('Official base/tokenizer SHA mismatch: '+name)
        if any(len(r['input_ids'])>2048 for r in inputs['train_profile']):raise ValueError('Overlength reference')
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        torch.set_num_threads(8)
        tokenizer=AutoTokenizer.from_pretrained(base,local_files_only=True)
        tokenizer_identity=validate_tokenizer(tokenizer)
        identity=dict(model_revision=MODEL_REVISION,model_sha256=inputs['model_files_sha256']['model.safetensors'],
            source_commit=args.source_commit,inputs_sha256=sha(args.inputs),
            release_manifest_sha256=inputs['release_manifest_sha256'],precision='FP32_master_BF16_autocast',
            attention='sdpa',tokenizer=tokenizer_identity)
        write_json(out/'identity.json',identity)
        receipt=dict(status='running',identity=identity,formal_optimizer_updates=0,
            nonformal_optimizer_updates=0,training=[],annotations=[],generation=None,
            hardware=dict(name=torch.cuda.get_device_name(0),total_memory_bytes=torch.cuda.get_device_properties(0).total_memory),
            versions=dict(torch=torch.__version__,transformers=__import__('transformers').__version__))
        # Four normal-length updates plus one real longest-reference TrimSFT update, at
        # most five nonformal updates. Every arm is initialized from public base.
        for arm in ARMS:
            check_deadline(args.deadline_unix,reserve=480)
            model=load_base(base,training=True)
            optimizer=torch.optim.AdamW(model.parameters(),lr=5e-5,betas=(.9,.999),eps=1e-8,weight_decay=0)
            profiles=['train_profile','longest_profile'] if arm=='TrimSFT' else ['train_profile']
            for profile_name in profiles:
                print(json.dumps(dict(event='engineering_update_start',arm=arm,profile=profile_name)),flush=True)
                rows=inputs[profile_name]; denominator=sum(len(r['response_ids']) for r in rows)
                masks=[]
                for row in rows:
                    n=len(row['response_ids']);m=[False]*n
                    # Explicit engineering mask, never formal QDW annotation.
                    for j in range(min(max(1,math.ceil((n-1)*.1)),max(0,n-1))):m[j]=True
                    masks.append(m)
                reserve_call(args.ledger,'nonformal_optimizer_update',f'{arm}/{profile_name}')
                check_deadline(args.deadline_unix,reserve=300)
                optimizer.zero_grad(set_to_none=True);torch.cuda.reset_peak_memory_stats();began=time.monotonic();audits=[]
                for i in range(0,32,2):
                    check_deadline(args.deadline_unix,reserve=150)
                    batch,labels,qmask=training_batch(rows[i:i+2],masks=masks[i:i+2])
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        logits=model(**batch,use_cache=False).logits
                        loss,audit=compute_loss(logits,labels,arm,denominator,
                            qdw_mask=qmask if arm=='QDW_v0' else None,attention_mask=batch['attention_mask'])
                    loss.backward();audits.append(audit)
                    del batch,labels,qmask,logits,loss
                norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.0,error_if_nonfinite=True)
                optimizer.step();torch.cuda.synchronize();receipt['nonformal_optimizer_updates']+=1
                entry=dict(arm=arm,seconds=time.monotonic()-began,profile=profile_name,
                    max_input_length=max(len(r['input_ids']) for r in rows),
                    max_response_length=max(len(r['response_ids']) for r in rows),
                    supervised_tokens=denominator,raw_input_tokens=sum(len(r['input_ids']) for r in rows),
                    optimizer_updates=1,grad_norm_before_clipping=float(norm),
                    max_memory_allocated=torch.cuda.max_memory_allocated(),max_memory_reserved=torch.cuda.max_memory_reserved(),
                    microbatch=2,gradient_accumulation=16,engineering_mask_only=arm=='QDW_v0',microbatch_audits=audits)
                receipt['training'].append(entry);write_json(out/f'{arm}_{profile_name}.json',entry)
                print(json.dumps(dict(event='engineering_update_done',arm=arm,profile=profile_name,seconds=entry['seconds'])),flush=True)
            if arm=='SFT':
                check_deadline(args.deadline_unix,reserve=360)
                store=CheckpointStore(out/'smoke_checkpoint',args.volume_root,phase=PHASE+'_engineering',
                    arm='SFT-smoke',config_hash=json_hash(identity))
                if host_available_bytes() < 48 * 2**30: raise RuntimeError('Insufficient host RAM for checked CPU roundtrip')
                rng=capture_rng();began=time.monotonic()
                saved=store.save(model.state_dict(),optimizer.state_dict(),step=1,token_step=denominator,
                    scheduler_state=dict(kind='discarded_engineering_constant_lr'),rng_state=rng,
                    metadata=dict(formal=False,discard_before_main=True),scientific=False,terminal=False)
                saved_seconds=time.monotonic()-began;began=time.monotonic();restored=store.load_latest()
                optimizer.zero_grad(set_to_none=True)
                model.load_state_dict(restored['model_state'],strict=True);optimizer.load_state_dict(restored['optimizer_state']);restore_rng(restored['rng_state'])
                for name, value in model.state_dict().items():
                    if not torch.equal(value.cpu(), restored['model_state'][name]):
                        raise ValueError('Live restored model differs: '+name)
                live_opt = optimizer.state_dict()
                for key, expected in restored['optimizer_state']['state'].items():
                    for name, value in expected.items():
                        actual=live_opt['state'][key][name]
                        if not _same(actual.cpu() if isinstance(actual,torch.Tensor) else actual,value):
                            raise ValueError('Live restored optimizer differs')
                if (not _same(live_opt['param_groups'],restored['optimizer_state']['param_groups']) or
                        not _same(capture_rng(),restored['rng_state'])):
                    raise ValueError('Restored optimizer groups/RNG differ')
                receipt['checkpoint_roundtrip']=dict(save_seconds=saved_seconds,load_seconds=time.monotonic()-began,
                    checkpoint=saved,step=restored['step'],token_step=restored['token_step'],formal=False,
                    roundtrip_verified=True)
                del restored,live_opt;write_json(out/'checkpoint_roundtrip.json',receipt['checkpoint_roundtrip'])
                receipt['engineering_checkpoint_discard']=store.discard_engineering(saved,
                    roundtrip_receipt=receipt['checkpoint_roundtrip'])
                print(json.dumps(dict(event='verified_smoke_roundtrip_and_discard')),flush=True)
            drop_model(model,optimizer);del optimizer,model;gc.collect();torch.cuda.empty_cache()
        check_deadline(args.deadline_unix,reserve=300)
        model=load_base(base,training=False)
        for idx,row in enumerate(inputs['train_profile']):
            check_deadline(args.deadline_unix,reserve=180)
            reserve_call(args.ledger,'annotation_forward',row['id']+'/full')
            full,fstats=gold_forward(model,row)
            write_json(out/f'annotation_{idx:04d}.full.json',dict(id=row['id'],identity=identity,logp=full,stats=fstats))
            reserve_call(args.ledger,'annotation_forward',row['id']+'/blank')
            blank,bstats=gold_forward(model,row,blank=True)
            write_json(out/f'annotation_{idx:04d}.blank.json',dict(id=row['id'],identity=identity,logp=blank,stats=bstats))
            selected=select_qdw_tokens(row['response'],row['response_ids'],row['response_offsets'],full,blank,
                blank_response_ids=row['blank_input_ids'][row['blank_response_start']:],special_ids=tokenizer.all_special_ids,
                full_prefix_length=row['response_start'],blank_prefix_length=row['blank_response_start'])
            record=dict(id=row['id'],identity=identity,encoded_sha256=json_hash(row),annotation=selected,
                full=fstats,blank=bstats,scientific_annotation_reusable_under_exact_identity=True)
            write_json(out/f'annotation_{idx:04d}.json',record);receipt['annotations'].append(dict(id=row['id'],full=fstats,blank=bstats))
        receipt['generation']=greedy_profile(model,tokenizer,inputs['dev_profile'],out/'base_dev32',identity,args.deadline_unix,ledger=args.ledger)
        drop_model(model);del model;gc.collect();torch.cuda.empty_cache()
        if receipt['nonformal_optimizer_updates']>8:raise AssertionError('Nonformal update cap exceeded')
        receipt['all_training_state_discarded_before_scientific_annotations']=True
        status='engineering_preflight_completed_not_main_admission'
    except Exception as error:
        receipt.update(error_type=type(error).__name__,error_message=str(error))
        raise
    finally:
        receipt.update(status=status,wall_seconds=time.monotonic()-started,finished_at_utc=datetime.now(timezone.utc).isoformat(),
            formal_optimizer_updates=0,main_grid_admitted=False)
        write_json(out/'PREFLIGHT_RECEIPT.json',receipt)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',required=True);p.add_argument('--inputs',required=True);p.add_argument('--output',required=True)
    p.add_argument('--volume-root',action='append',required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--deadline-unix',type=float,required=True);p.add_argument('--ledger',required=True)
    print(json.dumps(run(p.parse_args()),sort_keys=True))
