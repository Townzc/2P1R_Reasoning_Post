"""E012 model worker. Enter only through the bounded, explicit one-arm launcher."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import signal
import time

from src.relation_diagnostic_execution import (RELEASE,load_inputs,provenance,
    account,reference_record,aggregate_references,result_metrics,score_tokens)
from src.relation_diagnostic_verifier import summarize
from src.relation_engineering import dump
from src.relation_experiment import accumulate_gradients,profile
from src.sft_data import collate,prefix,sha256_file


def generate(model, tokenizer, rows, cfg, output_path):
    import torch
    from transformers import GenerationConfig
    model.eval(); predictions = []
    known = frozenset(tokenizer.get_vocab().values())
    settings = GenerationConfig(do_sample=False,num_beams=1,max_new_tokens=cfg['max_new_tokens'],
        eos_token_id=tokenizer.eos_token_id,pad_token_id=tokenizer.pad_token_id,use_cache=True)
    with Path(output_path).open('x') as f:
        for start in range(0,len(rows),cfg['eval_batch_size']):
            group = rows[start:start+cfg['eval_batch_size']]
            prompts = [tokenizer(prefix(r['prompt']),add_special_tokens=False)['input_ids'] for r in group]
            width = max(map(len,prompts))
            if width+cfg['max_new_tokens']>cfg['max_length']: raise ValueError('Generation context cap exceeded')
            inputs = torch.tensor([[tokenizer.pad_token_id]*(width-len(x))+x for x in prompts],device='cuda')
            masks = torch.tensor([[0]*(width-len(x))+[1]*len(x) for x in prompts],device='cuda')
            with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
                output = model.generate(input_ids=inputs,attention_mask=masks,generation_config=settings)
            for row, stream in zip(group,output[:,width:].tolist()):
                eos = tokenizer.eos_token_id in stream
                ids = stream[:stream.index(tokenizer.eos_token_id)+1] if eos else stream
                raw = tokenizer.decode(ids[:-1] if eos else ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
                prediction = {**row,'generated_ids':ids,'generated_tokens':len(ids),'text':raw,
                    'score':score_tokens(row,raw,ids,eos,not eos and len(ids)==cfg['max_new_tokens'],known)}
                predictions.append(prediction); f.write(json.dumps(prediction,allow_nan=False)+'\n'); f.flush()
            del inputs,masks,output
    return predictions


def reference_batch(model, rows, encoded, pad_id, *, device='cuda'):
    """Return per-target CE/top-one IDs; CPU is for synthetic numerical tests only."""
    import torch
    import torch.nn.functional as F
    batch = {k:v.to(device) for k,v in collate(encoded,pad_id).items()}
    context = torch.autocast('cuda',dtype=torch.bfloat16) if str(device).startswith('cuda') else nullcontext()
    with torch.inference_mode(),context:
        output = model(input_ids=batch['input_ids'],attention_mask=batch['attention_mask'],use_cache=False)
        targets = batch['labels'][:,1:]; valid = targets!=-100
        active = output.logits[:,:-1][valid].float()
        losses = F.cross_entropy(active,targets[valid],reduction='none').cpu().tolist()
        predicted = active.argmax(dim=-1).cpu().tolist()
    records = []; cursor = 0
    for row,enc in zip(rows,encoded):
        n = enc['n_supervised']
        records.append(reference_record(row,enc,predicted[cursor:cursor+n],losses[cursor:cursor+n]))
        cursor += n
    if cursor!=len(losses): raise ValueError('Teacher-forced target partition mismatch')
    return records


def measure_references(model, tokenizer, data, output_path):
    model.eval(); records = []; micro = data['cfg']['microbatch_size']
    vocab_size = model.config.vocab_size
    with Path(output_path).open('x') as f:
        for start in range(0,len(data['train']),micro):
            part = reference_batch(model,data['train'][start:start+micro],data['encoded'][start:start+micro],tokenizer.pad_token_id)
            for rec in part: f.write(json.dumps(rec,allow_nan=False)+'\n'); f.flush()
            records.extend(part)
    aggregate_references(records,data['train'],data['encoded'],vocab_size)
    return records


def main():
    p = argparse.ArgumentParser(); p.add_argument('--snapshot',required=True)
    p.add_argument('--arm',required=True); p.add_argument('--preflight',required=True)
    args = p.parse_args()
    source = provenance(include_release=True)
    prepared = load_inputs(args.snapshot); data = prepared['arms'][args.arm]; cfg = data['cfg']
    out = Path('runs')/cfg['run_id']
    if os.environ.get('CS294_BOUNDED_RUN_ID')!=cfg['run_id'] or not out.is_dir():
        raise ValueError('Mandatory bounded wrapper and unique run directory required')
    if (out/'run_manifest.json').exists(): raise FileExistsError('Immutable diagnostic run already exists')
    preflight = json.loads(Path(args.preflight).read_text())
    if preflight['source_commit']!=source['source_commit'] or preflight['arm']!=cfg['arm'] or not preflight['server']['model']['all_files_verified']:
        raise ValueError('Missing matching published source/base/server preflight')
    tokenizer = prepared['tokenizer']; vocab_size = prepared['model_vocab_size']
    import torch
    from transformers import AutoModelForCausalLM
    if not torch.cuda.is_available(): raise ValueError('Registered model execution requires CUDA')
    torch.manual_seed(cfg['seed']); random.seed(cfg['seed']); torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    manifest = {**source,'phase':'E012','status':'running','config':cfg,
        'tokenizer':prepared['tokenizer_record'],'data_manifest_sha256':cfg['data_manifest_sha256'],
        'execution_release_sha256':sha256_file(RELEASE),'preflight_sha256':sha256_file(args.preflight),
        'server':preflight['server'],'model':prepared['tokenizer_record']['repo_id'],
        'model_revision':prepared['tokenizer_record']['revision'],'weights':'fresh_pinned_base',
        'parameter_dtype':'float32','autocast_dtype':'bfloat16','optimizer':'AdamW_foreach_false',
        'attention':'sdpa','gradient_checkpointing':'nonreentrant','tf32':False,
        'eos_token_id':tokenizer.eos_token_id,'pad_token_id':tokenizer.pad_token_id,
        'model_vocab_size':vocab_size,'tokenizer_size':len(tokenizer),
        'started_at_utc':datetime.now(timezone.utc).isoformat(),'holdout_access':False,
        'scientific_treatment_comparison':False}
    dump(out/'run_manifest.json',manifest); dump(out/'preflight.json',preflight)
    dump(out/'planned_budget.json',data['budget'])
    history = []; executed_schedule = []
    def stop(*_): raise TimeoutError('Bounded watchdog requested termination; no retry')
    signal.signal(signal.SIGTERM,stop); start = time.monotonic()
    try:
        model = AutoModelForCausalLM.from_pretrained(args.snapshot,dtype=torch.float32,
                    attn_implementation='sdpa',local_files_only=True).cuda()
        model.config.use_cache = False
        if model.get_output_embeddings().weight.shape[0]!=vocab_size:
            raise ValueError('Pinned output vocabulary differs from checkpoint')
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
        if any(p.dtype!=torch.float32 or not p.requires_grad for p in model.parameters()):
            raise ValueError('All original parameters must train in FP32')
        optimizer = torch.optim.AdamW(model.parameters(),lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'],
                                     betas=tuple(cfg['adam_betas']),eps=cfg['adam_eps'],foreach=False)
        baseline = generate(model,tokenizer,data['dev'],cfg,out/'base_dev.jsonl')
        dump(out/'baseline_metrics.json',summarize(data['dev'],[r['score'] for r in baseline]))
        torch.cuda.reset_peak_memory_stats()
        with (out/'train_history.jsonl').open('x') as f:
            for step,indices in enumerate(data['schedule'],1):
                model.train(); optimizer.zero_grad(set_to_none=True)
                torch.cuda.synchronize(); tick = time.perf_counter()
                batch_rows = [data['encoded'][i] for i in indices]
                nll = accumulate_gradients(model,batch_rows,tokenizer.pad_token_id,cfg['microbatch_size'],'cuda')
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(),cfg['grad_clip'])
                if not torch.isfinite(norm): raise FloatingPointError('Nonfinite gradient')
                optimizer.step(); torch.cuda.synchronize(); executed_schedule.append(list(indices))
                row = {'step':step,'row_indices':list(indices),'response_nll':nll,'grad_norm':norm.item(),
                    'supervised_tokens':sum(r['n_supervised'] for r in batch_rows),
                    'processed_tokens':sum(r['n_processed'] for r in batch_rows),
                    'seconds':time.perf_counter()-tick,'peak_allocated_mib':torch.cuda.max_memory_allocated()/1024**2,
                    'peak_reserved_mib':torch.cuda.max_memory_reserved()/1024**2}
                history.append(row); f.write(json.dumps(row,allow_nan=False)+'\n'); f.flush()
                if step==1 or step%32==0: print(json.dumps(row),flush=True)
        dump(out/'throughput.json',profile(history,cfg))
        dump(out/'actual_budget.json',account(data['train'],data['encoded'],executed_schedule,cfg['microbatch_size']))
        model.gradient_checkpointing_disable()
        training = generate(model,tokenizer,data['train'],cfg,out/'final_train.jsonl')
        dev = generate(model,tokenizer,data['dev'],cfg,out/'final_dev.jsonl')
        references = measure_references(model,tokenizer,data,out/'train_reference_tokens.jsonl')
        metrics = result_metrics(data,history,baseline,training,dev,references,vocab_size)
        dump(out/'evaluation_metrics.json',metrics)
        checkpoint = out/'checkpoint_final'
        model.save_pretrained(checkpoint,safe_serialization=True); tokenizer.save_pretrained(checkpoint)
        dump(out/'checkpoint_manifest.json',{'kind':'model_weights_only_not_optimizer_or_rng_resume',
            'files':{p.name:{'sha256':sha256_file(p),'bytes':p.stat().st_size} for p in sorted(checkpoint.iterdir()) if p.is_file()}})
        dump(out/'metrics.json',metrics); manifest['status'] = 'completed'
    except Exception as exc:
        manifest.update(status='failed',exception_type=type(exc).__name__,exception=str(exc)); raise
    finally:
        if not (out/'actual_budget.json').exists():
            dump(out/'partial_budget.json',account(data['train'],data['encoded'],executed_schedule,cfg['microbatch_size']))
        manifest.update(steps_completed=len(history),wall_seconds=time.monotonic()-start,
            finished_at_utc=datetime.now(timezone.utc).isoformat(),peak_allocated_mib=torch.cuda.max_memory_allocated()/1024**2)
        temp = out/'run_manifest.tmp'; dump(temp,manifest); temp.replace(out/'run_manifest.json')


if __name__=='__main__': main()
