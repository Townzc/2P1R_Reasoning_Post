"""Finite saved-output comparability gate; Linux CPU only, no new model output."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import sys
import time

from .contracts import read_records, identity_hash
from .gpu_profile import ProfileError, durable_json, launch_guarded, sha256
from .screen_scoring import load_problems, load_references, score_pair
from .scoring_preflight import saved_inputs
from .screen_runtime import extract_code


def saved_sample(phase, batch_index, index):
    matches=[]
    for d in (Path(phase)/'batches').iterdir():
        intent,=read_records(d/'intent.jsonl')
        if intent['batch_index']==batch_index: matches.append((d,intent))
    if len(matches)!=1: raise ProfileError('exact immutable batch missing or duplicated')
    d,intent=matches[0];rows=read_records(d/'batch.jsonl')
    if rows[0]!=intent: raise ProfileError('batch intent mismatch')
    sample=rows[index+1]
    backend=json.loads((d/'generation_return.json').read_text())
    inputs=json.loads((d/'scoring_inputs.json').read_text());code=inputs['codes'][index]
    if (sample['sample_index']!=index or sample['intent_sha256']!=intent['record_sha256']
        or sample['task_id']!=intent['tasks'][index]
        or sample['completion_text']!=backend['decoded_text'][index]
        or sample['completion_token_ids']!=backend['completion_ids'][index]
        or code!=extract_code(sample['completion_text'])
        or identity_hash({'code':code})!=inputs['code_sha256'][index]):
        raise ProfileError('saved candidate evidence changed')
    return sample,code


def worker(a):
    os.environ['CUDA_VISIBLE_DEVICES']=''
    from .scoring_cpu import pin_scoring_cpu
    durable_json(Path(a.out)/'scoring_cpu_placement.json',pin_scoring_cpu())
    from .scoring_guard_v2 import diagnose_timeout
    from evalplus.eval import untrusted_check
    out=Path(a.out);problems=load_problems(a.data_json,a.data_sha256)
    refs,manifest=load_references(a.references)
    if manifest['data_sha256']!=a.data_sha256: raise ProfileError('reference identity mismatch')
    controls=[]
    for name,code,wanted in [
        ('valid','def fixture(x):\n    return x','pass'),
        ('wrong','def fixture(x):\n    return x+1','fail'),
        ('syntax','this is invalid syntax !','fail'),
        ('init','raise ValueError("authored initialization failure")','fail'),
        ('test_timeout','def fixture(x):\n    while True: pass','fail')]:
        result=diagnose_timeout({'base_input':[[1]],'entry_point':'fixture','atol':0},
            code,[1],[.01],suite='base',original_details=[])
        durable_json(out/f'authored_{name}.json',result)
        if result.get('verified_suite_verdict')!=wanted:
            raise ProfileError('authored guard control failed: '+name)
        controls.append(name)
    # These checks run first: an inconsistency closes admission without spending on training.
    diagnoses=[]
    for label,phase,batch,index,task,suite,nold in [
        ('R599',Path(a.continuation_root)/'R_future',25,8,'Mbpp/599','extra',34),
        ('C260',Path(a.v2_root)/'C_prefix',100,2,'Mbpp/260','base',0)]:
        old,code=saved_sample(phase,batch,index)
        if old['task_id']!=task or old[suite]['status']!='timeout': raise ProfileError('wrong failure fixture')
        olddetail=json.loads(old[suite]['detail'])
        if olddetail['tests_observed']!=nold or olddetail['test_passes_observed']!=nold:
            raise ProfileError('original timeout prefix is not verified')
        verdicts=[]
        for repeat in range(3):
            refkey='plus' if suite=='extra' else 'base'
            result=diagnose_timeout(problems[task],code,refs[task][refkey],refs[task][refkey+'_time'],
                suite=suite,original_details=[True]*nold,outer_cap_seconds=180.0)
            durable_json(out/f'{label}_{repeat}.json',{'sample_id':old['sample_id'],
                'code_sha256':identity_hash({'code':code}),'old':old[suite], 'diagnosis':result,
                'diagnostic_only':True,'historical_result_changed':False})
            verdict=result.get('verified_suite_verdict')
            if not result.get('prefix_consistent') or verdict not in ('pass','fail'):
                raise ProfileError(f'{label} recovery unresolved or contradicts saved prefix; no model admission')
            verdicts.append(verdict)
        if len(set(verdicts))!=1: raise ProfileError(f'{label} repeat verdicts disagree')
        if label=='C260' and verdicts!=['fail']*3: raise ProfileError('initialization failure not reproduced')
        diagnoses.append({'fixture':label,'verdicts':verdicts})
    known=matched=resolved=0
    for batch,index,old,code in saved_inputs(a.initial_root):
        pair=score_pair(problems[old['task_id']],refs[old['task_id']],code,untrusted_check,
            fast_check=True,guarded_scoring_v2=True)
        oldknown=all(old[k]['status'] in ('pass','fail') for k in ('base','extra'))
        newknown=all(pair[k]['status'] in ('pass','fail') for k in ('base','extra'))
        equal=all(old[k]['status']==pair[k]['status'] for k in ('base','extra'))
        durable_json(out/f'original96_{batch:03d}_{index:02d}.json',{'sample_id':old['sample_id'],
            'old':{k:old[k] for k in ('base','extra')},'new':pair,'known':oldknown,'equal':equal})
        if not newknown or oldknown and not equal: raise ProfileError('original96 comparability failed')
        known+=oldknown;matched+=oldknown and equal;resolved+=newknown
    if (known,matched,resolved)!=(90,90,96): raise ProfileError('original96 coverage differs')
    sentinel_count=0
    for phase,root,task,batch,indices in [
        ('W_prefix',Path(a.v2_root)/'W_prefix','Mbpp/599',10,range(8,16)),
        ('W_prefix',Path(a.v2_root)/'W_prefix','Mbpp/260',100,range(8)),
        ('W_future',Path(a.continuation_root)/'W_future','Mbpp/599',25,range(8,16)),
        ('W_future',Path(a.continuation_root)/'W_future','Mbpp/260',52,range(8))]:
        for index in indices:
            old,code=saved_sample(root,batch,index)
            if old['task_id']!=task: raise ProfileError('wrong sentinel task')
            pair=score_pair(problems[task],refs[task],code,untrusted_check,fast_check=True,guarded_scoring_v2=True)
            equal=all(old[k]['status'] in ('pass','fail') and old[k]['status']==pair[k]['status'] for k in ('base','extra'))
            durable_json(out/f'sentinel_{phase}_{batch:03d}_{index:02d}.json',{'sample_id':old['sample_id'],
                'old':{k:old[k] for k in ('base','extra')},'new':pair,'equal':equal})
            if not equal: raise ProfileError('old W reward comparability sentinel failed')
            sentinel_count+=1
    durable_json(out/'preflight_complete.json',{'schema':1,'passed':True,
        'source_commit':a.source_commit,'diagnoses':diagnoses,'authored_controls_passed':controls,'original_saved_outputs':96,
        'plan_sha256':'351b33126af0b2457377a24ebb6618923e627f362cc8e06cfb69f390ae93806f',
        'reward_semantics_unchanged':True,
        'previous_known_pairs':90,'matched_pairs':90,'resolved_pairs':96,
        'known_W_sentinels_matched':sentinel_count,'new_generations':0,'optimizer_updates':0,
        'historical_records_relabelled':False,'reward_semantics_changed':False,
        'reference_manifest_sha256':sha256(Path(a.references)/'manifest.json'),
        'scope':'saved-output CPU admission; no universal timing equivalence or scientific result claim'})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['initial-root','v2-root','continuation-root','references','data-json','data-sha256','out','source-commit']:
        p.add_argument('--'+name,required=True)
    p.add_argument('--provider-deadline-epoch',type=float,required=True)
    p.add_argument('--execute-saved-output-preflight',action='store_true')
    p.add_argument('--_worker',action='store_true')
    a=p.parse_args()
    if platform.system()!='Linux' or not a.execute_saved_output_preflight: raise ProfileError('explicit Linux-only saved-code gate')
    if a._worker:
        if os.environ.get('Q2_PROFILE_PARENT_PID')!=str(os.getppid()): raise ProfileError('owned parent required')
        try: worker(a)
        except BaseException as exc:
            durable_json(Path(a.out)/'preflight_failure.json',{'error':repr(exc),'model_admitted':False})
            os._exit(1)
        os._exit(0)
    cap=min(1200.0,a.provider_deadline_epoch-600-time.time())
    if cap<=0: raise ProfileError('no diagnostic window remains')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    durable_json(out/'preflight_intent.json',{'source_commit':a.source_commit,'cap_seconds':cap,
        'failure_fixtures_repeats':{'R599':3,'C260':3},'saved_original_outputs':96,'known_W_sentinels':32,
        'new_generations':0,'optimizer_updates':0,'started_epoch':time.time()})
    return launch_guarded([sys.executable,'-m','experiments.q2_supervision_migration.completion_preflight',
        *sys.argv[1:],'--_worker'],out,cap,phase='cpu')

if __name__=='__main__': raise SystemExit(main())
