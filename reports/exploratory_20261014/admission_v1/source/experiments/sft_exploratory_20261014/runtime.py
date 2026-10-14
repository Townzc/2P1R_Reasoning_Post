"""Three finite exploratory roles; old training, parser and optimizer are reused."""
from pathlib import Path
from collections import Counter
import json
import math
import time
from experiments.sft_allocation_midpoint import runtime as rt
from experiments.sft_allocation_midpoint.common import read, dump, sha, verify
from experiments.sft_allocation_p008.frozen_student_plan import validate_plan
from analyses.completion_contract import first_stop, completion_score
from analyses.gsm8k_answer_audit import score
from src.sft_data import read_jsonl

EVAL = dict(max_new_tokens=512, max_length=2048, eval_batch_size=16)


def reference_event(tokens, tok, eos_ids):
    # C020 independently scans all decoded prefixes. Substituting only native
    # terminal IDs leaves the visible text unchanged and permits both official
    # Instruct EOS IDs; the original single-EOS student contract is unchanged.
    normalized = [tok.eos_token_id if t in eos_ids else t for t in tokens]
    return first_stop(normalized, lambda x:tok.decode(x,skip_special_tokens=True,
        clean_up_tokenization_spaces=False), tok.eos_token_id, 512,
        (set(tok.all_special_ids)-set(eos_ids)) | {t for t in tokens if t>=len(tok)})


def audit_batch(raw, records, rows, prompts, tok, eos_ids):
    if (len(records) != len(rows) or len(raw['batch_output_ids']) != len(rows) or
            len(prompts) != len(rows) or len(raw['events']) != len(rows)):
        raise ValueError('Incomplete original batch')
    ids = [p['input_ids'] for p in prompts]
    width = max(map(len, ids))
    if raw['input_ids'] != ids or raw['prompt_width'] != width or raw['problem_ids'] != [r['problem_id'] for r in rows]:
        raise ValueError('Frozen prompts/identities differ')
    steps = len(raw['batch_output_ids'][0])
    if not 0 < steps <= 512 or width + steps > 2048:
        raise ValueError('Generation/context cap differs')
    for row, p, tokens, record, event in zip(rows,prompts,raw['batch_output_ids'],records,raw['events']):
        if p['problem_id'] != row['problem_id'] or any(record.get(k)!=v for k,v in row.items()):
            raise ValueError('Original endpoint row differs')
        if len(tokens)!=steps or any(type(t)is not int or t<0 for t in tokens):
            raise ValueError('Raw output shape differs')
        expected=reference_event(tokens,tok,eos_ids);n=expected['retained_tokens']
        if event!=expected or record['stop']!=expected or any(t!=tok.eos_token_id for t in tokens[n:]):
            raise ValueError('Independent native stop/padding differs')
        visible=tokens[:n-1] if expected['actual_eos_at_stop'] else tokens[:n]
        text=tok.decode(visible,skip_special_tokens=False,clean_up_tokenization_spaces=False)
        if (record['generated_ids']!=tokens[:n] or record['batch_output_ids']!=tokens or
                record['generated_tokens']!=n or record['raw_text']!=text or
                record['batch_generated_steps']!=steps or record['post_stop_padding_tokens']!=steps-n or
                record['padded_prompt_width']!=width or
                record['generation_batch_seconds']!=raw['seconds'] or
                record['task_score']!=completion_score(row,expected) or
                record['legacy_marked_prefix_score']!=score(row,text,expected['actual_eos_at_stop'],expected['stop_reason']=='length_cap')):
            raise ValueError('Raw/score correspondence differs')
        if not math.isfinite(raw['seconds']) or raw['seconds']<=0:
            raise ValueError('Invalid actual batch duration')
        if expected['stop_reason']=='length_cap' and record['task_score']['task_answer_correct']:
            raise ValueError('Capped completion cannot be counted correct')
    return True


def evaluate(model,tok,rows,prompts,out,journal,eos_ids):
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
    model.eval();predictions=[]
    for start in range(0,len(rows),16):
        part=rows[start:start+16];pp=prompts[start:start+16]
        ids=[r['input_ids'] for r in pp];width=max(map(len,ids))
        if width+512>2048:raise ValueError('No context truncation')
        unit=f'endpoint1319_batch_{start:04d}'
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
        audit_batch(raw,records,part,pp,tok,eos_ids)
        journal.end(unit,dict(count=len(records),raw_sha256=sha(rawpath),scored_sha256=sha(scored)))
        journal.commit();predictions.extend(records)
        print(json.dumps(dict(evaluation='endpoint1319',completed=len(predictions),batch_seconds=seconds)),flush=True)
        del inputs,masks,output
    summary=dict(n=len(predictions),correct=sum(r['task_score']['task_answer_correct'] for r in predictions),
        parsed=sum(r['task_score']['marked']['status']=='parsed' for r in predictions),
        stop_reasons=dict(Counter(r['stop']['stop_reason'] for r in predictions)),
        generated_tokens=sum(r['generated_tokens'] for r in predictions),
        padded_tokens=sum(r['batch_generated_steps'] for r in predictions),
        question_correct={r['problem_id']:r['task_score']['task_answer_correct'] for r in predictions})
    dump(folder/'summary.json',summary);journal.commit();return summary


def run(assets,inputs,out,journal,identity,instruct_path=None):
    config=identity['config'];kind=config['run_id'];inputs=Path(inputs)
    meta=read(inputs/'manifest.json');verify(inputs,meta['files'])
    if sha(inputs/'manifest.json')!=config['input_sha256']:raise ValueError('Input release differs')
    rows=read_jsonl(inputs/'gsm8k_test1319.jsonl')
    if len(rows)!=1319 or len({r['problem_id'] for r in rows})!=1319:raise ValueError('Full endpoint required')
    is_student=kind=='wrong_teacher_t1'
    model_path=instruct_path if kind=='instruct_0shot' else Path(assets)/'model'
    model,tok=rt.new_model(model_path,17,adapt=is_student)
    from .contract import prompt_ids
    examples=read(inputs/'dev_examples.json');prompts=read(inputs/(kind+'_prompts.json'))
    for r,p in zip(rows,prompts):
        if p!=dict(problem_id=r['problem_id'],input_ids=prompt_ids(kind,r,tok,examples)):
            raise ValueError('Runtime tokenizer/chat serialization differs')
    if len(prompts)!=1319:raise ValueError('Missing prompt roster')
    eos_ids=[151645,151643] if kind=='instruct_0shot' else [tok.eos_token_id]
    recipe=dict(identity=identity,eval=EVAL,eos_ids=eos_ids,pad_token_id=tok.eos_token_id,
        greedy=True,repetition_penalty=1.0,parser='marked_answer_v1',training=is_student,
        input_prompt_file=kind+'_prompts.json',exploratory=True,preregistered=False)
    targets=processed=updates=0
    if is_student:
        trainrows=read_jsonl(inputs/'wrong_teacher.jsonl');encoded=rt.encode(trainrows,tok)
        plan=read(inputs/'wrong_teacher_t1_plan.json');budget=validate_plan(trainrows,encoded,plan,config)
        recipe.update(budget=budget,schedule=plan['updates'],lrs=plan['lrs'],row_path_ids=plan['row_path_ids'],
            row_exposures=plan['row_exposures'],zero_exposure_answers=plan['zero_exposure_answers'])
        dump(Path(out)/'recipe.json',recipe)
        optimizer=rt.optimizer_for(model);journal.configure_training(encoded,plan['updates'],plan['lrs'])
        history,targets,processed=rt.train(model,tok,optimizer,encoded,plan['updates'],plan['lrs'],out,journal,identity,save_steps=(256,))
        updates=len(history)
        if updates!=256 or targets!=524287:raise ValueError('Authorized dose differs')
        journal.assert_training_complete()
    else:
        if config['updates']!=0 or config['targets']!=0:raise ValueError('Evaluation only')
        dump(Path(out)/'recipe.json',recipe)
    result=evaluate(model,tok,rows,prompts,out,journal,eos_ids)
    return dict(run_id=kind,updates=updates,targets=targets,processed_tokens=processed,
        endpoint=result,checkpoint_selection=False,exploratory=True,preregistered=False)
