"""Prepared CPU-only complete-plan builder; never dispatches or reads model scores."""
from collections import Counter
import hashlib
import json
from .contract import BASE_TARGETS,BASE_UPDATES,run_roster,lrs
from .schedule import schedule


def common_plans(corpora,branch):
    """corpora maps (draw,budget,price,policy) to frozen encoded usable inventory.

    Rows must be stable-sorted before this function. Every target level is shared
    across both draws and all retained cells; all choices precede student scores.
    """
    roster=run_roster(*branch);expected={(r['draw'],r['budget_multiple'],r['price'],r['policy']) for r in roster}
    if set(corpora)!=expected:raise ValueError('All acquired corpora required before any student plan freeze')
    for key,rows in corpora.items():
        if not rows or len({r['path_id'] for r in rows})!=len(rows):raise ValueError('Empty/duplicate usable inventory')
        if any(r['n_supervised']<=0 or r['n_processed']>2048 or r['n_prompt']<=0 for r in rows):raise ValueError('Nonwhole/overflow answer')
    result={};choices={}
    for multiple in sorted({r['training_multiple'] for r in roster}):
        group=[r for r in roster if r['training_multiple']==multiple]
        nominal=BASE_TARGETS*multiple;minimum=nominal-(nominal//1000);u=BASE_UPDATES*multiple
        failures=[]
        for targets in range(nominal,minimum-1,-1):
            trial={};failure=None
            for r in group:
                key=(r['draw'],r['budget_multiple'],r['price'],r['policy'])
                try:trial[r['run_id']]=schedule([x['n_supervised'] for x in corpora[key]],targets,u,17)
                except ValueError as exc:failure=dict(run_id=r['run_id'],reason=str(exc));break
            if failure is None:
                result.update(trial);choices[str(multiple)]=dict(nominal=nominal,realized=targets,updates=u,
                    lower_bound=minimum,failed_target_candidates=failures);break
            failures.append(dict(targets=targets,**failure))
        else:raise ValueError('No jointly feasible dose within registered0.1% envelope; no student dispatch')
    for r in roster:
        name=r['run_id'];plan=result[name];key=(r['draw'],r['budget_multiple'],r['price'],r['policy']);rows=corpora[key]
        plan.update(run=r,lrs=lrs(r['updates']),row_path_ids=[x['path_id'] for x in rows],
          acquired_parents=len({x['problem_id'] for x in rows}),
          exposed_parents=len({rows[i]['problem_id'] for i,n in enumerate(plan['row_exposures']) if n}),
          targets_are_frozen_before_student_scores=True)
        if sum(rows[i]['n_supervised'] for batch in plan['updates'] for i in batch)!=plan['supervised_targets']:
            raise AssertionError('Whole-answer dose differs')
    return dict(branch=list(branch),dose_choices=choices,plans=result,student_seed=17,main_outputs_not_read=True)
