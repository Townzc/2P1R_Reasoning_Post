"""One local D2(a) state oracle and first complete-scope score; no model/collect."""
import argparse
import os
from pathlib import Path
import subprocess
import threading
import time
from experiments.p011 import long_owner_path as path, long_d2_scope as scope
from experiments.p011 import long_owner_evidence as original
from experiments.p011 import long_d2_scope_scoring as scoring,long_d2_scope_score_process as process
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,verify
from scripts.p011_long_owner_closed_io import reused_assets
ROOT=Path(__file__).resolve().parents[1]


def bound_source(root):
    spec=path.validate(read(root/path.SPEC));head=path.published(root,spec)
    binding=read(root/scope.PACKET/'SOURCE_BINDING.json')
    for name in (scope.PACKET+'/SOURCE_BINDING.json',scope.DECISION):
        if subprocess.check_output(['git','show',head+':'+name],cwd=root)!=(root/name).read_bytes():
            raise ValueError('Owner scope and candidate binding must be published unchanged')
    for name,expected in binding['source_files'].items():
        if sha(root/name)!=expected or subprocess.check_output(['git','show',head+':'+name],cwd=root)!=(root/name).read_bytes():
            raise ValueError('D2 option(a) exact published source differs')
    if (sha(root/scope.DECISION)!=binding['owner_decision_sha256']
            or sha(root/path.SPEC)!=binding['original_spec_sha256']
            or sha(root/scope.PRESERVED/'PRESERVATION_COMPLETED.json')!=binding['preservation_sha256']
            or sha(root/'reports/p011_20261020/owner_D2_terminal_failure_v1/MANIFEST.json')!=binding['original_failure_manifest_sha256']):
        raise ValueError('Owner scope/original input/failure binding differs')
    owner=read(root/scope.DECISION)
    if (owner['job']!=scope.JOB or owner['score_total']!=2980 or owner['new_model_calls_authorized'] is not False
            or owner['score_cap_seconds']!=7200 or owner['local_results_cutoff_utc']!='2026-10-22T05:00:00Z'):
        raise ValueError('Exact direct owner D2 option(a) authority required')
    return spec,binding


def audit(root,out,spec,binding):
    job=spec['jobs'][scope.JOB];k=path.key(job);saved=root/scope.PRESERVED;payload=saved/'original_remote_payload'
    preservation=read(saved/'PRESERVATION_COMPLETED.json')
    if not preservation['stable_inventory'] or preservation['file_count']!=246 or preservation['absent_count']!=2:
        raise ValueError('Exact once-preserved failed attempt required')
    records={}
    for p in (saved/'named_records').glob('*.json'):
        v=read(p)
        if v['key'] in records:raise ValueError('Duplicate preserved immutable record')
        records[v['key']]=v['value']
    dispatch=read(root/path.LOCAL/'dispatch'/scope.JOB/'INTENT.json')
    if records.pop(k+'/dispatch')!=dispatch or read(payload/'ADMISSION.json')!=dispatch:
        raise ValueError('Original D2 dispatch/admission differs')
    provider=read(root/path.LOCAL/'long_owner_closeout_r1/collect/long_baseline_S-L15_s17_owner_r1/PROVIDER_STOPPED0.json')
    claim=read(payload/'CLAIM.json');identity=read(payload/'IDENTITY.json');timing=read(payload/'TIMING_POLICY.json')
    if (provider['app_id']!=claim['app_id'] or provider['state']!='stopped' or provider['owned_containers']!=0
            or provider['observed_epoch']<preservation['original_failure_observed_epoch']):
        raise ValueError('Original shared app must have actually stopped')
    review=path.reviewed(spec,root/path.SPEC,read(root/path.LOCAL/'OWNER150_EXECUTION_AUTHORIZATION.json'))
    budgetfile=root/path.LOCAL/'dispatch'/scope.JOB/'BUDGET_SOURCE.json'
    if (dispatch['review']!=review or sha(budgetfile)!=dispatch['budget_source_sha256']
            or path.budget_check(root,spec,job,read(budgetfile),dispatch['prior_attempt_records'],dispatch['provider_observation'],dispatch['dispatch_epoch'])!=dispatch['budget']
            or records[k+'/claim']!=claim or claim['dispatch_sha256']!=digest(dispatch)
            or timing!=path.policy(job,claim['worker_start_epoch'],dispatch['budget']['prior_reserved_usd'])
            or identity!=dict(logical_id=scope.JOB,arm=job['arm'],job_sha256=digest(job),input_plan_sha256=job.get('input_plan_sha256'),execution=dispatch['execution'],source_files=spec['source_files'])):
        raise ValueError('Original claim/source/admission/timing/identity differs')
    attempts,done=scope.journals(payload,k,records)
    inputs=root/path.LOCAL/path.LOCAL_INPUT_DIRECTORY/job['input_directory'];verify(inputs,job['local_input_files'])
    reused_assets(root,job);assets=root/job['model']['local_path'];verify(assets,job['model']['local_audit_asset_files'])
    config=read(assets/'config.json');view=scope.training_view(payload,out/'DERIVED_TRAINING_ONLY_VIEW')
    train=original.verify_training(view,read(inputs/'encoded.json'),read(inputs/'plan.json'),read(inputs/('rates_'+job['arm']+'.json')),job['arm'],config,identity,attempts,done,timing)
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(assets,local_files_only=True,trust_remote_code=False,use_fast=True)
    endpoint=scope.endpoint(payload,read(inputs/'ENDPOINT_LOCAL.json'),job['context'],job['eos_token_ids'],tokenizer,config,attempts,done,timing,train['training_seconds'])
    dump(out/'SCORING_ROWS.json',endpoint.pop('scoring_rows'));dump(out/'DECODED.json',endpoint.pop('decoded'))
    dump(out/'COMPLETE_PROOF.json',dict(passed=True,scope='owner_D2_option_a_complete_MATH_AIME_only',original_worker_completed=False,
        source_binding_sha256=sha(root/scope.PACKET/'SOURCE_BINDING.json'),job_sha256=digest(job),original_source_files=spec['source_files'],
        training_proof=train,training_state_verified=True,derived_training_view_not_worker_result=True,endpoint=endpoint,
        scoring_rows_sha256=sha(out/'SCORING_ROWS.json'),actual_A3_accepted=False,finished_epoch=time.time(),new_model_calls=0))


def score(root,out,spec,binding):
    folder=root/scope.LOCAL/'audit';proof=read(folder/'COMPLETE_PROOF.json')
    if (proof['passed'] is not True or proof['job_sha256']!=digest(spec['jobs'][scope.JOB])
            or proof['source_binding_sha256']!=sha(root/scope.PACKET/'SOURCE_BINDING.json')
            or sha(folder/'SCORING_ROWS.json')!=proof['scoring_rows_sha256']):
        raise ValueError('New complete scoped oracle required')
    rows=read(folder/'SCORING_ROWS.json');bound=dict(source_binding=binding,oracle_sha256=sha(folder/'COMPLETE_PROOF.json'),owner_decision_sha256=sha(root/scope.DECISION))
    seconds=min(7200,int(path.CUTOFF-time.time())-5)
    if seconds<1:raise TimeoutError('Owner05UTC result deadline exhausted')
    result=process.supervise_once(out/'owned_score',rows,bound,seconds)
    checked=scoring.verify_saved_scores(out/'owned_score/payload',rows,bound,seconds)
    dump(out/'COMPLETED.json',dict(result=result,read_only_saved_score_proof=checked,original_worker_completed=False,
        amc23=proof['endpoint']['amc23'],actual_A3_accepted=False,completed_epoch=time.time(),disclosure=scope.DISCLOSURE))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['audit','score']);a=p.parse_args()
    spec,binding=bound_source(ROOT)
    seconds=min(3600,int(path.CUTOFF-time.time())-5)
    if seconds<1:raise TimeoutError('Owner local result cutoff exhausted')
    out=ROOT/scope.LOCAL/a.mode;out.mkdir(parents=True,exist_ok=False)
    dump(out/'ATTEMPT.json',dict(mode=a.mode,owner_decision_sha256=sha(ROOT/scope.DECISION),source_binding=binding,
        started_epoch=time.time(),absolute_deadline=path.CUTOFF,no_model_call=True,no_automatic_retry=True))
    timer=None
    if a.mode=='audit':timer=threading.Timer(seconds,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        {'audit':audit,'score':score}[a.mode](ROOT,out,spec,binding)
        if time.time()>=path.CUTOFF:raise TimeoutError('Owner05UTC cutoff exceeded')
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,message=str(exc),partial_retained=True,no_automatic_retry=True));raise
    finally:
        if timer:timer.cancel()

if __name__=='__main__':main()
