"""Future P008 block-journal worker; scientific execution matches frozen run().

The two explicit journal hooks are the only AST changes to the old run body.
The original student_runtime.py remains in the live pool source, unchanged.
"""
from pathlib import Path
from experiments.sft_allocation_midpoint import runtime as rt
from experiments.sft_allocation_midpoint.common import read,dump,verify,sha
from src.sft_data import read_jsonl
from .frozen_student_plan import EVAL,validate_plan


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
    journal.configure_training(encoded,plan['updates'],plan['lrs'])
    history,targets,processed=rt.train(model,tok,optimizer,encoded,plan['updates'],plan['lrs'],out,journal,identity,save_steps=forensic_steps)
    if len(history)!=config['updates'] or targets!=config['targets']:raise ValueError('Realized dose differs')
    journal.assert_training_complete()
    evaluation=rt.evaluate(model,tok,evaluation_rows,out,'endpoint1319',journal,config=EVAL)
    return dict(role=role,run_id=config['run_id'],updates=len(history),targets=targets,processed_tokens=processed,
        endpoint=evaluation,terminal_step=config['updates'],checkpoint_selection=False,
        acquisition_draw=config['draw'],student_seed=17,acquired_answers=len(rows),
        exposed_answers=sum(n>0 for n in plan['row_exposures']))
