"""Exact arithmetic scoring and bounded raw-token sampling, independent of gold stops."""
from collections import Counter,defaultdict
from fractions import Fraction
import json
from pathlib import Path
import re
import time

from experiments.thursday_probe.common import dump, stamp, motifs
from src.countdown_smoke import safe_parse
from src.evaluation import score_text
from src.trace_audit import parse_expression, exact_value, audit_trace
from src.sft_data import prefix, read_jsonl


def score(row, event, forced_prefix=''):
    text=forced_prefix+event['answer_segment']
    complete=event['stop_reason'] in ('native_eos','new_problem_boundary')
    if row['task']=='construct':
        scored=score_text(text,row['numbers'],row['target'])
        trace=audit_trace(text,row['numbers'],row['target'])
        scored['trace_status']=trace['complete_trace_status']
        scored['interfaces']=dict(motifs(safe_parse(scored['expression']))) if scored['parsed'] else {}
    else:
        matches=list(re.finditer(r'(?m)^\s*Answer:\s*([^\n]+)',text))
        scored={'parsed':False,'correct':False,'trace_status':'not_certified','expression':None,'structure_id':None,'interfaces':{}}
        if len(matches)==1:
            try:
                value=exact_value(parse_expression(matches[0][1]))
                scored.update(parsed=True,correct=value==Fraction(row['answer']),expression=matches[0][1])
            except (ValueError,SyntaxError,RecursionError,ZeroDivisionError,OverflowError):
                pass
    scored['answer_correct_ignoring_stop']=bool(scored['correct'])
    scored['correct']=bool(scored['correct'] and complete)
    scored['completed']=complete
    scored['failure']=('none' if scored['correct'] else 'stop_'+event['stop_reason'] if not complete
                       else 'parse' if not scored['parsed'] else 'wrong_answer_or_resources')
    return scored


class GenerationBudget:
    def __init__(self,path,cap=8000,initial_used=160):
        self.path=Path(path)
        if self.path.exists(): raise FileExistsError('Never reset generation ledger')
        self.cap=cap; self.used=initial_used
        dump(self.path,{'cap':cap,'used':initial_used,'events':[{'name':'E018','reserved':initial_used} ]})

    def reserve(self,name,n):
        if type(n) is not int or n<=0 or self.used+n>self.cap: raise ValueError('Generation cap exceeded')
        record=json.loads(self.path.read_text())
        if record['used'] != self.used: raise ValueError('Generation ledger has another writer')
        if name in {e['name'] for e in record['events']}: raise ValueError('Do not replay a completed/reserved evaluation')
        self.used+=n; record['used']=self.used
        record['events'].append({'name':name,'reserved':n,'at_utc':stamp()})
        tmp=self.path.with_suffix('.tmp'); dump(tmp,record);tmp.replace(self.path)


def generate(model,tokenizer,rows,path,budget,samples=1,sampling=False,max_new_tokens=512,seed=2026091603,forced=None):
    import torch
    from transformers import GenerationConfig,StoppingCriteriaList
    from analyses.e017_stopping import TaskBoundaryStop
    from analyses.completion_contract import first_stop
    path=Path(path)
    if path.exists(): raise FileExistsError('No prediction overwrite')
    expanded=[(r,s) for r in rows for s in range(samples)]
    budget.reserve(path.name,len(expanded)); model.eval(); torch.manual_seed(seed)
    args={'do_sample':sampling,'num_beams':1,'max_new_tokens':max_new_tokens,
          'eos_token_id':tokenizer.eos_token_id,'pad_token_id':tokenizer.eos_token_id,'use_cache':True}
    if sampling: args.update(temperature=.7,top_p=.95,top_k=0)
    config=GenerationConfig(**args); dump(path.with_suffix('.generation.json'),{**args,'seed':seed,'samples':samples,'batch_size':8})
    records=[]
    with path.open('x') as f:
        for start in range(0,len(expanded),8):
            batch=expanded[start:start+8]
            prefixes=[(forced or {}).get(r['problem_id'],'') for r,_ in batch]
            ids=[tokenizer.encode(prefix(r['prompt'])+p,add_special_tokens=False) for (r,_),p in zip(batch,prefixes)]
            width=max(map(len,ids))
            if width+max_new_tokens>1024: raise ValueError('Generation context exceeded')
            inputs=torch.tensor([[tokenizer.eos_token_id]*(width-len(x))+x for x in ids],device='cuda')
            masks=torch.tensor([[0]*(width-len(x))+[1]*len(x) for x in ids],device='cuda')
            stopper=TaskBoundaryStop(tokenizer,width,len(batch),max_new_tokens)
            tick=time.monotonic()
            with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
                output=model.generate(input_ids=inputs,attention_mask=masks,generation_config=config,
                                      stopping_criteria=StoppingCriteriaList([stopper]))
            torch.cuda.synchronize(); seconds=time.monotonic()-tick
            if not torch.equal(output[:,:width],inputs): raise ValueError('Prompt prefix changed')
            all_ids=output[:,width:].tolist()
            decode=lambda ts:tokenizer.decode(ts,skip_special_tokens=True,clean_up_tokenization_spaces=False)
            for (r,s),p,tokens,event in zip(batch,prefixes,all_ids,stopper.events):
                # Reuse the independent whole-stream oracle, not the incremental stopper.
                oracle=first_stop(tokens,decode,tokenizer.eos_token_id,max_new_tokens,
                                  set(tokenizer.all_special_ids)|{t for t in tokens if t>=len(tokenizer)})
                if event!=oracle or any(t!=tokenizer.eos_token_id for t in tokens[event['retained_tokens']:]):
                    raise ValueError('Independent stop/padding audit failed')
                record={'problem_id':r['problem_id'],'sample_index':s,'task':r['task'],
                        'category':r.get('category'),'forced_prefix':p,'stop':event,
                        'generated_ids':tokens[:event['retained_tokens']],'batch_output_ids':tokens,
                        'prompt_ids':tokenizer.encode(prefix(r['prompt'])+p,add_special_tokens=False),
                        'batch_index':start//8,'batch_seconds':seconds,'score':score(r,event,p)}
                records.append(record); f.write(json.dumps(record,allow_nan=False)+'\n');f.flush()
            if len(records)%64==0 or len(records)==len(expanded):
                print(json.dumps({'evaluation':path.name,'generated':len(records),'reserved':len(expanded)}),flush=True)
            del inputs,masks,output
    return records


def summarize(records):
    if not records: raise ValueError('Empty result denominator')
    by=defaultdict(list)
    for r in records: by[r['problem_id']].append(r)
    return {'questions':len(by),'generations':len(records),
            'pass_at_1':sum(sum(r['score']['correct'] for r in rs)/len(rs) for rs in by.values())/len(by),
            'parse_fraction':sum(r['score']['parsed'] for r in records)/len(records),
            'completed_fraction':sum(r['score']['completed'] for r in records)/len(records),
            'stop_reasons':dict(Counter(r['stop']['stop_reason'] for r in records)),
            'failures':dict(Counter(r['score']['failure'] for r in records)),
            'trace_status':dict(Counter(r['score']['trace_status'] for r in records))}


def manipulation(control,bridge):
    stats={name:{cat:summarize([r for r in rs if r['category']==cat]) for cat in ('atomic','target','control')}
           for name,rs in [('C',control),('B',bridge)]}
    gains={cat:stats['B'][cat]['pass_at_1']-stats['C'][cat]['pass_at_1'] for cat in ('atomic','target','control')}
    specificity=gains['target']-(gains['atomic']+gains['control'])/2
    target=[stats[p]['target'] for p in ('C','B')]
    checks={'target_gain_at_least_10pp':gains['target']>=.1,'specificity_at_least_5pp':specificity>=.05,
        'no_floor_or_ceiling':all(.05<x['pass_at_1']<.95 for x in target),
        'parse_not_sole_advantage':abs(target[1]['parse_fraction']-target[0]['parse_fraction'])<=.05,
        'termination_not_sole_advantage':abs(target[1]['completed_fraction']-target[0]['completed_fraction'])<=.05}
    return {'stats':stats,'gains':gains,'specificity':specificity,'checks':checks,'passed':all(checks.values())}
