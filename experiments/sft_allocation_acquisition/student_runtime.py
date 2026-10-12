"""P007B terminal-only SFT on fully audited procured data; no dispatch or search."""
from pathlib import Path
import json
from experiments.sft_allocation_midpoint import runtime as rt, checkpoint as ck
from experiments.sft_allocation_midpoint.common import dump,read,verify,digest
from src.sft_data import budget_report,read_jsonl

EVAL=dict(max_new_tokens=512,max_length=2048,eval_batch_size=16)
CELLS=('breadth_p0','depth_p0','breadth_p4','depth_p4')


def preflight_inputs(inputs,tok,identity):
    """Recompute ALL eight plans before any one student output/update."""
    verify(inputs,read(inputs/'manifest.json')['files'])
    result={}
    for cell in CELLS:
        rows=read_jsonl(inputs/f'{cell}_train.jsonl')
        encoded=rt.encode(rows,tok)
        for seed in (17,23):
            plan=read(inputs/f'{cell}_seed{seed}.json')
            budget=budget_report(encoded,plan['updates'],1)
            if (json.loads(json.dumps(budget,allow_nan=False))!=plan['budget'] or budget['optimizer_updates']!=256 or
                    budget['supervised_response_tokens']!=524288 or budget['padding_tokens']!=0):
                raise ValueError('One or more cell budgets differ; no one-sided repair')
            from collections import Counter
            count=Counter(i for batch in plan['updates'] for i in batch)
            if set(count)!=set(range(len(rows))) or max(count.values())-min(count.values())>1:
                raise ValueError('Every accepted answer needs balanced complete exposure')
            result[f'{cell}_s{seed}']=dict(budget=budget,rows=len(rows),parents=len({r['problem_id'] for r in rows}))
    return result


def run(base_assets,inputs,out,journal,identity):
    cfg=identity['config'];cell=cfg['cell'];seed=cfg['seed']
    if cell not in CELLS or seed not in (17,23) or cfg['eval']!=EVAL:
        raise ValueError('Unapproved cell/seed/decoder')
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(base_assets/'model',local_files_only=True,use_fast=True)
    tok.pad_token=tok.eos_token
    all_budgets=preflight_inputs(inputs,tok,identity)
    dump(out/'all_cells_budget_preflight.json',all_budgets)
    rows=read_jsonl(inputs/f'{cell}_train.jsonl')
    plan=read(inputs/f'{cell}_seed{seed}.json')
    endpoint=read_jsonl(inputs/'gsm8k_test1319.jsonl')
    if len(endpoint)!=1319 or len({r['problem_id'] for r in endpoint})!=1319:
        raise ValueError('Standard benchmark roster differs')
    model,tok=rt.new_model(base_assets/'model',seed)
    encoded=rt.encode(rows,tok);opt=rt.optimizer_for(model);schedule=plan['updates']
    rates=rt.frozen_main_lrs(identity)
    dump(out/'recipe.json',dict(identity=identity,cell=cell,seed=seed,lrs=rates,eval=EVAL,budget=plan['budget'],
        terminal_only=True,intermediate_generation_count=0))
    ck.save(out,ck.snapshot(model,opt,identity,0,0,0,rates,schedule),journal.commit)
    history,targets,processed=rt.train(model,tok,opt,encoded,schedule,rates,out,journal,identity,
                                     save_steps=set(range(32,257,32)))
    if targets!=524288 or len(history)!=256:raise ValueError('Student dose differs')
    endpoint_result=rt.evaluate(model,tok,endpoint,out,'endpoint1319',journal,config=EVAL)
    return dict(status='completed',cell=cell,seed=seed,committed_updates=256,supervised_tokens=targets,
        processed_tokens=processed,physical_generated_outputs=1319,endpoint=endpoint_result,
        train_seconds=sum(r['seconds'] for r in history),budget=plan['budget'],
        interpretation='One procurement draw, two training seeds; official test previously researcher-observed, not pristine confirmation.')
