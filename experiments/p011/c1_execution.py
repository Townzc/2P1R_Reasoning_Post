"""C1 worker body and complete proof checks, pending shared full-path CR.

No Modal entry, dispatch or implicit admission. Reuses original token/NLL code;
new outer runtime must supply exact inputs, audited measured timing, budget,
source/claim/resource admission and original immutable base assets.
"""
from decimal import Decimal, ROUND_CEILING
import math
import os
from pathlib import Path
import time

from experiments.p011 import c1_nll, c1_evidence
from experiments.sft_allocation_midpoint.common import dump, read, sha, digest, verify

CATEGORY_CAP = Decimal('12')
CUTOFF_EPOCH = 1792645200  # 2026-10-22T05:00:00Z, checked by new boundary test.
CHUNK = 32


def validate_spec(spec):
    limits = spec['limits']
    for k in ('worker_seconds','platform_seconds','startup_seconds','closeout_seconds',
              'full_result_window_seconds'):
        if type(limits[k]) is not int or limits[k] <= 0:
            raise ValueError('Positive exact integer C1 limits required')
    if (limits['startup_seconds'] < 600
            or limits['platform_seconds'] < limits['worker_seconds']+60
            or limits['full_result_window_seconds'] < limits['startup_seconds']+
                limits['platform_seconds']+limits['closeout_seconds']
            or type(limits['future_allowance_seconds']) not in (int,float)
            or not math.isfinite(limits['future_allowance_seconds'])
            or limits['future_allowance_seconds'] < 300
            or type(limits['measurement_exceptions']) is not int
            or limits['measurement_exceptions'] != 0
            or spec['model']['model_id'] != c1_nll.MODEL['model_id']
            or spec['model']['revision'] != c1_nll.MODEL['revision']
            or spec['model']['remote_path'] != '/evidence/mp-engineering-20261012-r1/assets/model'
            or spec['forward'] != {'dtype':'bfloat16','loss_dtype':'float32','attention':'sdpa',
                'model_batch_size':1,'journal_chunk_size':32,'use_cache':False,
                'training':False,'adapter':False,'original_EOS':151643}):
        raise ValueError('Frozen base/forward configuration or finite window differs')
    times=spec['timing']['complete_chunk_seconds']
    if (not times or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in times)
            or spec['timing']['measurement_basis_accepted'] is not True
            or spec['timing'].get('whole_chunk_iteration_timing') is not True
            or not spec['timing']['source_evidence_files']
            or spec['timing']['basis_kind'] not in ('actual_C1_complete_chunk',
                'independently_accepted_prior_measurement_proxy')
            or spec['timing']['target_scope'] != 'C1_sequential32_original_token_forwards_including_FP32_loss'
            or (spec['timing']['basis_kind']=='independently_accepted_prior_measurement_proxy'
                and spec['timing'].get('uncalibrated_proxy_scope_accepted') is not True)):
        raise ValueError('Actual accepted complete C1-compatible batch timing required')
    rate=Decimal(str(limits['usd_per_second']));reserve=Decimal(str(limits['reserved_usd']))
    if (not rate.is_finite() or rate<=0 or not reserve.is_finite() or reserve<=0
            or reserve < (rate*(limits['startup_seconds']+limits['platform_seconds'])).quantize(
                Decimal('.01'),rounding=ROUND_CEILING)):
        raise ValueError('Whole billed window must fit fixed reservation')


def forecast(spec, elapsed, batches_left, observed, prior_reserved):
    validate_spec(spec)
    if (type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0
            or type(batches_left) is not int or batches_left<0
            or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in observed)):
        raise ValueError('Complete real elapsed/batch observations required')
    all_times=spec['timing']['complete_chunk_seconds']+list(observed)
    seconds=1.2*(elapsed+batches_left*max(all_times)+spec['limits']['future_allowance_seconds'])
    rate=Decimal(str(spec['limits']['usd_per_second']))
    money=(rate*(Decimal(str(seconds))+spec['limits']['startup_seconds'])).quantize(
        Decimal('.01'),rounding=ROUND_CEILING)
    prior=Decimal(str(prior_reserved));reserve=Decimal(str(spec['limits']['reserved_usd']))
    if (not prior.is_finite() or prior<0 or seconds>spec['limits']['worker_seconds']-30
            or prior+reserve>CATEGORY_CAP or money>reserve
            or money>Decimal('.8')*(CATEGORY_CAP-prior)):
        raise ValueError('C1 full-time or original80% C budget forecast exceeded')
    return {'elapsed_seconds':elapsed,'remaining_chunks':batches_left,
        'max_complete_chunk_seconds':max(all_times),'all_original_observations_retained':True,
        'actual_observation_count':len(observed),'total_scenario_seconds':seconds,
        'timing_basis_kind':spec['timing']['basis_kind'],
        'future_uncalibrated_seconds':spec['limits']['future_allowance_seconds'],
        'margin_fraction':.2,'forecast_usd':str(money),'prior_reserved_usd':str(prior),
        'new_reserved_usd':str(reserve),'category':'C','cap_usd':'12',
        'forecast_is_not_a_runtime_guarantee_or_actual_expense':True}


def load_base(spec,out,deadline_epoch):
    """Pinned untouched BF16 base, no tokenizer, PEFT, generation or optimizer."""
    import importlib.metadata
    import torch
    from transformers import AutoModelForCausalLM
    validate_spec(spec)
    if time.time()>=deadline_epoch or os.environ.get('CUBLAS_WORKSPACE_CONFIG')!=':4096:8':
        raise ValueError('Original bounded deterministic environment required')
    expected={'torch':'2.8.0','transformers':'4.56.2','numpy':'2.2.6','safetensors':'0.6.2'}
    versions={p:importlib.metadata.version(p) for p in expected}
    if any(versions[k].split('+')[0]!=v for k,v in expected.items()):
        raise ValueError('Pinned C1 runtime versions differ')
    if not torch.cuda.is_available() or torch.version.cuda!='12.8':
        raise ValueError('Actual CUDA12.8 GPU required')
    prop=torch.cuda.get_device_properties(0)
    if 'H100' not in prop.name or prop.total_memory < 79_000_000_000:
        raise ValueError('Actual original H10080GB required')
    root=Path(spec['model']['remote_path'])
    verify(root,spec['model']['files'])
    if (root/'adapter_config.json').exists():
        raise ValueError('Untouched original base required, no adapter')
    torch.set_num_threads(4);torch.set_num_interop_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.deterministic=True
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(17);torch.cuda.manual_seed_all(17)
    tick=time.monotonic()
    model=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,
        trust_remote_code=False,torch_dtype=torch.bfloat16,attn_implementation='sdpa')
    model.requires_grad_(False);model.eval();model.to('cuda:0');model.config.use_cache=False
    if (getattr(model,'peft_config',None) or model.training
            or model.config.model_type!='qwen2'
            or any(p.requires_grad or p.dtype!=torch.bfloat16 or p.device.type!='cuda'
                   for p in model.parameters()) or time.time()>=deadline_epoch):
        raise ValueError('Actual untouched base load/configuration differs')
    dump(Path(out)/'MODEL_LOADED.json',{'versions':versions,'cuda':torch.version.cuda,
        'device':prop.name,'total_memory':prop.total_memory,'model':spec['model'],
        'forward':spec['forward'],'load_seconds':time.monotonic()-tick,
        'model_training':False,'optimizer_created':False,'adapter_loaded':False,
        'new_tokenization':False,'deterministic_seed':17,'threads':4})
    return model


def run_body(spec,tasks,memberships,out,basis,store,key,claim,commit,
             worker_start,deadline_epoch,prior_reserved,loader=load_base):
    """One invocation after outer claim. No retry/resume; partial remains failed."""
    validate_spec(spec)
    if (not basis or deadline_epoch!=worker_start+spec['limits']['worker_seconds']
            or time.time()>=deadline_epoch
            or worker_start+spec['limits']['worker_seconds']+spec['limits']['closeout_seconds']>CUTOFF_EPOCH
            or store.get(key+'/claim')!=claim):
        raise ValueError('Original source/claim/window must be admitted first')
    needed={m['sequence_sha256'] for rows in memberships.values() for m in rows}
    keys=sorted(tasks);basis_sha=digest(basis)
    if needed!=set(keys) or not keys:
        raise ValueError('Complete exact token roster required')
    for k,t in tasks.items():
        if k!=t['sequence_sha256'] or k!=digest({'input_ids':t['input_ids'],'labels':t['labels']}):
            raise ValueError('Frozen original sequence changed')
    out=Path(out);out.mkdir(parents=False,exist_ok=False);confirmed={};times=[];cycles=[]
    monotonic_origin=time.monotonic()
    try:
        initial=forecast(spec,time.time()-worker_start,(len(keys)+31)//32,[],prior_reserved)
        dump(out/'INTENT.json',{'basis':basis,'basis_sha256':basis_sha,'task_ids':keys,
            'membership_sha256':digest(memberships),'deadline_epoch':deadline_epoch,
            'forward_retries':0,'chunk_size':CHUNK,'worker_start_epoch':worker_start,
            'prior_reserved_usd':str(prior_reserved),'spec_sha256':digest(spec),'claim':claim})
        dump(out/'MEMBERSHIPS.json',memberships);dump(out/'INITIAL_FORECAST.json',initial);commit()
        model=loader(spec,out,deadline_epoch);commit()
        for first in range(0,len(keys),CHUNK):
            cycle_start=time.monotonic()
            part=keys[first:first+CHUNK];number=first//CHUNK;chunk=out/'chunks'/f'{number:05d}'
            f=forecast(spec,time.time()-worker_start,(len(keys)-first+31)//32,times,prior_reserved)
            if store.get(key+'/claim')!=claim:raise ValueError('Original C1 claim changed')
            unit=key+f'/chunk/{number:05d}'
            plan={'first_index':first,'sequence_ids':part,'basis_sha256':basis_sha}
            if not store.put(unit,plan,skip_if_exists=True):
                raise ValueError('C1 chunk already attempted; never replay')
            chunk.mkdir(parents=True,exist_ok=False);dump(chunk/'FORECAST.json',f)
            dump(chunk/'INTENT.json',plan);commit();tick=time.monotonic();records=[]
            for task_id in part:
                if time.time()>=deadline_epoch:raise TimeoutError('Original C1 deadline reached')
                task=tasks[task_id];start=time.monotonic()
                dump(chunk/(task_id+'.ATTEMPT.json'),{'sequence_sha256':task_id,
                    'basis_sha256':basis_sha,'started_epoch':time.time()})
                result=c1_nll.forward_one(model,task)
                c1_evidence.validate_forward_result(task,result)
                record={'result':result,'forward_seconds':time.monotonic()-start,
                    'basis_sha256':basis_sha,'task_sha256':digest(task)}
                dump(chunk/(task_id+'.RESULT.json'),record)
                records.append({'sequence_sha256':task_id,
                    'result_file_sha256':sha(chunk/(task_id+'.RESULT.json'))})
                confirmed[task_id]=result
            commit()  # retain all per-sequence vectors before complete-chunk acknowledgment
            ack={'basis_sha256':basis_sha,'first_index':first,'records':records,'count':len(part),
                'elapsed_seconds':time.monotonic()-tick,'final_confirmation_write_excluded_from_elapsed':True}
            dump(chunk/'CONFIRMED.json',ack);commit()
            if not store.put(key+f'/chunk_done/{number:05d}',ack,skip_if_exists=True):
                raise ValueError('C1 complete-chunk acknowledgment already exists')
            # This ends AFTER all three volume commits and the remote completed
            # acknowledgment. The old ack duration remains a body-only diagnostic.
            cycle_end=time.monotonic()
            cycles.append({'chunk':number,'started_offset_seconds':cycle_start-monotonic_origin,
                'finished_offset_seconds':cycle_end-monotonic_origin,
                'elapsed_seconds':cycle_end-cycle_start,'volume_commits_included':3,
                'remote_chunk_done_included':True,
                'body_ack_elapsed_seconds':ack['elapsed_seconds']})
            times.append(cycles[-1]['elapsed_seconds'])
        if time.time()>=deadline_epoch:raise TimeoutError('Original C1 completion deadline reached')
        # Persist complete timings at finalization. The final proof/summary write
        # is outside the per-chunk scope and must fit the fixed future allowance.
        dump(out/'COMPLETE_ITERATION_TIMES.json',{'cycles':cycles,
            'timing_scope':'loop_entry_through_all_three_commits_and_remote_chunk_done',
            'final_proof_summary_commit_included':False,
            'finalization_covered_by_fixed_future_allowance':True})
        summary=c1_nll.descriptive_summary(memberships,confirmed)
        dump(out/'DESCRIPTIVE_SUMMARY.json',summary)
        dump(out/'ALL_CONFIRMED.json',{'basis_sha256':basis_sha,'unique_sequences':len(keys),
            'chunks':(len(keys)+31)//32,'summary_file_sha256':sha(out/'DESCRIPTIVE_SUMMARY.json'),
            'elapsed_seconds':time.time()-worker_start,'final_marker_write_excluded_from_elapsed':True,
            'actual_A3_accepted':False});commit()
        return {'unique_sequences':len(keys),'original_group_members':sum(map(len,memberships.values())),
            'complete_chunk_seconds':times,'summary_sha256':sha(out/'DESCRIPTIVE_SUMMARY.json'),
            'new_training':0,'new_generation':0,'new_tokenization':0,'actual_A3_accepted':False}
    except BaseException as exc:
        dump(out/'FAILED.json',{'type':type(exc).__name__,'message':str(exc),
            'basis_sha256':basis_sha,'automatic_retry_allowed':False,
            'confirmed_complete_iteration_timings':cycles,
            'partial_is_not_a_completed_summary':True});commit();raise


def check_body(spec,out,tasks,memberships,basis,store_records,key,claim):
    """Read-only exact original evidence and forecast replay; no NLL/stat rerun."""
    validate_spec(spec);out=Path(out)
    proof=c1_evidence.check_confirmed_evidence(out,tasks,memberships,basis)
    intent=read(out/'INTENT.json');keys=sorted(tasks);times=[]
    timing=read(out/'COMPLETE_ITERATION_TIMES.json');cycles=timing['cycles']
    if (timing.get('timing_scope')!='loop_entry_through_all_three_commits_and_remote_chunk_done'
            or timing.get('final_proof_summary_commit_included') is not False
            or timing.get('finalization_covered_by_fixed_future_allowance') is not True
            or len(cycles)!=(len(keys)+31)//32):
        raise ValueError('Complete whole-iteration timing scope required')
    if (intent['spec_sha256']!=digest(spec) or intent['claim']!=claim
            or store_records.get(key+'/claim')!=claim):
        raise ValueError('Original exact source/spec/claim differs')
    initial=read(out/'INITIAL_FORECAST.json')
    if initial!=forecast(spec,initial['elapsed_seconds'],(len(keys)+31)//32,[],intent['prior_reserved_usd']):
        raise ValueError('Original initial numeric admission differs')
    for first in range(0,len(keys),32):
        number=first//32;chunk=out/'chunks'/f'{number:05d}'
        f=read(chunk/'FORECAST.json');ack=read(chunk/'CONFIRMED.json')
        if (f!=forecast(spec,f['elapsed_seconds'],(len(keys)-first+31)//32,times,intent['prior_reserved_usd'])
                or store_records.get(key+f'/chunk/{number:05d}')!=read(chunk/'INTENT.json')
                or store_records.get(key+f'/chunk_done/{number:05d}')!=ack):
            raise ValueError('Original numeric forecast or confirmed store record differs')
        if type(ack['elapsed_seconds']) not in (int,float) or not math.isfinite(ack['elapsed_seconds']) or ack['elapsed_seconds']<=0:
            raise ValueError('Finite positive complete chunk timing required')
        cycle=cycles[number]
        start=cycle['started_offset_seconds'];end=cycle['finished_offset_seconds']
        elapsed=cycle['elapsed_seconds']
        if (cycle.get('chunk')!=number or cycle.get('volume_commits_included')!=3
                or cycle.get('remote_chunk_done_included') is not True
                or cycle.get('body_ack_elapsed_seconds')!=ack['elapsed_seconds']
                or any(type(x) not in (int,float) or not math.isfinite(x) for x in (start,end,elapsed))
                or not 0<=start<end or elapsed<=0
                or not math.isclose(elapsed,end-start,rel_tol=0,abs_tol=1e-7)
                or elapsed<ack['elapsed_seconds']
                or (number and start<cycles[number-1]['finished_offset_seconds'])):
            raise ValueError('Actual complete iteration timing differs or excludes acknowledged work')
        times.append(elapsed)
    return {**proof,'complete_chunk_seconds':times,'source_claim_provider_outer_checks_still_required':True}
