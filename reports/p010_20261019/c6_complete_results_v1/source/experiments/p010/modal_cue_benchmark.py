"""Single original C6 benchmark group; exact complete source/numeric A2 first."""
from pathlib import Path
import modal
from experiments.p010.common import read

ROOT=Path(__file__).resolve().parents[2]
SPEC='reports/p010_20261019/c6_benchmark_runtime_v1/SPEC.json'
spec=read(ROOT/SPEC)
app=modal.App('p010-cue-benchmark-original-four')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
          'TOKENIZERS_PARALLELISM':'false','VLLM_WORKER_MULTIPROC_METHOD':'spawn',
          'VLLM_USE_V1':'1','CUBLAS_WORKSPACE_CONFIG':':4096:8'}))
for name in list(spec['source_files'])+[SPEC]:
    image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),
    timeout=5460,startup_timeout=600,retries=0,max_containers=1,min_containers=0,
    buffer_containers=0,scaledown_window=2,single_use_containers=True,
    serialized=True,include_source=False,volumes={'/evidence':volume})
def worker(execution,reviews,prior):
    import multiprocessing,time,traceback
    from experiments.p010.common import dump,sha,digest,verify,utc
    from experiments.p010.runtime_support import source_check,hard_timer,compact
    from experiments.p010.cue_benchmark_group import KEY,HARD_SECONDS,check_rosters,forecast,child
    from experiments.p010.cue_benchmark_roster import RUNS
    started=time.time();deadline=started+HARD_SECONDS;timer=hard_timer(HARD_SECONDS)
    out=Path('/evidence/p010-20261019/cue/benchmark_group_r1')
    inputs=Path('/evidence/p010-20261019/cue_benchmark_inputs_r1')
    store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False)
    claimed=False;proc=None
    try:
        s=read('/workspace/'+SPEC);source_check(s);volume.reload();verify(inputs,s['input_files'])
        rosters={run:read(inputs/(run+'.json')) for run in RUNS};check_rosters(rosters)
        if (sha(inputs/'SELECTION.json')!=s['selection_sha256']
                or read(inputs/'MODEL_BINDINGS.json')!=s['model_bindings']):
            raise ValueError('Original selected cue or model roster changed')
        for run in RUNS:
            for suffix in ('claim','terminal'):
                if store.get('cue/benchmark_r1/'+run+'/'+suffix) is not None:
                    raise ValueError('An original cell was already attempted separately')
        claim=dict(run='benchmark_group_r1',execution=execution,epoch=started,
            selection_sha256=s['selection_sha256'])
        if not store.put(KEY+'/claim',claim,skip_if_exists=True):
            raise RuntimeError('Original four-cell benchmark already attempted')
        claimed=True;out.mkdir(parents=True,exist_ok=False)
        dump(out/'INTENT.json',dict(claim=claim,execution=execution,reviews=reviews,
            worker_start_epoch=started,hard_deadline_epoch=deadline,source_files=s['source_files'],
            prior_I_reserved_usd=prior,input_files=s['input_files'],selection_sha256=s['selection_sha256']))
        dump(out/'BEFORE_GROUP_FORECAST.json',forecast(time.time()-started,0,[],s['observed_batch_seconds'],prior));volume.commit()
        times=[];results={};ctx=multiprocessing.get_context('spawn')
        for run in RUNS:
            if store.get(KEY+'/claim')!=claim:raise RuntimeError('Original group claim changed')
            intent=dict(run=run,claim=claim,roster_sha256=sha(inputs/(run+'.json')),
                original_model_binding_sha256=digest(s['model_bindings'][run]),prior_completed_batches=len(times))
            if not store.put(KEY+'/'+run+'/cell',intent,skip_if_exists=True):
                raise RuntimeError('Original cell already reserved')
            dump(out/'cell_intents'/(run+'.json'),intent);volume.commit()
            parent,remote=ctx.Pipe()
            proc=ctx.Process(target=child,args=(remote,run,str(inputs/(run+'.json')),str(out/'cells'/run),
                s['model_bindings'][run],claim,started,deadline,s['observed_batch_seconds'],times,prior))
            proc.start();remote.close()
            if not parent.poll(max(1,deadline-time.time()-30)):raise TimeoutError('Original cell child deadline')
            kind,value=parent.recv();proc.join(timeout=max(1,min(30,deadline-time.time()-15)))
            if kind!='complete' or proc.is_alive() or proc.exitcode!=0:
                raise RuntimeError('Original cell did not complete and exit: '+str(value))
            volume.reload()
            if value!=read(out/'cells'/run/'RESULT.json'):raise ValueError('Original child completion differs')
            dump(out/'child_exits'/(run+'.json'),dict(pid=proc.pid,exitcode=proc.exitcode,joined_before_next_model=True))
            times.extend(value['batch_seconds']);results[run]=value;volume.commit();parent.close()
        if len(times)!=85 or time.time()>=deadline-15:raise TimeoutError('Full benchmark or closeout window incomplete')
        result=dict(cells=results,new_outputs=21371,batch_seconds=times,new_training_updates=0,
            new_checkpoint_loads=0,new_merge_operations=0,old_generations_repeated=0,seconds=time.time()-started)
        dump(out/'RESULT.json',result);volume.commit();artifact=compact(out);volume.commit()
        if time.time()>=deadline:raise TimeoutError('Original packing exceeded whole worker window')
        terminal=dict(status='completed',finished_utc=utc(),result=result,artifact=artifact,
            seconds_including_pack=time.time()-started)
        dump(out/'TERMINAL.json',terminal);volume.commit()
        if not store.put(KEY+'/terminal',terminal,skip_if_exists=True):raise RuntimeError('Original terminal exists')
        return terminal
    except BaseException as exc:
        if claimed and out.exists():
            dump(out/'FAILURE.json',dict(type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),utc=utc(),retry=False))
            volume.commit();store.put(KEY+'/terminal',dict(status='failed',error=str(exc)),skip_if_exists=True)
        raise
    finally:
        if proc is not None and proc.is_alive():proc.kill();proc.join(timeout=5)
        timer.cancel()


@app.local_entrypoint()
def main(receipt_dir:str,runtime_review_json:str,selection_review_json:str,
         actual_results_review_json:str,a4_report_json:str,budget_json:str):
    import datetime,time,fcntl,json,subprocess
    from decimal import Decimal
    from concurrent.futures import ThreadPoolExecutor
    from experiments.p010.common import dump,sha,require_published
    from experiments.p010.runtime_support import source_check
    from experiments.p010.cue_benchmark_group import KEY,FULL_WINDOW,forecast
    from experiments.p010.tier3_dispatch import attempted_records,totals_and_slots,fixed_review,validate_a4
    if time.time()+FULL_WINDOW>datetime.datetime(2026,10,21,19,tzinfo=datetime.timezone.utc).timestamp():
        raise ValueError('Full original bounded benchmark window required')
    execution=require_published(ROOT);source_check(spec,ROOT)
    runtime,selection,results=[read(p) for p in (runtime_review_json,selection_review_json,actual_results_review_json)]
    clean=[fixed_review(v) for v in (runtime,selection,results)]
    if (runtime.get('scope')!='p010-C6-complete-benchmark-input-runtime-and-numeric-A2'
            or runtime.get('spec_sha256')!=sha(ROOT/SPEC) or runtime.get('source_files')!=spec['source_files']
            or selection.get('scope')!='p010-C6-complete-search-selection-A3'
            or selection.get('target_commit')!=spec['selection_binding']['target_commit']
            or selection.get('selection_sha256')!=spec['selection_sha256']):
        raise ValueError('True exact runtime A2 and actual fixed selection A3 required')
    a4=read(a4_report_json);validate_a4(a4,results)
    reviews=dict(runtime_A2=clean[0],selection_A3=clean[1],actual_results_A3=clean[2],A4=a4)
    budget=read(budget_json)
    if (budget.get('category')!='I' or budget.get('cap_usd')!='15'
            or budget.get('reserve_release_used') is not False
            or not 0<=time.time()-budget['observed_epoch']<=3600):
        raise ValueError('Fresh original I budget, with all old reservations retained')
    prior=str(Decimal(budget['prior_attempted_reserved_usd']))
    initial=forecast(0,0,[],spec['observed_batch_seconds'],prior)
    root=ROOT/'.local/p010_20261019/r1';out=Path(receipt_dir)
    if out.resolve()!=(root/'cue_benchmark_runs/benchmark_group_r1').resolve():raise ValueError('Canonical original receipt required')
    uploaded=read(root/'cue_benchmark_input_upload_r1/COMPLETED.json')
    if {k:{x:v[x] for x in ('bytes','sha256')} for k,v in uploaded['files'].items()}!=spec['input_files']:
        raise ValueError('Full exact input readback required')
    with (root/'student_dispatch.lock').open('a+') as handle:
        fcntl.flock(handle.fileno(),fcntl.LOCK_EX)
        records=attempted_records(root);cli=str(ROOT/'.local/midpoint_20261011/venv/bin/modal')
        containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=45))
        apps=[read(p.parent/'SUBMITTED.json')['app_id'] for p in records if (p.parent/'SUBMITTED.json').exists()]
        def state(app_id):
            try:
                value=json.loads(subprocess.check_output([cli,'app','info',app_id,'--json'],text=True,timeout=45,stderr=subprocess.PIPE))
                if value['app_id']!=app_id:raise ValueError('Provider identity differs')
                return app_id,value['lifecycle']['state']
            except Exception:return app_id,'unknown'
        with ThreadPoolExecutor(max_workers=2) as readers:states=dict(readers.map(state,apps))
        totals,slots=totals_and_slots(records,containers,states)
        if totals['I']!=Decimal(prior) or slots>=4 or sum(totals.values())+Decimal('8.65')>240:
            raise ValueError('All attempted costs/shared pending unknown slots must fit')
        store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False)
        if any(store.get(KEY+'/'+suffix) is not None for suffix in ('dispatch','claim','terminal')):
            raise RuntimeError('Original benchmark is already attempted or ambiguous')
        out.mkdir(parents=True,exist_ok=False)
        intent=dict(run='benchmark_group_r1',execution=execution,epoch=time.time(),reviews=reviews,
            budget=initial['budget'],budget_source_sha256=sha(budget_json),admission_provider_states=states,admission_slots=slots)
        dump(out/'INTENT.json',intent)
        if not store.put(KEY+'/dispatch',intent,skip_if_exists=True):raise RuntimeError('Original benchmark dispatch exists')
        call=worker.spawn(execution,reviews,prior)
        dump(out/'SUBMITTED.json',dict(run='benchmark_group_r1',app_id=app.app_id,call_id=call.object_id))
    try:dump(out/'RESULT.json',call.get())
    except BaseException as exc:
        dump(out/'ERROR.json',dict(type=type(exc).__name__,error=str(exc)));raise
