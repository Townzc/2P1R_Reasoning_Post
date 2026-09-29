"""Dry-run by default; explicit bounded worker for the registered seven-run phase."""
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

from experiments.thursday_probe.common import dump, stamp, verify_manifest, SEEDS
from experiments.thursday_probe.lora import attach,parameter_digest,save_adapter
from experiments.thursday_probe.arithmetic_eval import summarize
from experiments.thursday_probe_v2.config import (
    ROOT,DATA,RELEASE,OUT,BRANCH,REVISION,OLD_LEDGER_HASH,STATES,TRAINING,LIMITS,evaluation_queue,continue_after_measurement)
from experiments.thursday_probe_v2.training import train,restore_adapter,atomic_json
from experiments.thursday_probe_v2.runtime import GenerationBudget,evaluate,projected_remainder
from experiments.thursday_probe_v2.continuation import validate_previous, continuation_cap

OUT=Path(os.environ.get("THU_V2_OUTPUT",str(OUT)))
if OUT not in (Path("runs/thursday_arithmetic_v2_r1"),Path("runs/thursday_arithmetic_v2_r2")):
    raise ValueError("Unregistered attempt directory")
from scripts.audit_family_matching import verified_tokenizer
from scripts.run_relation_engineering import server_preflight
from src.relation_experiment import reference_nll
from src.sft_data import read_jsonl,encode_row,sha256_file


def source(require_published=True):
    def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
    head=git('rev-parse','HEAD')
    if require_published and (git('branch','--show-current')!=BRANCH or
        git('status','--porcelain','--untracked-files=no') or head!=git('rev-parse','origin/'+BRANCH)):
        raise ValueError('Clean published assigned branch required')
    files=[str(p) for d in ('src','analyses','scripts','experiments/thursday_probe',str(ROOT)) for p in Path(d).glob('*.py')]
    return dict(source_commit=head,source_files_sha256={p:sha256_file(p) for p in files})


def load_inputs():
    old=verify_manifest(DATA); release=verify_manifest(RELEASE)
    if release['old_manifest_sha256']!=sha256_file(DATA/'manifest.json'):
        raise ValueError('Old data release identity changed')
    def read(name):return json.loads((RELEASE/name).read_text())
    if read('limits.json')!=LIMITS or read('evaluation_queue.json')!=evaluation_queue():
        raise ValueError('Frozen limits/queue disagree with implementation')
    inputs={n:read_jsonl(DATA/(n+'.jsonl')) for n in ('surface','paths','prep_control','prep_bridge','probes','discovery_problems')}
    inputs.update({n:read_jsonl(RELEASE/(n+'.jsonl')) for n in ('calibration','calibration_fit','sentinel','midpoint')})
    registrations=read('registrations.json')['entries']
    if [(r['state'],r['parent'],r['data'],r['updates']) for r in registrations]!=list(TRAINING):
        raise ValueError('Registered training queue differs')
    return inputs,registrations,read('schedules.json'),read('learning_rates.json'),read('doses.json')


def dry_run():
    inputs,regs,schedules,lrs,doses=load_inputs()
    summary=dict(status='prepared_not_run',training_runs=regs,updates=sum(r['updates'] for r in regs),
        generations=sum(r['generations'] for r in evaluation_queue()),limits=LIMITS,
        input_manifest_sha256=sha256_file(DATA/'manifest.json'),release_manifest_sha256=sha256_file(RELEASE/'manifest.json'),
        scientific_selection_gates=[],reserved_test_contents_read=False,
        checkpoint_policy='Main0/64/128/256; prep/calibration0/32; latest recoverable optimizer+adapter+RNG per run.',
        runtime_disk_design='23 complete adapter directories plus 7 final recovery states; one rolling recovery transition at a time; minimum4.5GiB.',
        cumulative_training_tokens=sum(doses[r['data']]['supervised_response_tokens'] for r in regs),
        cumulative_processed_tokens=sum(doses[r['data']]['processed_nonpadding_tokens'] for r in regs))
    assert summary['updates']==1120 and summary['generations']==4704
    return summary


def worker(snapshot):
    if os.environ.get('THU_V2_BOUNDED')!='thursday_arithmetic_v2_r1':
        raise ValueError('Bounded parent launcher required')
    import torch
    from transformers import AutoModelForCausalLM
    inputs,regs,schedules,lrs,doses=load_inputs()
    tokenizer,tok=verified_tokenizer(Path(snapshot));tokenizer.pad_token=tokenizer.eos_token
    encoded={n:[encode_row(r,tokenizer,1024) for r in inputs[n]] for n in ('calibration','calibration_fit','surface','paths','prep_control','prep_bridge')}
    torch.manual_seed(SEEDS['training']);torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.cuda.reset_peak_memory_stats()
    start=time.monotonic();deadline=float(os.environ['THU_V2_DEADLINE'])
    manifest=dict(**source(),status='running',started_at_utc=stamp(),model=dict(id='Qwen/Qwen2.5-1.5B',revision=REVISION,
        kind='base',parameters='float32',autocast='bfloat16',attention='sdpa',tf32=False),
        peft=importlib.metadata.version('peft'),tokenizer=tok,seeds=SEEDS,
        release_manifest_sha256=sha256_file(RELEASE/'manifest.json'),old_ledger_sha256=OLD_LEDGER_HASH,
        runs=[{**r,'status':'not_run','reason':'Earlier fixed stages pending'} for r in regs],evaluations=[])
    dump(OUT/'run_manifest.json',manifest)
    atomic_json(OUT/'progress.json',manifest)
    previous=os.environ.get('THU_V2_PREVIOUS')
    carry=validate_previous(Path(previous)) if previous else None
    if bool(carry)!=(OUT.name=='thursday_arithmetic_v2_r2'):
        raise ValueError('Worker continuation and output identity disagree')
    fault=carry['fault_generations'] if carry else 0
    manifest['continuation']=carry
    budget=GenerationBudget(OUT/'generation_ledger.json',fault_generations=fault)
    def termination(*args):raise TimeoutError('Finite v2 process cap reached')
    signal.signal(signal.SIGTERM,termination)
    events={e['name']:e for e in evaluation_queue()};evaluation_records={}
    def ev(state,view):
        name=state+'_'+view;event=events[name]
        key='discovery_problems' if view.startswith('discovery_') else view
        tick=time.monotonic()
        if carry and name=='C0_calibration':
            if parameter_digest(model,True)!=carry['reused_adapter']:
                raise ValueError('Reused evaluation adapter differs')
            for suffix in ('.jsonl','.generation.json'):
                shutil.copy2(Path(previous)/(name+suffix),OUT/(name+suffix))
            records=read_jsonl(OUT/(name+'.jsonl'))
            from experiments.thursday_probe_v2.analyze import audit_records
            audit_records(OUT/(name+'.jsonl'),inputs[key],tokenizer)
            budget.reserve(name+'.jsonl',event['generations'])
        else:
            records=evaluate(model,tokenizer,inputs[key],OUT/(name+'.jsonl'),budget,event,deadline)
        evaluation_records[name]=records
        record=dict(**event,status='completed',seconds=time.monotonic()-tick,metrics=summarize(records),
                    predictions_sha256=sha256_file(OUT/(name+'.jsonl')),
                    adapter=parameter_digest(model,True),reused_from=previous if carry and name=='C0_calibration' else None)
        dump(OUT/(name+'.summary.json'),record)
        manifest['evaluations'].append(record);atomic_json(OUT/'progress.json',manifest)
        return records
    try:
        base=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.float32,attn_implementation='sdpa',local_files_only=True).cuda()
        model=attach(base)
        if any(p.dtype!=torch.float32 for p in model.parameters()):raise ValueError('Wrong precision')
        base_hash=parameter_digest(model);initial=save_adapter(model,OUT/'checkpoint_C0')
        if initial['parameter_digest']['parameters']!=18464768:raise ValueError('Wrong LoRA capacity')
        manifest.update(base_parameter_digest=base_hash,initial_adapter=initial)
        checkpoints={'C0':OUT/'checkpoint_C0'}
        bcal=ev('C0','calibration');ev('C0','probes');ev('C0','discovery_greedy')
        for i,reg in enumerate(regs):
            state,parent,name=reg['state'],reg['parent'],reg['data'];out=OUT/reg['run_id'];out.mkdir()
            identity=restore_adapter(model,checkpoints[parent])
            stage='calibration' if state=='calibration' else 'prep' if state in ('C','B') else 'main'
            if time.time()>=deadline:raise TimeoutError('No training budget remaining')
            record=dict(**reg,status='running',started_at_utc=stamp(),parent_checkpoint=str(checkpoints[parent]),
                parent_adapter=identity['parameter_digest'],optimizer_reset=True,scheduler_reset=True,
                recipe=dict(peak_lr=5e-5,floor_lr=1e-5,batch_size=16,microbatch_size=1,lora_rank=16,lora_alpha=32,
                    dropout=0.,bias='none',betas=[.9,.999],eps=1e-8,weight_decay=0.,grad_clip=1.,
                    schedule='linear warmup round(updates/16), cosine to floor'),
                source_commit=manifest['source_commit'],data_sha256=sha256_file((RELEASE if name=='calibration_fit' else DATA)/(name+'.jsonl')),
                budget=doses[name],seed=17)
            dump(out/'run_manifest.json',record)
            manifest['runs'][i]={**reg,'status':'running','parent_adapter':identity['parameter_digest']}
            atomic_json(OUT/'progress.json',manifest)
            tick=time.monotonic()
            nll_before=reference_nll(model,encoded[name],tokenizer,1)
            dump(out/'reference_nll_before.json',nll_before)
            if state=='calibration':
                check_encoded=[r for r,x in zip(encoded['calibration'],inputs['calibration']) if x['calibration_split']=='check']
                check_before=reference_nll(model,check_encoded,tokenizer,1)
            history,saved=train(model,encoded[name],schedules[stage],lrs[stage],tokenizer,out,
                identity=dict(run_id=reg['run_id'],data_sha256=record['data_sha256'],parent=identity['parameter_digest'],source_commit=manifest['source_commit']),
                checkpoint_steps={64,128,256} if stage=='main' else {32},
                midpoint=(lambda m,s=state:ev(s,'midpoint')) if stage=='main' else None,
                deadline=min(deadline,time.time()+LIMITS['training_run_seconds']))
            nll_after=reference_nll(model,encoded[name],tokenizer,1)
            dump(out/'reference_nll_after.json',nll_after)
            if state=='calibration':
                check_after=reference_nll(model,check_encoded,tokenizer,1)
            checkpoint=out/f"checkpoint_{reg['updates']}"
            # Independently deserialize the entire saved tensor map before any child.
            actual=parameter_digest(model,True);restore_adapter(model,checkpoint)
            if parameter_digest(model,True)!=actual or parameter_digest(model)!=base_hash:
                raise ValueError('Checkpoint/base identity check failed')
            if len(history)!=reg['updates'] or sum(r['supervised_tokens'] for r in history)!=doses[name]['supervised_response_tokens']:
                raise ValueError('Frozen update/token dose mismatch')
            checkpoints[state]=checkpoint
            record.update(status='completed',finished_at_utc=stamp(),elapsed_seconds=time.monotonic()-tick,
                final_adapter=actual,checkpoint=str(checkpoint),reference_nll_before=nll_before,reference_nll_after=nll_after,
                warning='reference_nll_not_reduced' if nll_after['nll']>=nll_before['nll'] else None,
                frozen_base_unchanged=True,recoverable_state=json.loads((out/'recovery/latest.json').read_text()))
            dump(out/'run_manifest_final.json',record)
            manifest['runs'][i]={k:v for k,v in record.items() if k!='budget'}
            atomic_json(OUT/'progress.json',manifest)
            if state=='calibration':
                fcal=ev('calibration','calibration')
                cal=dict(status='completed',before=summarize(bcal),after=summarize(fcal),
                    reference_nll_before=nll_before,reference_nll_after=nll_after,
                    check_reference_nll_before=check_before,check_reference_nll_after=check_after,
                    initial_adapter=identity['parameter_digest'],final_adapter=actual,
                    fit_check={split:dict(before=summarize([r for r in bcal if r['problem_id'] in {x['problem_id'] for x in inputs['calibration'] if x['calibration_split']==split}]),
                                          after=summarize([r for r in fcal if r['problem_id'] in {x['problem_id'] for x in inputs['calibration'] if x['calibration_split']==split}])) for split in ('fit','check')},
                    learning_warning=record['warning'],accuracy_used_as_admission_gate=False)
                dump(OUT/'ARITH_CALIBRATION_RESULTS.json',cal)
                projection=projected_remainder(history,list(evaluation_records.values()),1088,
                    sum(doses[x['data']]['processed_nonpadding_tokens'] for x in regs[1:]),
                    LIMITS['planned_generations']-(budget.used-fault))
                projection.update(remaining_process_seconds=deadline-time.time())
                dump(OUT/'measured_admission.json',projection)
                if not continue_after_measurement(hard_errors=[],
                    resource_available=projection['projected_process_seconds']<=projection['remaining_process_seconds'],
                    accuracy=summarize(fcal)['pass_at_1'],nll_improved=nll_after['nll']<nll_before['nll']):
                    raise TimeoutError('Complete fixed factorial does not fit measured phase budget; preserve calibration and stop')
            elif state in ('C','B'):
                ev(state,'probes')
        # No score-based branch: all four children exist before common free decoding.
        for state in STATES:
            restore_adapter(model,checkpoints[state])
            ev(state,'discovery_sampled');ev(state,'discovery_greedy')
        for state in STATES[2:]:
            restore_adapter(model,checkpoints[state]);ev(state,'sentinel')
        if budget.used!=LIMITS['planned_generations']+fault or len(manifest['evaluations'])!=len(events):
            raise ValueError('Finite queue not fully accounted')
        if parameter_digest(model)!=base_hash:raise ValueError('Frozen base changed')
        manifest['status']='completed'
    except BaseException as exc:
        manifest.update(status='failed_hard_or_resource',exception_type=type(exc).__name__,exception_message=str(exc))
        for r in manifest['runs']:
            if r['status']=='running':r.update(status='failed',reason=type(exc).__name__)
            elif r['status']=='not_run':r['reason']='Phase stopped: '+type(exc).__name__
        raise
    finally:
        manifest.update(finished_at_utc=stamp(),process_worker_seconds=time.monotonic()-start,
            reserved_generations=budget.used,peak_memory_allocated_bytes=torch.cuda.max_memory_allocated(),
            optional_prefix_status='not_run_core_priority',optional_n8_status='not_run_core_priority')
        dump(OUT/'run_manifest_final.json',manifest)
        atomic_json(OUT/'progress.json',manifest)
        # Compact identity list also covers binary checkpoints and recovery states.
        dump(OUT/'export_manifest.json',dict(created_at_utc=stamp(),files={str(p.relative_to(OUT)):
            dict(sha256=sha256_file(p),bytes=p.stat().st_size) for p in sorted(OUT.rglob('*')) if p.is_file()}))


def launch(snapshot,ledger,power_on,current_rate,previous=None):
    source();dry_run()
    carry=validate_previous(Path(previous)) if previous else None
    if bool(carry)!=(OUT.name=='thursday_arithmetic_v2_r2'):
        raise ValueError('Continuation and output identity disagree')
    if sha256_file(ledger)!=OLD_LEDGER_HASH:raise ValueError('Historical ledger differs; never reset it')
    prior=json.loads(Path('experiments/thursday_probe/PHASE_LEDGER.json').read_text())
    if not prior['closed'] or prior['total_charged_seconds_across_phases']!=7372 or prior['reservations']!=0:
        raise ValueError('Prior phase not reconciled')
    if OUT.exists():raise FileExistsError('No automatic phase replay or overwrite')
    now=datetime.now(timezone.utc);started=datetime.fromisoformat(power_on.replace('Z','+00:00'))
    if carry and started!=datetime.fromisoformat(carry['power_on_at_utc'].replace('Z','+00:00')):
        raise ValueError('Continuation must preserve the original powered-on window')
    age=(now-started).total_seconds()
    maximum_age=LIMITS['whole_window_seconds']-LIMITS['process_seconds']-LIMITS['kill_grace_seconds']-LIMITS['export_shutdown_reserve_seconds']
    if age<0 or (not carry and age>maximum_age):raise ValueError('Insufficient whole-window admission time')
    if not 0<current_rate<=LIMITS['maximum_current_rate_cny_per_hour']:
        raise ValueError('Current verified hourly price exceeds phase cap')
    server=server_preflight({'min_free_gib':LIMITS['minimum_free_disk_gib']},Path(snapshot))
    if importlib.metadata.version('peft')!='0.17.1':raise ValueError('Pinned PEFT required')
    now=datetime.now(timezone.utc)
    age=(now-started).total_seconds()
    if not carry and age>maximum_age:
        raise ValueError('Preflight consumed the complete-queue admission margin')
    cap=continuation_cap(age,carry['charged_seconds'] if carry else 0)
    guard=LIMITS['kill_grace_seconds']
    OUT.mkdir()
    preflight=dict(server=server,power_on_at_utc=power_on,age_seconds=age,limits=LIMITS,
        verified_current_rate_cny_per_hour=current_rate,
        whole_window_compute_cost_bound_cny=current_rate*LIMITS['whole_window_seconds']/3600,
        historical_ledger_sha256=OLD_LEDGER_HASH,historical_phase_seconds=7372,
        phase_process_allowance_seconds=LIMITS['process_seconds']+LIMITS['kill_grace_seconds'],
        continuation=carry,current_attempt_process_cap_seconds=cap,
        budget_basis='Owner-approved finite protocol within existing CNY3000 ceiling; no recharge or extra machine.',
        remaining_historical_money_allowance='unknown; ceiling is not a measured account balance')
    dump(OUT/'preflight.json',preflight)
    tick=time.monotonic()
    command=['timeout','--signal=TERM',f'--kill-after={guard}s',f'{cap}s',sys.executable,'-m',
             'experiments.thursday_probe_v2.queue','worker','--snapshot',snapshot]
    with (OUT/'stdout.log').open('x') as stream:
        code=subprocess.call(command,stdout=stream,stderr=subprocess.STDOUT,env={**os.environ,
            'THU_V2_BOUNDED':'thursday_arithmetic_v2_r1','THU_V2_DEADLINE':str(time.time()+cap),
            'THU_V2_OUTPUT':str(OUT),'THU_V2_PREVIOUS':str(previous) if previous else '',
            'TOKENIZERS_PARALLELISM':'false','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
    elapsed=time.monotonic()-tick
    receipt=dict(run_id=OUT.name,status='completed' if code==0 else 'failed',exit_code=code,
        wall_seconds=elapsed,charged_seconds=math.ceil(elapsed),process_cap_seconds=cap,guard_seconds=guard,
        started_at_utc=now.isoformat(),finished_at_utc=stamp(),historical_ledger_sha256=OLD_LEDGER_HASH,
        historical_ledger_unchanged=sha256_file(ledger)==OLD_LEDGER_HASH,
        new_phase_allowance_seconds=LIMITS['process_seconds']+guard,continuation=carry,command=command[:4]+['PINNED_RUNTIME']+command[5:-1]+['PINNED_MODEL_SNAPSHOT'])
    dump(OUT/'resource_receipt.json',receipt)
    dump(OUT/'phase_ledger.json',dict(closed=True,reservations=0,prior_receipts=22,prior_charged_seconds=7372,
        phase_allowance_seconds=LIMITS['process_seconds']+guard,receipt=receipt,
        previous_attempt_charged_seconds=carry['charged_seconds'] if carry else 0,
        total_charged_seconds_across_phases=7372+receipt['charged_seconds']+(carry['charged_seconds'] if carry else 0)))
    # The parent runs after worker stdout, failure traceback and receipt are closed.
    dump(OUT/'export_manifest_final.json',dict(created_at_utc=stamp(),files={str(p.relative_to(OUT)):
        dict(sha256=sha256_file(p),bytes=p.stat().st_size) for p in sorted(OUT.rglob('*')) if p.is_file()}))
    print(json.dumps(receipt,indent=2));return code


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',nargs='?',default='dry-run',choices=['dry-run','launch','worker'])
    parser.add_argument('--snapshot');parser.add_argument('--ledger');parser.add_argument('--power-on-at-utc')
    parser.add_argument('--current-rate-cny',type=float);parser.add_argument('--continue-from');args=parser.parse_args()
    if args.action=='dry-run':print(json.dumps(dry_run(),indent=2))
    elif args.action=='worker':worker(args.snapshot)
    else:sys.exit(launch(args.snapshot,args.ledger,args.power_on_at_utc,args.current_rate_cny,args.continue_from))
