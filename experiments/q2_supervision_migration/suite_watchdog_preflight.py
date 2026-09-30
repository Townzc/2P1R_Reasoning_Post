"""Bounded Linux diagnosis of the saved R_future batch25 sample8; no model work."""
import argparse
import json
import os
from pathlib import Path
import platform
import sys

from .contracts import read_records, identity_hash
from .gpu_profile import ProfileError, durable_json, launch_guarded
from .screen_scoring import load_problems, load_references
from .screen_runtime import extract_code
from .initialization_guard import diagnose_initialization_timeout


def worker(a):
    os.environ['CUDA_VISIBLE_DEVICES']=''
    evidence=Path(a.evidence_root)
    problems=load_problems(a.data_json,a.data_sha256)
    refs,manifest=load_references(evidence/'references')
    if manifest['data_sha256']!=a.data_sha256:raise ProfileError('reference mismatch')
    selected=[]
    for d in (evidence/'R_future/batches').iterdir():
        intent,=read_records(d/'intent.jsonl')
        if intent['batch_index']==25:selected.append((d,intent))
    if len(selected)!=1:raise ProfileError('exact saved batch required')
    d,intent=selected[0];rows=read_records(d/'batch.jsonl');s=rows[9]
    backend=json.loads((d/'generation_return.json').read_text())
    code=extract_code(s['completion_text'])
    scoring=json.loads((d/'scoring_inputs.json').read_text())
    assert s['sample_index']==8 and s['task_id']=='Mbpp/599'
    assert s['intent_sha256']==intent['record_sha256']
    assert s['completion_text']==backend['decoded_text'][8]
    assert s['completion_token_ids']==backend['completion_ids'][8]
    assert code==scoring['codes'][8] and identity_hash({'code':code})==scoring['code_sha256'][8]
    assert s['base']['status']=='pass' and s['extra']['status']=='timeout'
    p=problems[s['task_id']];gt=refs[s['task_id']]
    result=diagnose_initialization_timeout('mbpp',code,p['plus_input'],p['entry_point'],gt['plus'],p['atol'],gt['plus_time'],complete_suite=True)
    durable_json(Path(a.out)/'saved_candidate_diagnosis.json',{'sample_id':s['sample_id'],
        'old_base':s['base'],'old_extra':s['extra'],'diagnosis':result,'historical_records_changed':False})
    if result['verified_suite_verdict'] not in ('pass','fail') or result['observed'][:34]!=[True]*34:
        raise ProfileError('suite verdict unresolved or previously passing tests differ')
    controls=[]
    for code,expected_status in [('def fixture(x):\n    return x','pass'),('def fixture(x):\n    return x+1','fail')]:
        control=diagnose_initialization_timeout('mbpp',code,[[1]],'fixture',[1],0,[.01],complete_suite=True)
        controls.append(control)
        if control['verified_suite_verdict']!=expected_status:raise ProfileError('authored control mismatch')
    durable_json(Path(a.out)/'preflight_complete.json',{'saved_suite_timeout_resolved':1,
        'authored_negative_controls':controls,'new_generations':0,'optimizer_updates':0,
        'scope':'CPU diagnosis only; no training restart or historical relabeling'})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['evidence-root','data-json','data-sha256','out']:p.add_argument('--'+name,required=True)
    p.add_argument('--execute-suite-diagnosis',action='store_true')
    p.add_argument('--_worker',action='store_true')
    a=p.parse_args()
    if platform.system()!='Linux' or not a.execute_suite_diagnosis:raise ProfileError('explicit Linux CPU diagnostic required')
    if a._worker:
        if os.environ.get('Q2_PROFILE_PARENT_PID')!=str(os.getppid()):raise ProfileError('owned parent required')
        try:worker(a)
        except BaseException as exc:
            durable_json(Path(a.out)/'preflight_failure.json',{'error':repr(exc)});os._exit(1)
        os._exit(0)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    durable_json(out/'preflight_intent.json',{'saved_candidate':1,'new_generations':0,'updates':0,'cap_seconds':210})
    return launch_guarded([sys.executable,'-m','experiments.q2_supervision_migration.suite_watchdog_preflight',*sys.argv[1:],'--_worker'],out,210,phase='cpu')

if __name__=='__main__':raise SystemExit(main())
