"""One independently approved remaining C6 T72 evaluation; never replay the parent."""
from pathlib import Path
import modal
from experiments.p010.common import read
ROOT=Path(__file__).resolve().parents[2]
SPEC='reports/p010_20261019/c6_remaining_runtime_v1/SPEC.json'
spec=read(ROOT/SPEC);app=modal.App('p010-c6-t72-only-remaining')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12').pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','VLLM_WORKER_MULTIPROC_METHOD':'spawn','VLLM_USE_V1':'1','CUBLAS_WORKSPACE_CONFIG':':4096:8'}))
for n in list(spec['source_files'])+[SPEC]:image=image.add_local_file(ROOT/n,'/workspace/'+n,copy=True)


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=1260,startup_timeout=600,
    retries=0,max_containers=1,min_containers=0,buffer_containers=0,scaledown_window=2,single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def worker(execution,reviews,budget):
    import time,traceback
    from experiments.p010.common import dump,utc
    from experiments.p010.runtime_support import source_check,hard_timer,compact
    from experiments.p010.cue_remaining import KEY,HARD_SECONDS,check_parent,generate
    start=time.time();timer=hard_timer(HARD_SECONDS);claimed=False
    out=Path('/evidence/p010-20261019/cue/t72_remaining_r1');inputs=Path('/evidence/p010-20261019/cue_benchmark_inputs_r1')
    store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False)
    try:
        s=read('/workspace/'+SPEC);source_check(s);volume.reload();check_parent(s,store)
        claim=dict(run='t72_remaining_r1',execution=execution,epoch=start)
        if not store.put(KEY+'/claim',claim,skip_if_exists=True):raise RuntimeError('Remaining cell already attempted')
        claimed=True;out.mkdir(parents=True,exist_ok=False)
        dump(out/'INTENT.json',dict(claim=claim,execution=execution,reviews=reviews,budget=budget,
            worker_start_epoch=start,hard_deadline_epoch=start+HARD_SECONDS,source_files=s['source_files'],input_files=s['input_files'],failed_parent=s['failed_parent']))
        volume.commit();result=generate(inputs,out,s,claim,start,start+HARD_SECONDS,budget['prior_reserved_usd'],store,volume)
        artifact=compact(out);volume.commit()
        if time.time()>=start+HARD_SECONDS:raise TimeoutError('Packing exceeded original remaining window')
        terminal=dict(status='completed',finished_utc=utc(),result=result,artifact=artifact,seconds_including_pack=time.time()-start)
        dump(out/'TERMINAL.json',terminal);volume.commit()
        if not store.put(KEY+'/terminal',terminal,skip_if_exists=True):raise RuntimeError('Remaining terminal exists')
        return terminal
    except BaseException as exc:
        if claimed and out.exists():
            dump(out/'FAILURE.json',dict(type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),utc=utc(),automatic_retry=False));volume.commit()
            store.put(KEY+'/terminal',dict(status='failed',error=str(exc)),skip_if_exists=True)
        raise
    finally:timer.cancel()


@app.local_entrypoint()
def main(receipt_dir:str,runtime_review_json:str,owner_decision_json:str,budget_json:str):
    import datetime,time,fcntl,json,subprocess
    from decimal import Decimal
    from concurrent.futures import ThreadPoolExecutor
    from experiments.p010.common import dump,sha,require_published,CAPS,utc,verify
    from experiments.p010.runtime_support import source_check
    from experiments.p010.cue_remaining import KEY,check_parent,forecast
    from experiments.p010.cue_remaining_binding import owner_review,effective_totals
    from experiments.p010.tier3_dispatch import attempted_records,fixed_review,validate_a4
    root=ROOT/'.local/p010_20261019/r1';out=Path(receipt_dir)
    if time.time()+spec['full_result_window_seconds']>datetime.datetime(2026,10,21,19,tzinfo=datetime.timezone.utc).timestamp():
        raise ValueError('Full cloud/raw/scoring/publication window must fit')
    execution=require_published(ROOT);source_check(spec,ROOT)
    for n,h in spec['verification_source_files'].items():
        if sha(ROOT/n)!=h:raise ValueError('Verification source changed')
    if out.resolve()!=(root/'cue_remaining_runs/t72_remaining_r1').resolve():raise ValueError('Canonical create-only receipt required')
    owner,audit=read(owner_decision_json),read(runtime_review_json);reviews=owner_review(spec,owner,audit,ROOT/SPEC)
    olda2=read(root/'C6_BENCHMARK_A2_ACCEPTED.json');selection=read(root/'C6_COMPLETE_SELECTION_A3_ACCEPTED.json')
    results=read(root/'K1_E1D_S1_SAMPLES_C9_A3_ACCEPTED.json');a4=read(root/'A4_SCIENTIFIC_SIGNAL_REPORT.json')
    for obj in (olda2,selection,results):fixed_review(obj)
    validate_a4(a4,results)
    if olda2['spec_sha256']!=spec['original_spec_sha256'] or selection['selection_sha256']!=spec['selection_sha256']:
        raise ValueError('Original reviewed parent and chosen cue differ')
    reviews.update(original_A2=fixed_review(olda2),selection_A3=fixed_review(selection),actual_results_A3=fixed_review(results),A4=a4)
    preserved=root/'cue_benchmark_failure_preservation_r1'
    if sha(preserved/'MANIFEST.json')!=spec['failed_parent_manifest_sha256'] or sha(preserved/'COMPLETED.json')!=spec['preservation_completed_sha256']:
        raise ValueError('Exact completed preservation changed')
    verify(preserved/'evidence',read(preserved/'MANIFEST.json'))
    uploaded=read(root/'cue_benchmark_input_upload_r1/COMPLETED.json')
    if {n:{k:v[k] for k in ('bytes','sha256')} for n,v in uploaded['files'].items()}!=spec['input_files']:
        raise ValueError('Original input readback required; no upload')
    b=read(budget_json)
    if (not 0<=time.time()-b['observed_epoch']<=3600 or b.get('caps_usd')!={'G':50,'T':150,'I':15,'C':25}
            or b.get('overall_cap_usd')!='240' or b.get('protected_usd')!='43'
            or sha(b['local_billing_report'])!=b['billing_report_sha256']):raise ValueError('Fresh original-cap real billing proof required')
    fresh=read(b['local_billing_report'])
    with (root/'student_dispatch.lock').open('a+') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX);records=attempted_records(root)
        cli=str(ROOT/'.local/midpoint_20261011/venv/bin/modal')
        containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=45))
        apps=[read(p.parent/'SUBMITTED.json')['app_id'] for p in records if (p.parent/'SUBMITTED.json').exists()]
        def state(app_id):
            try:
                v=json.loads(subprocess.check_output([cli,'app','info',app_id,'--json'],text=True,timeout=45,stderr=subprocess.PIPE))
                if v['app_id']!=app_id:raise ValueError('Wrong app identity')
                return app_id,v['lifecycle']['state']
            except Exception:return app_id,'unknown'
        with ThreadPoolExecutor(max_workers=2) as readers:states=dict(readers.map(state,apps))
        totals,effective,slots,settlement=effective_totals(root,records,containers,states,spec,fresh)
        if slots!=0 or {k:str(v) for k,v in totals.items()}!=b['all_attempted_reservations_usd']:
            raise ValueError('All original workers STOPPED0 and exact attempted ledger required')
        initial=forecast(0,0,[],spec['observed_batch_seconds'],str(effective['I']));budget=initial['budget']
        if sum(effective.values())+Decimal('2.52')>240:raise ValueError('Overall240 cap')
        store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False);check_parent(spec,store)
        if any(store.get(KEY+'/'+s) is not None for s in ('dispatch','claim','terminal')):
            raise RuntimeError('Remaining dispatch was already consumed or unknown')
        # Do not reset the original fourth-cell marker or any failed terminal.
        out.mkdir(parents=True,exist_ok=False)
        intent=dict(run='t72_remaining_r1',execution=execution,reviews=reviews,budget=budget,epoch=time.time(),
            all_attempted_reservations_usd={k:str(v) for k,v in totals.items()},effective_prior_charges_usd={k:str(v) for k,v in effective.items()},
            admission_states=states,admission_slots=slots,budget_source_sha256=sha(budget_json),failed_parent_manifest_sha256=spec['failed_parent_manifest_sha256'])
        dump(out/'INTENT.json',intent)
        dump(out/'I_D1_SETTLEMENT_APPLIED.json',dict(utc=utc(),actual_release_applied=True,original_claims_modified=False,
            settlement=settlement,exact_A2_report_sha256=audit['report_sha256'],runtime_spec_sha256=sha(ROOT/SPEC),owner_evidence_sha256=owner['evidence_sha256']))
        if not store.put(KEY+'/dispatch',intent,skip_if_exists=True):raise RuntimeError('Remaining dispatch fence exists')
        call=worker.spawn(execution,reviews,budget);dump(out/'SUBMITTED.json',dict(run='t72_remaining_r1',app_id=app.app_id,call_id=call.object_id))
    try:dump(out/'RESULT.json',call.get())
    except BaseException as exc:
        dump(out/'ERROR.json',dict(type=type(exc).__name__,error=str(exc),automatic_retry=False));raise
