"""Bounded Linux diagnosis of the saved C_prefix batch100 sample2; no model work."""
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
    for d in (evidence/'C_prefix/batches').iterdir():
        intent,=read_records(d/'intent.jsonl')
        if intent['batch_index']==100:selected.append((d,intent))
    if len(selected)!=1:raise ProfileError('exact saved batch required')
    d,intent=selected[0];rows=read_records(d/'batch.jsonl');s=rows[3]
    backend=json.loads((d/'generation_return.json').read_text())
    code=extract_code(s['completion_text'])
    scoring=json.loads((d/'scoring_inputs.json').read_text())
    assert s['sample_index']==2 and s['task_id']=='Mbpp/260'
    assert s['intent_sha256']==intent['record_sha256']
    assert s['completion_text']==backend['decoded_text'][2]
    assert s['completion_token_ids']==backend['completion_ids'][2]
    assert code==scoring['codes'][2] and identity_hash({'code':code})==scoring['code_sha256'][2]
    assert s['base']['status']=='timeout' and s['extra']['status']=='fail'
    p=problems[s['task_id']];gt=refs[s['task_id']]
    result=diagnose_initialization_timeout('mbpp',code,p['base_input'],p['entry_point'],gt['base'],p['atol'],gt['base_time'])
    durable_json(Path(a.out)/'saved_candidate_diagnosis.json',{'sample_id':s['sample_id'],
        'old_base':s['base'],'old_extra':s['extra'],'diagnosis':result,'historical_records_changed':False})
    if not result['confirmed_candidate_initialization_failure']:raise ProfileError('candidate initialization attribution not confirmed')
    controls=[]
    for code in ['def fixture(x):\n    return x','this is invalid syntax !']:
        control=diagnose_initialization_timeout('mbpp',code,[[1]],'fixture',[1],0,[.01])
        controls.append(control)
        if control['confirmed_candidate_initialization_failure']:raise ProfileError('false candidate attribution in authored control')
    durable_json(Path(a.out)/'preflight_complete.json',{'saved_timeout_attributed':1,
        'authored_negative_controls':controls,'new_generations':0,'optimizer_updates':0,
        'scope':'CPU diagnosis only; not permission to replay the 100 lost C updates'})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['evidence-root','data-json','data-sha256','out']:p.add_argument('--'+name,required=True)
    p.add_argument('--execute-initialization-diagnosis',action='store_true')
    p.add_argument('--_worker',action='store_true')
    a=p.parse_args()
    if platform.system()!='Linux' or not a.execute_initialization_diagnosis:raise ProfileError('explicit Linux CPU diagnostic required')
    if a._worker:
        if os.environ.get('Q2_PROFILE_PARENT_PID')!=str(os.getppid()):raise ProfileError('owned parent required')
        try:worker(a)
        except BaseException as exc:
            durable_json(Path(a.out)/'preflight_failure.json',{'error':repr(exc)});os._exit(1)
        os._exit(0)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    durable_json(out/'preflight_intent.json',{'saved_candidate':1,'new_generations':0,'updates':0,'cap_seconds':45})
    return launch_guarded([sys.executable,'-m','experiments.q2_supervision_migration.initialization_preflight',*sys.argv[1:],'--_worker'],out,45,phase='cpu')

if __name__=='__main__':raise SystemExit(main())
