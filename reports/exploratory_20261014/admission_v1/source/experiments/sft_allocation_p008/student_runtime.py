"""Prepared dynamic-horizon P008 SFT/base worker logic, without cloud dispatch.

Uses the unchanged HF forward/loss/stop/checkpoint primitives. Does not use the
historical hardcoded256-step plan or change any P007 data/source.
"""
from pathlib import Path
from collections import Counter
import json
from experiments.sft_allocation_midpoint import runtime as rt
from experiments.sft_allocation_midpoint.common import read,dump,verify,sha,digest
from src.sft_data import read_jsonl,budget_report
from .contract import lrs,BASE_UPDATES,BASE_TARGETS

EVAL=dict(max_new_tokens=512,max_length=2048,eval_batch_size=16)


def validate_plan(rows,encoded,plan,config):
    u=config['updates'];multiple=config['training_multiple'];targets=config['targets']
    if u!=BASE_UPDATES*multiple or multiple not in (1,4,8):raise ValueError('Unregistered training horizon')
    nominal=BASE_TARGETS*multiple
    if not nominal-nominal//1000<=targets<=nominal:raise ValueError('Target tolerance differs')
    if config['seed']!=17 or plan['lrs']!=lrs(u) or len(plan['updates'])!=u:
        raise ValueError('Fixed LR,seed or update count differs')
    if plan['row_path_ids']!=[r['path_id'] for r in rows] or len(set(plan['row_path_ids']))!=len(rows):
        raise ValueError('Whole inventory/order differs')
    if any(not b or any(type(i)is not int or not 0<=i<len(rows) for i in b) for b in plan['updates']):
        raise ValueError('Empty/foreign row in update')
    count=Counter(i for b in plan['updates'] for i in b);all_counts=[count[i] for i in range(len(rows))]
    if (max(all_counts)-min(all_counts)>1 or plan['row_exposures']!=all_counts
         or plan['zero_exposure_answers']!=sum(n==0 for n in all_counts)):
        raise ValueError('Balanced complete-answer exposure differs')
    budget=budget_report(encoded,plan['updates'],1)
    if budget['supervised_response_tokens']!=targets or budget['optimizer_updates']!=u or budget['padding_tokens']!=0:
        raise ValueError('Full-answer dose differs')
    if plan['supervised_targets']!=targets or not plan['targets_are_frozen_before_student_scores']:
        raise ValueError('Plan is not bound to pre-outcome common target')
    return budget


def run(assets,inputs,out,journal,identity):
    config=identity['config'];role=config['role'];inputs=Path(inputs)
    meta=read(inputs/'manifest.json');verify(inputs,meta['files'])
    if sha(inputs/'manifest.json')!=config['input_sha256']:raise ValueError('Published inputs changed')
    evaluation_rows=read_jsonl(inputs/'gsm8k_test1319.jsonl')
    if len(evaluation_rows)!=1319 or len({r['problem_id'] for r in evaluation_rows})!=1319:
        raise ValueError('Complete formal endpoint required')
    if role=='base':
        if config['updates']!=0 or config['targets']!=0:raise ValueError('Base cannot update')
        model,tok=rt.new_model(assets/'model',17,adapt=False)
        dump(out/'recipe.json',dict(identity=identity,eval=EVAL,training=False))
        evaluation=rt.evaluate(model,tok,evaluation_rows,out,'endpoint1319',journal,config=EVAL)
        return dict(role='base',updates=0,targets=0,endpoint=evaluation,checkpoint_selection=False)
    if role not in ('main','bridge'):raise ValueError('Unknown role')
    model,tok=rt.new_model(assets/'model',17);rows=read_jsonl(inputs/config['rows_file'])
    encoded=rt.encode(rows,tok);plan=read(inputs/config['plan_file']);budget=validate_plan(rows,encoded,plan,config)
    gate=read(inputs/'COMMON_PLAN_GATE.json')
    if gate['plans'][config['run_id']]!=sha(inputs/config['plan_file']) or gate['common_targets'][str(config['training_multiple'])]!=config['targets']:
        raise ValueError('Common pre-outcome plan gate differs')
    dump(out/'recipe.json',dict(identity=identity,budget=budget,schedule=plan['updates'],lrs=plan['lrs'],
        row_path_ids=plan['row_path_ids'],row_exposures=plan['row_exposures'],zero_exposure_answers=plan['zero_exposure_answers'],eval=EVAL))
    optimizer=rt.optimizer_for(model)
    forensic_steps=(1024,2048) if config['updates']==2048 else (config['updates'],)
    history,targets,processed=rt.train(model,tok,optimizer,encoded,plan['updates'],plan['lrs'],out,journal,identity,save_steps=forensic_steps)
    if len(history)!=config['updates'] or targets!=config['targets']:raise ValueError('Realized dose differs')
    evaluation=rt.evaluate(model,tok,evaluation_rows,out,'endpoint1319',journal,config=EVAL)
    return dict(role=role,run_id=config['run_id'],updates=len(history),targets=targets,processed_tokens=processed,
        endpoint=evaluation,terminal_step=config['updates'],checkpoint_selection=False,
        acquisition_draw=config['draw'],student_seed=17,acquired_answers=len(rows),
        exposed_answers=sum(n>0 for n in plan['row_exposures']))
