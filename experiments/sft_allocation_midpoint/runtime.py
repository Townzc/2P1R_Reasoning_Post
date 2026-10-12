"""Finite SFT runner. No dispatch, hidden retries, per-arm search or cleanup."""
from collections import Counter
from pathlib import Path
import importlib.metadata
import json
import math
import random
import time
from .common import dump,read,digest,sha,manifest,verify
from . import checkpoint as ck
from src.sft_data import read_jsonl,encode_row,collate,shifted_loss_sum,prefix,update_schedule,budget_report


VERSIONS={'torch':'2.8.0+cu128','transformers':'4.56.2','peft':'0.17.1',
          'tokenizers':'0.22.1','accelerate':'1.10.1','numpy':'2.3.2','safetensors':'0.6.2'}
TARGETS=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj']
EVAL=dict(max_new_tokens=512,max_length=2048,eval_batch_size=8)


def lrs():
    return [1e-4*(i+1)/16 if i<16 else 1e-5+(1e-4-1e-5)*.5*(1+math.cos(math.pi*(i-15)/240))
            for i in range(256)]


def seed_all(seed):
    import torch,numpy as np
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)


def environment():
    import torch,subprocess
    actual={name:importlib.metadata.version(name) for name in VERSIONS}
    if actual!=VERSIONS:raise ValueError('Pinned software versions differ: '+repr(actual))
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise ValueError('One CUDA GPU required')
    name=torch.cuda.get_device_name(0)
    if 'A100' not in name or torch.cuda.get_device_properties(0).total_memory<75*1024**3:
        raise ValueError('Requested A100-80GB was not provided')
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.backends.cudnn.benchmark=False;torch.use_deterministic_algorithms(True)
    return dict(versions=actual,gpu=name,cuda=torch.version.cuda,
                gpu_total_memory=torch.cuda.get_device_properties(0).total_memory,
                nvidia_smi=subprocess.check_output(['nvidia-smi'],text=True),deterministic_algorithms=True)


def new_model(path,seed,adapt=True):
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from peft import LoraConfig,get_peft_model,TaskType
    seed_all(seed)
    tok=AutoTokenizer.from_pretrained(path,local_files_only=True,use_fast=True)
    tok.pad_token=tok.eos_token
    model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,dtype=torch.float32,
                                            attn_implementation='sdpa').cuda()
    if adapt:
        model=get_peft_model(model,LoraConfig(r=16,lora_alpha=32,lora_dropout=0,bias='none',
                            target_modules=TARGETS,task_type=TaskType.CAUSAL_LM))
        if any(p.requires_grad!=('lora_' in n) for n,p in model.named_parameters()):
            raise ValueError('Unexpected adaptation scope')
    if any(p.dtype!=torch.float32 for p in model.parameters()):raise ValueError('FP32 parameters required')
    return model,tok


def optimizer_for(model):
    import torch
    return torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=1e-4,
                            betas=(.9,.999),eps=1e-8,weight_decay=0,foreach=False)


def encode(rows,tok):
    encoded=[encode_row(r,tok,2048) for r in rows]
    for r,e in zip(rows,encoded):
        if 'source' in r and any(r['source'][k]!=e[k] for k in ('n_supervised','n_processed','n_prompt')):
            raise ValueError('Retokenized training row differs')
    return encoded


def nll(model,encoded,tok,check):
    import torch
    total=0.;count=0;model.eval()
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
        for r in encoded:
            check();b={k:v.cuda() for k,v in collate([r],tok.pad_token_id).items()}
            loss=shifted_loss_sum(model(input_ids=b['input_ids'],attention_mask=b['attention_mask'],use_cache=False).logits,b['labels'])
            total+=loss.item();count+=r['n_supervised']
    if not math.isfinite(total):raise ValueError('Nonfinite NLL')
    return dict(loss_sum=total,tokens=count,n=len(encoded),nll=total/count)


def gradients(model,rows,tok,device='cuda'):
    import torch
    from contextlib import nullcontext
    denominator=sum(r['n_supervised'] for r in rows);total=0.
    if denominator<=0:raise ValueError('No supervised targets')
    for r in rows:
        b={k:v.to(device) for k,v in collate([r],tok.pad_token_id).items()}
        with torch.autocast('cuda',dtype=torch.bfloat16) if str(device).startswith('cuda') else nullcontext():
            out=model(input_ids=b['input_ids'],attention_mask=b['attention_mask'],use_cache=False)
            loss=shifted_loss_sum(out.logits,b['labels'])
        if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
        (loss/denominator).backward();total+=loss.item()
        del b,out,loss
    return total/denominator


class Journal:
    """Atomic remote intents precede work; completed outputs never authorize replay."""
    def __init__(self,out,key,store,commit,check):
        self.out=Path(out);self.key=key;self.store=store;self.commit=commit;self.check=check
    def begin(self,name,record):
        self.check()
        if not self.store.put(self.key+'/unit/'+name,record,skip_if_exists=True):
            raise RuntimeError('Work already attempted: '+name)
        dump(self.out/'intents'/(name+'.json'),record)
    def end(self,name,record):
        dump(self.out/'completed'/(name+'.json'),record)
        if not self.store.put(self.key+'/done/'+name,record,skip_if_exists=True):
            raise RuntimeError('Duplicate completion: '+name)


def train(model,tok,optimizer,encoded,schedule,rates,out,journal,identity,*,start=0,end=None,
          targets=0,processed=0,save_steps=(),callback=None):
    import torch
    end=len(schedule) if end is None else end
    history=[];params=[p for p in model.parameters() if p.requires_grad]
    for index in range(start,end):
        rows=[encoded[i] for i in schedule[index]];step=index+1;name=f'update_{step:04d}'
        intent=dict(step=step,indices=schedule[index],lr=rates[index],
                    supervised_tokens=sum(r['n_supervised'] for r in rows),processed_tokens=sum(r['n_processed'] for r in rows))
        journal.begin(name,intent);model.train();optimizer.zero_grad(set_to_none=True)
        torch.cuda.synchronize();tick=time.monotonic()
        loss=gradients(model,rows,tok);norm=torch.nn.utils.clip_grad_norm_(params,1.)
        if not torch.isfinite(norm) or not math.isfinite(loss):raise ValueError('Nonfinite update')
        for g in optimizer.param_groups:g['lr']=rates[index]
        optimizer.step();torch.cuda.synchronize()
        targets+=intent['supervised_tokens'];processed+=intent['processed_tokens']
        record={**intent,'loss':loss,'gradient_norm':norm.item(),'seconds':time.monotonic()-tick,
                'cumulative_targets':targets,'cumulative_processed':processed,
                'peak_allocated_bytes':torch.cuda.max_memory_allocated()}
        journal.end(name,record);history.append(record)
        if step in save_steps:
            ck.save(out,ck.snapshot(model,optimizer,identity,step,targets,processed,rates,schedule),journal.commit)
        if callback and step in (64,128,256):
            rng=ck.rng_state();callback(step,model);ck.restore_rng(rng)
        if step%16==0 or step==1:print(json.dumps({'update':step,'loss':loss,'seconds':record['seconds']}),flush=True)
    optimizer.zero_grad(set_to_none=True)
    return history,targets,processed


def evaluate(model,tok,rows,out,name,journal):
    """Save backend outputs before scoring; audit first-stop semantics separately."""
    import torch
    from transformers import GenerationConfig,StoppingCriteriaList
    from analyses.e017_stopping import TaskBoundaryStop,prediction
    from analyses.e017_audit import audit_predictions
    folder=Path(out)/name;folder.mkdir(exist_ok=False);predictions=[];model.eval()
    cfg=EVAL
    settings=GenerationConfig(do_sample=False,num_beams=1,max_new_tokens=cfg['max_new_tokens'],
                              eos_token_id=tok.eos_token_id,pad_token_id=tok.eos_token_id,use_cache=True)
    for start in range(0,len(rows),cfg['eval_batch_size']):
        part=rows[start:start+cfg['eval_batch_size']];unit=f'{name}_batch_{start:04d}'
        ids=[tok(prefix(r['prompt']),add_special_tokens=False)['input_ids'] for r in part]
        width=max(map(len,ids))
        if width+cfg['max_new_tokens']>cfg['max_length']:raise ValueError('Context overflow; no truncation')
        journal.begin(unit,dict(problem_ids=[r['problem_id'] for r in part],count=len(part),config=cfg))
        inputs=torch.tensor([[tok.eos_token_id]*(width-len(x))+x for x in ids],device='cuda')
        masks=torch.tensor([[0]*(width-len(x))+[1]*len(x) for x in ids],device='cuda')
        stop=TaskBoundaryStop(tok,width,len(part),cfg['max_new_tokens']);tick=time.monotonic()
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
            output=model.generate(input_ids=inputs,attention_mask=masks,generation_config=settings,
                                  stopping_criteria=StoppingCriteriaList([stop]))
        torch.cuda.synchronize();seconds=time.monotonic()-tick
        if not torch.equal(inputs,output[:,:width]):raise ValueError('Generation changed prompt')
        outputs=output[:,width:].tolist()
        raw=dict(problem_ids=[r['problem_id'] for r in part],input_ids=ids,prompt_width=width,
                 batch_output_ids=outputs,events=stop.events,seconds=seconds)
        rawpath=folder/f'batch_{start:04d}_raw.json';dump(rawpath,raw);journal.commit()
        records=[prediction(row,tok,tokens,event,seconds,0,width) for row,tokens,event in zip(part,outputs,stop.events)]
        scored=folder/f'batch_{start:04d}_scored.jsonl'
        with scored.open('x') as f:
            for r in records:f.write(json.dumps(r,allow_nan=False)+'\n')
        audit_predictions(scored,part,tok,cfg)
        journal.end(unit,dict(count=len(records),raw_sha256=sha(rawpath),scored_sha256=sha(scored)))
        predictions.extend(records)
        print(json.dumps({'evaluation':name,'completed':len(predictions),'total':len(rows),'batch_seconds':seconds}),flush=True)
        del inputs,masks,output
    stats=dict(n=len(predictions),correct=sum(r['task_score']['task_answer_correct'] for r in predictions),
        parsed=sum(r['task_score']['marked']['status']=='parsed' for r in predictions),
        stop_reasons=dict(Counter(r['stop']['stop_reason'] for r in predictions)),
        generated_tokens=sum(r['generated_tokens'] for r in predictions),
        padded_tokens=sum(r['batch_generated_steps'] for r in predictions),
        question_correct={r['problem_id']:r['task_score']['task_answer_correct'] for r in predictions})
    dump(folder/'summary.json',stats);journal.commit();return stats


def engineering(assets,out,journal,identity):
    import torch
    inputs=Path(assets)/'inputs';rows=read_jsonl(inputs/'repeat_train.jsonl')[:32]
    observed=read_jsonl(inputs/'observed80.jsonl')
    model,tok=new_model(Path(assets)/'model',20261012);encoded=encode(rows,tok);opt=optimizer_for(model)
    schedule=update_schedule(32,256,4,20261012);rates=[1e-4]*256
    dump(Path(out)/'recipe.json',dict(identity=identity,schedule=schedule,lrs=rates,eval=EVAL,seed=20261012,
         train_ids=[r['problem_id'] for r in rows],trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad)))
    before=nll(model,encoded,tok,journal.check)
    initial_train=evaluate(model,tok,rows,out,'initial_train32',journal)
    initial_dev=evaluate(model,tok,observed,out,'initial_observed80',journal)
    # Longest accepted sequence is a backward-only memory check, no optimizer update.
    allrows=[r for arm in ('repeat','solutions','mixed','breadth') for r in read_jsonl(inputs/f'{arm}_train.jsonl')]
    longest=max(encode(allrows,tok),key=lambda r:r['n_processed'])
    journal.begin('longest_backward',dict(n_processed=longest['n_processed'],n_supervised=longest['n_supervised'],optimizer_updates=0))
    model.train();opt.zero_grad(set_to_none=True);loss=gradients(model,[longest],tok)
    opt.zero_grad(set_to_none=True);journal.end('longest_backward',dict(loss=loss,optimizer_updates=0,
        peak_allocated_bytes=torch.cuda.max_memory_allocated()))
    ck.save(out,ck.snapshot(model,opt,identity,0,0,0,rates,schedule),journal.commit)
    history,targets,processed=train(model,tok,opt,encoded,schedule,rates,out,journal,identity,
                                   save_steps={2,4,32,64,96,128,160,192,224,256})
    after=nll(model,encoded,tok,journal.check)
    final_train=evaluate(model,tok,rows,out,'final_train32',journal)
    final_dev=evaluate(model,tok,observed,out,'final_observed80',journal)
    if len(history)!=256:raise ValueError('Incomplete engineering dose')
    fit=final_train['correct']>=24 and after['nll']<before['nll']*.5 and final_train['stop_reasons'].get('invalid_special_token',0)==0
    result=dict(status='completed',engineering_fit_gate=fit,initial_nll=before,final_nll=after,
        initial_train=initial_train,final_train=final_train,initial_dev=initial_dev,final_dev=final_dev,
        committed_updates=256,supervised_tokens=targets,processed_tokens=processed,
        physical_generated_outputs=224,longest_sequence=longest['n_processed'],
        train_seconds=sum(r['seconds'] for r in history),peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_reserved_bytes=torch.cuda.max_memory_reserved(),recovery_validation_pending=True,
        interpretation='Engineering memorization only. Observed-development changes do not select a scientific treatment or checkpoint.')
    return result


def resume_probe(assets,profile,out,journal,identity):
    inputs=Path(assets)/'inputs';rows=read_jsonl(inputs/'repeat_train.jsonl')[:32]
    state=ck.load(Path(profile)/'checkpoint_0002');expected=ck.load(Path(profile)/'checkpoint_0004')
    model,tok=new_model(Path(assets)/'model',20261012);opt=optimizer_for(model);encoded=encode(rows,tok)
    ck.restore(model,opt,state)
    history,targets,processed=train(model,tok,opt,encoded,state['schedule'],state['lrs'],out,journal,state['identity'],
        start=2,end=4,targets=state['supervised_tokens'],processed=state['processed_tokens'],save_steps={4})
    actual=ck.load(Path(out)/'checkpoint_0004')
    differences={k:ck.maximum_difference(actual[k],expected[k]) for k in ('adapter','optimizer')}
    exact=ck.same(actual,expected)
    passed=all(v<=1e-6 for v in differences.values()) and ck.same(actual['rng'],expected['rng'])
    for k in ('step','cursor','supervised_tokens','processed_tokens','identity','lrs','schedule','trainable_names'):
        passed=passed and ck.same(actual[k],expected[k])
    return dict(status='completed',recovery_gate=passed,bit_exact=exact,maximum_abs_difference=differences,
        committed_diagnostic_updates=2,scientific_updates=0,comparison_steps=[3,4],
        resume_source_sha256=sha(Path(profile)/'checkpoint_0002/state.pt'),
        expected_sha256=sha(Path(profile)/'checkpoint_0004/state.pt'),new_generations=0,
        tolerance=1e-6,scope='Independent fresh A100-80GB container; pinned deterministic kernels and fixed two-update trajectory.')


def main_train(assets,out,journal,identity,arm,seed):
    inputs=Path(assets)/'inputs';rows=read_jsonl(inputs/f'{arm}_train.jsonl')
    schedule_record=read(inputs/f'{arm}_seed{seed}.json');schedule=schedule_record['updates']
    model,tok=new_model(Path(assets)/'model',seed);opt=optimizer_for(model);encoded=encode(rows,tok)
    budget=budget_report(encoded,schedule,1)
    if budget['optimizer_updates']!=256 or budget['supervised_response_tokens']!=524288 or budget['padding_tokens']!=0:
        raise ValueError('Main dose differs from frozen exact contract')
    observed=read_jsonl(inputs/'observed80.jsonl');endpoint=read_jsonl(inputs/'endpoint431.jsonl')
    rates=lrs();dump(Path(out)/'recipe.json',dict(identity=identity,arm=arm,seed=seed,lrs=rates,eval=EVAL,budget=budget))
    before=nll(model,encoded[:32],tok,journal.check)
    curve={}
    def callback(step,model):curve[str(step)]=evaluate(model,tok,observed,out,f'observed80_step{step}',journal)
    ck.save(out,ck.snapshot(model,opt,identity,0,0,0,rates,schedule),journal.commit)
    history,targets,processed=train(model,tok,opt,encoded,schedule,rates,out,journal,identity,
        save_steps=set(range(32,257,32)),callback=callback)
    after=nll(model,encoded[:32],tok,journal.check)
    final=evaluate(model,tok,endpoint,out,'endpoint431',journal)
    return dict(status='completed',arm=arm,seed=seed,committed_updates=256,supervised_tokens=targets,
        processed_tokens=processed,physical_generated_outputs=671,endpoint=final,curve=curve,
        initial_reference_nll=before,final_reference_nll=after,train_seconds=sum(r['seconds'] for r in history),
        budget=budget,interpretation='Development result from one procurement draw, not pretraining-clean confirmation.')
