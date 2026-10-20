"""Prospective original S1 sample-only calls; full exact A2 is required."""
from pathlib import Path
import modal
from experiments.p010.common import read

ROOT=Path(__file__).resolve().parents[2]
SPEC='reports/p010_20261019/existing_s1_sampling_runtime_v1/SPEC.json'
spec=read(ROOT/SPEC)
app=modal.App('p010-existing-S1-new-samples')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
          'TOKENIZERS_PARALLELISM':'false','VLLM_WORKER_MULTIPROC_METHOD':'spawn',
          'VLLM_USE_V1':'1','CUBLAS_WORKSPACE_CONFIG':':4096:8'}))
for name in list(spec['source_files'])+[SPEC]:
    image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),
    timeout=1260,startup_timeout=600,retries=0,max_containers=2,min_containers=0,
    buffer_containers=0,scaledown_window=2,single_use_containers=True,
    serialized=True,include_source=False,volumes={'/evidence':volume})
def worker(run,execution,approval,prior):
    import multiprocessing,time,traceback
    from experiments.p010.common import dump,sha,digest,verify,utc
    from experiments.p010.runtime_support import source_check,hard_timer,compact
    from experiments.p010.existing_student_samples import rows_checked,sampling,forecast
    from experiments.p010.existing_student_restore import child
    start=time.time();stop=start+1200;timer=hard_timer(1200)
    key='existing_s1_samples/'+run
    out=Path('/evidence/p010-20261019/existing_s1_samples')/run
    store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False)
    original_store=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    claimed=False
    try:
        s=read('/workspace/'+SPEC);source_check(s);volume.reload()
        parent=s['parents'][run];old=Path(parent['remote_path'])
        if (original_store.get(parent['terminal_key'])!=parent['terminal']
                or read(old/'MERGE_PROOF.json')!=parent['merge_proof']
                or read(old/'checkpoint_1024/manifest.json')!=parent['proof']['checkpoint']):
            raise ValueError('Original completed student/merge/checkpoint metadata differs')
        verify(s['model']['remote_path'],s['model']['files'])
        endpoint=Path('/evidence/p010-20261019/student_inputs/MATH_ENDPOINT.json')
        if sha(endpoint)!=s['endpoint_sha256']:raise ValueError('Original exact MATH endpoint changed')
        rows=rows_checked(read(endpoint));params=[sampling(r['sampling_seed']) for r in rows]
        initial=forecast(time.time()-start,0,[],s['batch_observations_seconds'],prior)
        claim=dict(run=run,execution=execution,epoch=start,
                   original_state_sha256=parent['proof']['checkpoint']['sha256'])
        if not store.put(key+'/claim',claim,skip_if_exists=True):
            raise RuntimeError('Original four sample evaluations already attempted')
        claimed=True;out.mkdir(parents=True,exist_ok=False)
        dump(out/'INTENT.json',dict(run=run,execution=execution,claim=claim,approval=approval,
            source_files=s['source_files'],worker_start_epoch=start,hard_deadline_epoch=stop,
            prior_T_reserved_usd=prior,original_parent_terminal=parent['terminal'],
            original_state_sha256=claim['original_state_sha256'],new_training_updates=0))
        dump(out/'ORIGINAL_MODEL_PROOF.json',parent['proof'])
        dump(out/'BEFORE_RESTORE_FORECAST.json',initial);volume.commit()
        ctx=multiprocessing.get_context('spawn');connection,other=ctx.Pipe()
        process=ctx.Process(target=child,args=(other,s['model']['remote_path'],
            str(old/'checkpoint_1024'),parent['proof'],str(out/'restore'),str(out/'merged'),stop))
        process.start();other.close()
        if not connection.poll(max(1,stop-time.time()-30)):
            raise TimeoutError('Original saved-model restoration deadline')
        kind,value=connection.recv();process.join(timeout=max(1,min(30,stop-time.time()-15)))
        if kind!='restored' or process.is_alive() or process.exitcode!=0:
            raise RuntimeError('Original inference restoration did not exit successfully: '+str(value))
        dump(out/'RESTORE_PROCESS_EXIT.json',dict(pid=process.pid,exitcode=process.exitcode,
            joined_before_vllm=True,new_training_updates=0))
        restored=read(out/'restore/COMPLETED.json')
        if restored!=value['proof'] or restored['actual_merged_files']!=parent['proof']['merged_files']:
            raise ValueError('Original restored model proof differs')
        verify(out/'merged',restored['actual_merged_files']);volume.commit()
        from vllm import LLM,SamplingParams
        from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs,actual_engine
        from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
        actual_params=[SamplingParams(**p) for p in params]
        dump(out/'BEFORE_EVAL_FORECAST.json',forecast(time.time()-start,0,[],s['batch_observations_seconds'],prior));volume.commit()
        llm=LLM(model=str(out/'merged'),tokenizer=str(out/'merged'),**engine_kwargs())
        dump(out/'ENGINE.json',actual_engine(llm.llm_engine.vllm_config));volume.commit()
        times=[]
        for offset in range(0,2000,256):
            unit=f'{offset:04d}';part=rows[offset:offset+256];part_params=params[offset:offset+256]
            f=forecast(time.time()-start,len(times),times,s['batch_observations_seconds'],prior)
            if store.get(key+'/claim')!=claim or original_store.get(parent['terminal_key'])!=parent['terminal']:
                raise RuntimeError('Original parent or new sample claim changed')
            dump(out/'sample_forecasts'/(unit+'.json'),f)
            intent=dict(rows=part,sampling=part_params,epoch=time.time())
            if not store.put(key+'/sample/'+unit,intent,skip_if_exists=True):
                raise RuntimeError('Original sample batch already reserved')
            dump(out/'sample_intents'/(unit+'.json'),intent);volume.commit();tick=time.monotonic()
            responses=llm.generate([dict(prompt_token_ids=r['input_ids']) for r in part],
                actual_params[offset:offset+256],use_tqdm=False)
            raw=returned_records(part,part_params,responses)
            dump(out/'raw'/(unit+'.json'),raw);volume.commit()
            if len(raw)!=len(part) or any(x['output_count']!=1 or x['candidate_id']!=r['candidate_id']
                    or x['prompt_token_ids']!=r['input_ids'] for x,r in zip(raw,part)):
                raise ValueError('Original saved-model sample identity differs')
            ack=dict(count=len(part),raw_sha256=digest(raw),seconds=time.monotonic()-tick)
            times.append(ack['seconds']);dump(out/'sample_acks'/(unit+'.json'),ack)
            if not store.put(key+'/sample_done/'+unit,ack,skip_if_exists=True):
                raise RuntimeError('Original sample acknowledgment already exists')
            volume.commit()
        result=dict(run=run,raw_sample_outputs=2000,greedy_outputs_generated=0,
            original_training_updates=1024,original_targets=2097148,new_training_updates=0,
            sampling_seeds=list(range(4)),sample_batch_seconds=times,
            original_merged_model_reproduced=True,seconds=time.time()-start,
            scoring='Separate frozen CPU scoring and actual A3 still required')
        dump(out/'RESULT.json',result);volume.commit();artifact=compact(out);volume.commit()
        terminal=dict(status='completed',finished_utc=utc(),result=result,artifact=artifact,
            seconds_including_pack=time.time()-start)
        dump(out/'TERMINAL.json',terminal);volume.commit()
        if not store.put(key+'/terminal',terminal,skip_if_exists=True):raise RuntimeError('Original sample terminal already exists')
        return terminal
    except BaseException as exc:
        if claimed and out.exists():
            dump(out/'FAILURE.json',dict(type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),utc=utc(),retry=False))
            volume.commit();store.put(key+'/terminal',dict(status='failed',error=str(exc)),skip_if_exists=True)
        raise
    finally:
        if 'process' in locals() and process.is_alive():process.kill();process.join(timeout=5)
        timer.cancel()


@app.local_entrypoint()
def main(run:str,receipt_dir:str,review_json:str,budget_json:str):
    import time,datetime,fcntl,json,subprocess
    from decimal import Decimal
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor
    from experiments.p010.common import dump,sha,require_published
    from experiments.p010.runtime_support import source_check
    from experiments.p010.student_dispatch_v2 import original_T_records
    from experiments.p010.existing_student_samples import forecast
    if run not in spec['parents'] or time.time()+1900>datetime.datetime(2026,10,21,19,tzinfo=datetime.timezone.utc).timestamp():
        raise ValueError('Original two saved students and full original window required')
    execution=require_published(ROOT);source_check(spec,ROOT)
    review,b=read(review_json),read(budget_json)
    if (review.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or review.get('scope')!='p010-C5-existing-S1-sample-only-A2'
            or review.get('spec_sha256')!=sha(ROOT/SPEC)
            or sha(review['local_report_file'])!=review['report_sha256']):
        raise ValueError('Exact original input/restore/runtime A2 required')
    if (b.get('category')!='T' or b.get('cap_usd')!='150'
            or b.get('reserve_release_used') is not False or not 0<=time.time()-b['observed_epoch']<=3600):
        raise ValueError('Fresh actual T reservation ledger required')
    root=ROOT/'.local/p010_20261019/r1';out=Path(receipt_dir)
    if out.resolve()!=(root/'existing_s1_sample_runs'/run).resolve():raise ValueError('Original canonical receipt required')
    prior=str(Decimal(b['prior_attempted_reserved_usd']))
    initial=forecast(0,0,[],spec['batch_observations_seconds'],prior)
    with (root/'student_dispatch.lock').open('a+') as handle:
        fcntl.flock(handle.fileno(),fcntl.LOCK_EX)
        original_T=original_T_records(root)+list((root/'existing_s1_sample_runs').glob('*/INTENT.json'))
        actual=sum((Decimal(read(p)['budget']['new_reserved_usd']) for p in original_T),Decimal('0'))
        if actual!=Decimal(prior):raise ValueError('All failed/completed/started T reservations retained')
        records=original_T+list(root.glob('cue_*_runs/*/INTENT.json'))
        cli=str(ROOT/'.local/midpoint_20261011/venv/bin/modal')
        containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=45))
        apps=[read(p.parent/'SUBMITTED.json')['app_id'] for p in records if (p.parent/'SUBMITTED.json').exists()]
        if len(apps)!=len(set(apps)):raise ValueError('Ambiguous original app ownership')
        def state(app_id):
            try:
                value=json.loads(subprocess.check_output([cli,'app','info',app_id,'--json'],text=True,timeout=45,stderr=subprocess.PIPE))
                if value['app_id']!=app_id:raise ValueError('Provider identity differs')
                return app_id,value['lifecycle']['state']
            except Exception:return app_id,'unknown'
        with ThreadPoolExecutor(max_workers=2) as readers:states=dict(readers.map(state,apps))
        counts=Counter(x.get('app_id') for x in containers)
        slots=sum(not (p.parent/'SUBMITTED.json').exists() for p in records)
        for app_id in apps:
            count=counts.pop(app_id,0)
            slots+=count if str(states.get(app_id,'unknown')).lower()=='stopped' else max(1,count)
        slots+=sum(counts.values())
        if slots>=4:raise ValueError('Shared four-container limit includes T/I/pending/unknown/unmatched')
        out.mkdir(parents=True,exist_ok=False)
        approval={k:v for k,v in review.items() if k!='local_report_file'}
        dump(out/'INTENT.json',dict(run=run,execution=execution,epoch=time.time(),approval=approval,
            budget=initial['budget'],budget_source_sha256=sha(budget_json),
            admission_provider_states=states,admission_slots=slots))
        call=worker.spawn(run,execution,approval,prior)
        dump(out/'SUBMITTED.json',dict(run=run,app_id=app.app_id,call_id=call.object_id))
    try:dump(out/'RESULT.json',call.get())
    except BaseException as exc:
        dump(out/'ERROR.json',dict(type=type(exc).__name__,error=str(exc)));raise
