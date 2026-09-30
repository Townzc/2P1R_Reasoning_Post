"""Bounded CPU-only diagnosis on the 96 saved outputs; never generates or trains."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import sys
import time

from .contracts import read_records, identity_hash
from .gpu_profile import ProfileError, durable_json, launch_guarded
from .screen_scoring import load_problems, load_references, score_pair
from .screen_runtime import extract_code


def saved_inputs(root):
    root=Path(root);items=[]
    for directory in (root/'W_prefix/batches').iterdir():
        intent,=read_records(directory/'intent.jsonl')
        records=read_records(directory/'batch.jsonl')
        backend=json.loads((directory/'generation_return.json').read_text())
        scoring=json.loads((directory/'scoring_inputs.json').read_text())
        if records[0]!=intent or len(records)!=17:
            raise ProfileError('saved batch is incomplete')
        for i,sample in enumerate(records[1:]):
            if (sample['sample_index']!=i or sample['task_id']!=intent['tasks'][i]
                or sample['intent_sha256']!=intent['record_sha256']
                or sample['completion_text']!=backend['decoded_text'][i]
                or sample['completion_token_ids']!=backend['completion_ids'][i]):
                raise ProfileError('saved sample/backend identity mismatch')
            code=scoring['codes'][i]
            if code!=extract_code(sample['completion_text']) or identity_hash({'code':code})!=scoring['code_sha256'][i]:
                raise ProfileError('saved scoring input changed')
            items.append((intent['batch_index'],i,sample,code))
    items.sort(key=lambda x:x[:2])
    if [(b,i) for b,i,_,_ in items]!=[(b,i) for b in range(6) for i in range(16)]:
        raise ProfileError('expected exactly the six saved batches, no new work')
    return items


def worker(a):
    os.environ['CUDA_VISIBLE_DEVICES']=''
    problems=load_problems(a.data_json,a.data_sha256)
    refs,manifest=load_references(Path(a.evidence_root)/'references')
    if manifest['data_sha256']!=a.data_sha256:raise ProfileError('reference data mismatch')
    from evalplus.eval import untrusted_check
    known=matched=resolved=0
    for batch,index,old,code in saved_inputs(a.evidence_root):
        pair=score_pair(problems[old['task_id']],refs[old['task_id']],code,
                        untrusted_check,fast_check=True)
        old_known=all(old[k]['status'] in ['pass','fail'] for k in ['base','extra'])
        new_known=all(pair[k]['status'] in ['pass','fail'] for k in ['base','extra'])
        equal=all(old[k]['status']==pair[k]['status'] for k in ['base','extra'])
        durable_json(Path(a.out)/f'score_{batch:04d}_{index:04d}.json',
                     {'source_sample_id':old['sample_id'],'task_id':old['task_id'],
                      'old':{k:old[k] for k in ['base','extra']},'new':pair,
                      'old_known':old_known,'new_known':new_known,'equal':equal,
                      'diagnostic_only':True})
        if not new_known or (old_known and not equal):
            raise ProfileError('first-failure scoring unresolved or disagrees with known binary verdict')
        known+=old_known;matched+=old_known and equal;resolved+=new_known
    if (known,matched,resolved)!=(90,90,96):raise ProfileError('unexpected diagnostic coverage')
    durable_json(Path(a.out)/'preflight_complete.json',
                 {'saved_outputs_scored':96,'previous_known_pairs':known,'matched_pairs':matched,
                  'resolved_pairs':resolved,'new_generations':0,'optimizer_updates':0,
                  'fast_check':True,'historical_records_relabelled':False,
                  'scope':'CPU scoring diagnosis only; not a scientific W/C/R result'})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['evidence-root','data-json','data-sha256','out']:
        p.add_argument('--'+name,required=True)
    p.add_argument('--execute-saved-output-preflight',action='store_true')
    p.add_argument('--_worker',action='store_true')
    a=p.parse_args()
    if not a.execute_saved_output_preflight or platform.system()!='Linux':
        raise ProfileError('explicit isolated Linux CPU diagnostic required')
    if a._worker:
        if os.environ.get('Q2_PROFILE_PARENT_PID')!=str(os.getppid()):raise ProfileError('owned parent required')
        try:worker(a)
        except BaseException as exc:
            try:durable_json(Path(a.out)/'preflight_failure.json',{'error':repr(exc)})
            finally:os._exit(1)
        os._exit(0)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    durable_json(out/'preflight_intent.json',{'saved_outputs':96,'new_generations':0,
                 'optimizer_updates':0,'cap_seconds':180,'started_epoch':time.time()})
    return launch_guarded([sys.executable,'-m','experiments.q2_supervision_migration.scoring_preflight',
                           *sys.argv[1:],'--_worker'],out,180,phase='cpu')

if __name__=='__main__':raise SystemExit(main())
