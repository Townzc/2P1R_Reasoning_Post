# Exact53-source guard repair helper adaptation; original helpers unchanged.
"""Bounded read-only observation of the one independently approved NC replacement.
No spawning, remote writes, scoring, state loading, or automatic retry. The first
block proof is not a full raw/state/dose oracle. Original failure stays failed.
"""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,os,subprocess,sys,threading,re
from experiments.sft_allocation_midpoint.common import read,dump,sha,digest
from experiments.learning_regime_p009.stage1_nc_guard_repair_binding import (
    CAMPAIGN,RUN,validate,intent,marker,dispatch_key,logical_key)
from experiments.learning_regime_p009.stage1_nc_replacement_contract import RUN
ROOT=Path('.local/p009_20261014/r1/stage1_nc_guard_repair_r1')
SPEC=Path('reports/p009_20261014/stage1_nc_guard_repair_preflight_v1/ADMISSION.json')
CLI='.local/midpoint_20261011/venv/bin/modal'

def require_exact_review():
    code=read(ROOT/'READONLY_PUBLICATION_CODE_ACCEPTED.json')
    sources={p:sha(p) for p in ('scripts/p009_nc_guard_repair_observe.py',
        'scripts/publish_p009_nc_guard_repair_pair.py','scripts/publish_p009_stage0_result.py')}
    if (code.get('scope')!='p009-stage1-NC-guard-repair-observation-and-pair-publication-code'
        or code.get('decision') not in ('PASS','PASS-WITH-NOTES')
        or code.get('source_files')!=sources or len(code.get('target_commit',''))!=40
        or len(code.get('report_commit',''))!=40
        or sha(code['local_report_path'])!=code['report_sha256']):
        raise ValueError('Actual exact read-only helper code review is required')
    sent=read(ROOT/'runs'/RUN/'dispatch_intent.json')
    read(ROOT/'runs'/RUN/'submitted.json')
    spec=read(SPEC);validate(spec,sent['plan'],RUN,sent['release'])
    if any(sha(p)!=h for p,h in spec['source_files'].items()):
        raise ValueError('Reviewed53 runtime source bytes changed')

def observe():
    import modal
    now=datetime.now(timezone.utc); folder=ROOT/'status'/now.strftime('%Y%m%dT%H%M%S.%fZ'); dest=folder/'STATUS.json'
    dump(folder/'READ_INTENT.json',dict(started_utc=now.isoformat(),source_sha256=sha(__file__),remote_writes=0,new_model_calls=0))
    store=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    result=dict(started_utc=now.isoformat(),observer_source_sha256=sha(__file__),runs={},
                new_model_calls=0,remote_writes=0,partial_scores_computed=False)
    try:containers=json.loads(subprocess.check_output([CLI,'container','list','--json'],text=True,timeout=60))
    except Exception as e:containers=None;result['containers_read_error']=repr(e)
    pre='midpoint/'+CAMPAIGN+'/'
    for run in (RUN,):
        row={};result['runs'][run]=row
        try:
            sent=read(ROOT/'runs'/run/'dispatch_intent.json');app=sent['provider_app_id']
            row['app_id']=app;row['call']=read(ROOT/'runs'/run/'submitted.json')
            row['local_original_result_exists']=(ROOT/'runs'/run/'result.json').exists()
            row['local_original_return_error_exists']=(ROOT/'runs'/run/'return_error.json').exists()
            row['provider']=json.loads(subprocess.check_output([CLI,'app','info',app,'--json'],text=True,timeout=60))
            row['owned_containers']=None if containers is None else [x for x in containers if x.get('app_id')==app]
            keys=[pre+k+'/'+run for k in ('claim','intent','terminal')]+[dispatch_key(run),logical_key(run)]
            row['records']={k:store.get(k) for k in keys}
            row['progress']='unknown'
            entries=list(volume.iterdir('/'+CAMPAIGN+'/'+run+'/completed',recursive=True))
            if len(entries)>4096:raise ValueError('Original bounded directory exceeds4096 metadata entries')
            names=[Path(x.path).name for x in entries]
            row['completed_names']=sorted(names)
            updates=sorted(int(m.group(1)) for n in names if (m:=re.fullmatch(r'update_(\d{4})\.json',n)))
            continuous=0
            for n in updates:
                if n!=continuous+1:break
                continuous=n
            row['continuous_saved_update_records']=continuous
            blocks=sorted(n for n in names if re.fullmatch(r'training_block_\d{4}_\d{4}\.json',n))
            if blocks:
                name=blocks[-1];remote='/'+CAMPAIGN+'/'+run+'/completed/'+name
                ack=json.loads(b''.join(volume.read_file(remote)))
                row['latest_saved_block']=ack
                row['latest_block_remote_ack_matches']=store.get(pre+run+'/done/'+name[:-5])==ack
            endpoints=sorted(n for n in names if re.fullmatch(r'endpoint_\d{5}\.json',n))
            saved=0
            for n in endpoints:
                offset=int(n[9:14])
                if offset!=saved:break
                saved+=min(256,1319-offset)
            row['continuous_saved_endpoint_count_from_names']=saved
            row['progress']='saved_metadata_observed_not_full_raw_or_state_oracle'
        except Exception as e:row['read_error']=repr(e);row['progress']='unknown'
    result['read_utc']=datetime.now(timezone.utc).isoformat();dump(dest,result)
    print(json.dumps(dict(path=str(dest),read_utc=result['read_utc'],runs={k:{
        'provider_state':v.get('provider',{}).get('lifecycle',{}).get('state'),
        'owned_count':None if v.get('owned_containers') is None else len(v['owned_containers']),
        'terminal':v.get('records',{}).get(pre+'terminal/'+k),
        'updates':v.get('continuous_saved_update_records'),'endpoint':v.get('continuous_saved_endpoint_count_from_names'),
        'read_error':v.get('read_error')} for k,v in result['runs'].items()})))

def verify(run):
    spec=read(SPEC);dest=ROOT/'startup'/run
    if dest.exists():raise ValueError('Prior/partial startup read exists; no whole helper repeat')
    sent=read(ROOT/'runs'/run/'dispatch_intent.json');call=read(ROOT/'runs'/run/'submitted.json')
    cap=validate(spec,sent['plan'],run,sent['release'])
    if any(sha(k)!=v for k,v in spec['source_files'].items()):raise ValueError('Reviewed53 sources changed')
    import modal
    db=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    vol=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    pre='midpoint/'+CAMPAIGN+'/';unit='training_block_0001_0016'
    keys=[dispatch_key(run),logical_key(run),pre+'claim/'+run,pre+'intent/'+run,
          pre+run+'/unit/'+unit,pre+run+'/done/'+unit]
    records={k:db.get(k) for k in keys}
    ack=records[pre+run+'/done/'+unit]
    if ack is None:raise ValueError('Original first16 block has not acknowledged; no startup claim')
    dest.mkdir(parents=True,exist_ok=False)
    dump(dest/'READ_INTENT.json',dict(utc=datetime.now(timezone.utc).isoformat(),
        original_call=call,source_sha256=sha(__file__),new_model_calls=0,partial_score_computed=False))
    dump(dest/'RECORDS.json',records)
    parents={k:db.get(k) for k in spec['required_records']}
    dump(dest/'ORIGINAL_PARENT_RECORDS.json',parents)
    if parents!=spec['required_records']:
        raise ValueError('Original failed parent, completed sibling or fixed dependencies changed')
    files={}
    for name in ('intent.json','TRAINING_PROCESS.json','TRAINING_STARTED.json','training_environment.json',
                 'recipe.json','BEFORE_TRAINING_FORECAST.json','training_forecasts/000.json',
                 'completed/'+unit+'.json','completed/update_0016.json','training_timings/000.json'):
        raw=b''.join(vol.read_file('/'+CAMPAIGN+'/'+run+'/'+name))
        path=dest/'original'/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:f.write(raw)
        files[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    original=read(dest/'original/intent.json');process=read(dest/'original/TRAINING_PROCESS.json')
    env=read(dest/'original/training_environment.json');recipe=read(dest/'original/recipe.json')
    claim=records[pre+'claim/'+run];expected_marker=marker(spec,run,sent['release'])
    if (original['spec']!=spec or original['plan']!=sent['plan'] or original['release']!=sent['release']
        or original['run_id']!=run or claim['run_id']!=run or claim['reserved_cents']!=655
        or claim['plan_sha256']!=digest(sent['plan']) or claim['intent_sha256']!=digest(intent(spec,run))
        or records[pre+'intent/'+run]!=intent(spec,run)
        or any(records[k]!=expected_marker for k in (dispatch_key(run),logical_key(run)))
        or abs(original['hard_deadline_epoch']-original['worker_started_epoch']-cap['worker_seconds'])>.001):
        raise ValueError('Actual original claim/source/timer/dispatch changed')
    stem='nc17_n'+str(cap['n']);inputs=ROOT.parent/'stage1_nc_inputs_r1'
    plan=read(inputs/(stem+'_plan.json'));encoded=read(inputs/(stem+'_encoded.json'))
    cfg=read(inputs/(stem+'_config.json'));identity=recipe['identity']
    if (identity['config']!=cfg or identity['source_files']!=spec['source_files']
        or identity['spec_sha256']!=digest(spec) or recipe['schedule']!=plan['updates']
        or recipe['lrs']!=plan['lrs'] or recipe['targets']!=2097148 or recipe['seed']!=17):
        raise ValueError('Exact original recipe/whole answer plan differs')
    wanted=[dict(step=i+1,indices=list(indices),lr=plan['lrs'][i],
        supervised_tokens=sum(encoded[j]['n_supervised'] for j in indices),
        processed_tokens=sum(encoded[j]['n_processed'] for j in indices))
        for i,indices in enumerate(plan['updates'][:16])]
    block=records[pre+run+'/unit/'+unit];last=read(dest/'original/completed/update_0016.json')
    if (block['updates']!=wanted or block['updates_sha256']!=digest(wanted)
        or ack!=read(dest/'original/completed'/f'{unit}.json') or ack['count']!=16
        or ack['first_step']!=1 or ack['last_step']!=16 or ack['intent_sha256']!=digest(block)
        or ack['cumulative_targets']!=sum(x['supervised_tokens'] for x in wanted)
        or last['cumulative_targets']!=ack['cumulative_targets']):
        raise ValueError('Actual first16 original reservation/ack/dose differs')
    if (process['threads']!=4 or process['CUBLAS_WORKSPACE_CONFIG']!=':4096:8'
        or 'H100' not in process['gpu'] or process['tokenizer_is_verified_base'] is not True
        or env['cuda']!='12.8' or 'H100' not in env['gpu']
        or not env['deterministic_algorithms'] or env['allow_tf32'] is not False
        or env['versions']['torch'].split('+')[0]!='2.8.0'
        or env['versions']['numpy']!='2.2.6' or env['versions']['vllm']!='0.11.0'):
        raise ValueError('Actual isolated training environment differs')
    for name in ('BEFORE_TRAINING_FORECAST.json','training_forecasts/000.json'):
        if read(dest/'original'/name)['admitted'] is not True:raise ValueError('Original timing gate failed')
    dump(dest/'STARTUP_VERIFIED.json',dict(passed=True,utc=datetime.now(timezone.utc).isoformat(),
        run_id=run,app_id=sent['provider_app_id'],call_id=call['call_id'],
        worker_started_epoch=original['worker_started_epoch'],hard_deadline_epoch=original['hard_deadline_epoch'],
        original_files=files,first_block_updates=16,first_block_targets=ack['cumulative_targets'],
        actual_gpu=process['gpu'],source_file_count=53,scientific_total_verified=False,
        full_raw_or_state_oracle=False,partial_score_computed=False,new_model_calls=0))
    print(str(dest/'STARTUP_VERIFIED.json'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['status','startup']);a=p.parse_args()
    timer=threading.Timer(600,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        require_exact_review()
        observe() if a.action=='status' else verify(RUN)
    finally:timer.cancel()
