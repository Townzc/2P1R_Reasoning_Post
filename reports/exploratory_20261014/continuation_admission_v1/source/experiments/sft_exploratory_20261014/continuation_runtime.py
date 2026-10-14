"""Evaluation-only suffixes. No training call, new checkpoint or repeated prefix."""
from pathlib import Path
from collections import Counter
import json
import time
from experiments.sft_allocation_midpoint import runtime as rt, checkpoint as ck
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from experiments.sft_exploratory_20261014.runtime import EVAL
from experiments.sft_exploratory_20261014.cached_audit import audit_batch
from src.sft_data import read_jsonl

def evaluate(model,tok,rows,prompts,out,journal,eos_ids,prefix_records):
    import torch
    from transformers import GenerationConfig,StoppingCriteriaList
    from analyses.e017_stopping import TaskBoundaryStop,prediction

    class NativeStop(TaskBoundaryStop):
        def __call__(self,input_ids,scores,**kwargs):
            # Generated native alternate EOS becomes canonical only for the stop
            # detector; saved backend token IDs are never changed.
            observed=input_ids.clone()
            tail=observed[:,self.prompt_width:]
            for eos in eos_ids:
                if eos!=self.eos:tail.masked_fill_(tail==eos,self.eos)
            return super().__call__(observed,scores,**kwargs)

    folder=Path(out)/'endpoint1319';folder.mkdir(exist_ok=False)
    settings=GenerationConfig(do_sample=False,num_beams=1,max_new_tokens=512,
        eos_token_id=eos_ids,pad_token_id=tok.eos_token_id,repetition_penalty=1.0,use_cache=True)
    model.eval();predictions=list(prefix_records)
    offset=len(predictions)
    if offset not in (80,144,272):raise ValueError("Frozen suffix offset required")
    for start in range(offset,len(rows),16):
        part=rows[start:start+16];pp=prompts[start:start+16]
        ids=[r['input_ids'] for r in pp];width=max(map(len,ids))
        if width+512>2048:raise ValueError('No context truncation')
        unit=f'endpoint1319_batch_{start:04d}'
        batch_started=time.monotonic()
        journal.begin(unit,dict(problem_ids=[r['problem_id'] for r in part],count=len(part),config=EVAL))
        inputs=torch.tensor([[tok.eos_token_id]*(width-len(x))+x for x in ids],device='cuda')
        masks=torch.tensor([[0]*(width-len(x))+[1]*len(x) for x in ids],device='cuda')
        stop=NativeStop(tok,width,len(part),512);tick=time.monotonic()
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
            output=model.generate(input_ids=inputs,attention_mask=masks,generation_config=settings,
                stopping_criteria=StoppingCriteriaList([stop]))
        torch.cuda.synchronize();seconds=time.monotonic()-tick
        if not torch.equal(inputs,output[:,:width]):raise ValueError('Prompt changed')
        tokens=output[:,width:].tolist()
        raw=dict(problem_ids=[r['problem_id'] for r in part],input_ids=ids,prompt_width=width,
            batch_output_ids=tokens,events=stop.events,seconds=seconds)
        rawpath=folder/f'batch_{start:04d}_raw.json';dump(rawpath,raw);journal.commit()
        records=[prediction(r,tok,t,e,seconds,start//16,width) for r,t,e in zip(part,tokens,stop.events)]
        scored=folder/f'batch_{start:04d}_scored.jsonl'
        with scored.open('x') as f:
            for r in records:f.write(json.dumps(r,allow_nan=False)+'\n')
        audit_start=time.monotonic()
        audit_batch(raw,records,part,pp,tok,eos_ids)
        audit_seconds=time.monotonic()-audit_start
        journal.end(unit,dict(count=len(records),raw_sha256=sha(rawpath),scored_sha256=sha(scored)))
        journal.commit();predictions.extend(records)
        dump(folder/f'batch_{start:04d}_timing.json',dict(generation_seconds=seconds,
            independent_audit_seconds=audit_seconds,complete_batch_seconds=time.monotonic()-batch_started))
        journal.commit()
        print(json.dumps(dict(evaluation='endpoint1319',completed=len(predictions),batch_seconds=seconds)),flush=True)
        del inputs,masks,output
    summary=dict(n=len(predictions),correct=sum(r['task_score']['task_answer_correct'] for r in predictions),
        parsed=sum(r['task_score']['marked']['status']=='parsed' for r in predictions),
        stop_reasons=dict(Counter(r['stop']['stop_reason'] for r in predictions)),
        generated_tokens=sum(r['generated_tokens'] for r in predictions),
        padded_tokens=sum(r['batch_generated_steps'] for r in predictions),
        question_correct={r['problem_id']:r['task_score']['task_answer_correct'] for r in predictions})
    dump(folder/'summary.json',summary);journal.commit();return summary


def run(assets,inputs,parent,out,journal,config,spec):
    from experiments.sft_exploratory_20261014.contract import prompt_ids
    from experiments.sft_exploratory_20261014.continuation_prefix import inspect_prefix
    import torch
    inputs,parent,out=Path(inputs),Path(parent),Path(out)
    logical=config['logical_run'];proof=spec['prefix_proofs'][logical];binding=proof['binding']
    prefix_ledger=spec['parent_ledger']
    verified,prefix_records=inspect_prefix(parent,inputs,prefix_ledger,logical,spec['original_admission'])
    if verified!=binding or len(prefix_records)!=config['offset']:
        raise ValueError('Parent bytes/prefix binding differs')
    verify(inputs,read(inputs/'manifest.json')['files'])
    if sha(inputs/'manifest.json')!=config['input_sha256']:raise ValueError('Original inputs differ')
    student=logical=='wrong_teacher_t1'
    model_path=Path('/evidence/exploratory-20261014-r1/instruct_assets') if logical=='instruct_0shot' else Path(assets)/'model'
    if logical=='instruct_0shot':
        lock=read(inputs/'instruct_model_lock.json');verify(model_path,lock['metadata_files'])
        w=lock['weight']
        if (model_path/'model.safetensors').stat().st_size!=w['size'] or sha(model_path/'model.safetensors')!=w['sha256']:
            raise ValueError('Previously downloaded official weights differ; no redownload')
        dump(out/'official_model_readback.json',dict(lock=lock,download=read(model_path/'download_verified.json'),reused=True))
    model,tok=rt.new_model(model_path,17,adapt=student)
    if student:
        identity=read(parent/'recipe.json')['identity']
        state=ck.load(parent/'checkpoint_0256',identity)
        expected=spec['checkpoint_verified']
        if (read(parent/'checkpoint_0256/manifest.json')!=expected['manifest'] or
                state['step']!=256 or state['supervised_tokens']!=524287 or state['cursor']!=256):
            raise ValueError('Only original completed checkpoint256 permitted')
        optimizer=rt.optimizer_for(model)
        ck.restore(model,optimizer,state)
        params={n:p for n,p in model.named_parameters() if p.requires_grad}
        if any(not torch.equal(p.detach().cpu(),state['adapter'][n]) for n,p in params.items()):
            raise ValueError('Restored adapter bytes differ')
        dump(out/'CHECKPOINT_RESTORED.json',dict(passed=True,original_manifest=expected['manifest'],
             original_identity=identity,optimizer_exact=True,adapter_exact=True,rng_restored=True,
             new_training_updates=0,new_checkpoint_written=False))
        del optimizer,state
    rows=read_jsonl(inputs/'gsm8k_test1319.jsonl');examples=read(inputs/'dev_examples.json')
    prompts=read(inputs/(logical+'_prompts.json'))
    if len(rows)!=1319 or len(prompts)!=1319:raise ValueError('Full frozen endpoint required')
    for row,p in zip(rows,prompts):
        if p!=dict(problem_id=row['problem_id'],input_ids=prompt_ids(logical,row,tok,examples)):
            raise ValueError('Frozen prompt serialization differs')
    eos=[151645,151643] if logical=='instruct_0shot' else [tok.eos_token_id]
    dump(out/'recipe.json',dict(logical_run=logical,physical_run=config['run_id'],original_config=spec['original_admission']['configs'][logical],
         prefix_binding=binding,eval=EVAL,eos_ids=eos,pad_token_id=tok.eos_token_id,greedy=True,
         repetition_penalty=1.0,parser='marked_answer_v1',new_training_updates=0,
         training=False,exploratory=True,preregistered=False))
    journal.commit()
    endpoint=evaluate(model,tok,rows,prompts,out,journal,eos,prefix_records)
    return dict(run_id=config['run_id'],logical_run=logical,endpoint=endpoint,
                original_training_updates=256 if student else 0,original_training_targets=524287 if student else 0,
                new_training_updates=0,new_training_targets=0,saved_prefix_rows=config['offset'],
                newly_generated_rows=1319-config['offset'],parent_status='failed',
                exploratory=True,preregistered=False,checkpoint_selection=False)
