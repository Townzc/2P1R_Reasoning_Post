"""Prepared C6 benchmark body; future exact selected-cue wrapper owns admission.

No entrypoint, timer, deployment or dispatch is supplied here. The future outer
entry must validate full input/model provenance and start its whole-worker hard
clock before invoking this body. No new state load, optimizer, merge or training.
"""
from pathlib import Path
import time
from experiments.p010.common import dump,read,verify,digest,budget_check

RATE=.001097+4*.0000131+32*.00000222


def scenario(elapsed,completed,times,config,prior):
    from math import ceil,isfinite
    count=config['new_outputs'];batches=ceil(count/256);observed=config['observed_batch_seconds']
    if (type(count) is not int or count<=0 or type(completed) is not int
            or not 0<=completed<batches or len(times)!=completed or not observed
            or any(not isfinite(x) or x<=0 for x in list(times)+list(observed))
            or not isfinite(elapsed) or elapsed<0
            or type(config['worker_seconds']) is not int or config['worker_seconds']<=30):
        raise ValueError('Complete original output and measured interval roster required')
    maximum=max(list(observed)+list(times));remaining=1.2*(maximum*(batches-completed)+600)
    total=elapsed+remaining
    if total>config['worker_seconds']-30:raise TimeoutError('Original benchmark remainder exceeds its exact worker window')
    return dict(elapsed_seconds=elapsed,completed_batches=completed,full_batches=batches,
        actual_completed_seconds=list(times),original_observations=list(observed),maximum_seconds=maximum,
        remaining_seconds=remaining,total_seconds=total,setup_allowance_seconds=600,margin=1.2,
        calibrated_bound=False,first_paid_measurement_exceptions=0,
        budget=budget_check('I',prior,config['reserved_usd'],(total+700)*RATE))


def check_persisted_model(run,binding,store):
    if run not in ('base_math','base_gsm','s1_n400_math','t72_n400_math'):
        raise ValueError('Only the original four C6 benchmark cells')
    if binding['new_training_updates']!=0 or binding['new_checkpoint_loads']!=0 or binding['new_merge_operations']!=0:
        raise ValueError('Only the unchanged already persisted evaluated model may be reused')
    if run.startswith('base_'):
        if binding['parent'] is not None:raise ValueError('Original base has no student parent')
    else:
        parent=binding['parent']
        expected_prefix='existing_s1_samples/s1_s17_n400' if run=='s1_n400_math' else 'student/t72_s17_n400_k1'
        if (parent['terminal_key']!=expected_prefix+'/terminal' or parent['terminal']['status']!='completed'
                or store.get(parent['terminal_key'])!=parent['terminal']
                or parent['original_merged_files']!=binding['files']):
            raise ValueError('Complete original evaluated parent/model binding differs')
    verify(binding['remote_path'],binding['files'])
    # The exact full wrapper also binds original tokenizer and model hashes.
    return dict(run=run,model_files=binding['files'],parent=binding['parent'],
        new_training_updates=0,new_checkpoint_loads=0,new_merge_operations=0)


def generate(out,roster,binding,config,store,key,claim,volume,started,deadline,prior):
    """Called once, after permanent claim, exact frozen roster and hard timer."""
    from vllm import LLM,SamplingParams
    from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs,actual_engine
    from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
    out=Path(out);rows=roster['rows'];count=len(rows);run=roster['run']
    if (key!='cue/benchmark_r1/'+run or count!=roster['new_outputs'] or count!=config['new_outputs']
            or count<=0 or len({r['candidate_id'] for r in rows})!=count
            or abs(deadline-started-config['worker_seconds'])>.001 or store.get(key+'/claim')!=claim):
        raise ValueError('Only the admitted whole original benchmark lifetime is permitted')
    model_proof=check_persisted_model(run,binding,store)
    dump(out/'MODEL_REUSE_PROOF.json',model_proof);dump(out/'BENCHMARK_ROSTER.json',roster);volume.commit()
    params=[r['sampling'] for r in rows];constructed=[SamplingParams(**p) for p in params]
    dump(out/'BEFORE_EVAL_FORECAST.json',scenario(time.time()-started,0,[],config,prior));volume.commit()
    llm=LLM(model=binding['remote_path'],tokenizer=binding['remote_path'],**engine_kwargs())
    dump(out/'ENGINE.json',actual_engine(llm.llm_engine.vllm_config));volume.commit()
    times=[]
    for offset in range(0,count,256):
        unit=f'{offset:05d}';part=rows[offset:offset+256]
        f=scenario(time.time()-started,len(times),times,config,prior)
        if store.get(key+'/claim')!=claim:raise ValueError('Original benchmark claim changed')
        if binding['parent'] is not None and store.get(binding['parent']['terminal_key'])!=binding['parent']['terminal']:
            raise ValueError('Original complete parent changed')
        dump(out/'batch_forecasts'/(unit+'.json'),f)
        intent=dict(rows=part,sampling=params[offset:offset+256],epoch=time.time())
        if not store.put(key+'/batch/'+unit,intent,skip_if_exists=True):raise RuntimeError('Original benchmark batch already attempted')
        dump(out/'batch_intents'/(unit+'.json'),intent);volume.commit();tick=time.monotonic()
        responses=llm.generate([dict(prompt_token_ids=r['input_ids']) for r in part],constructed[offset:offset+256],use_tqdm=False)
        raw=returned_records(part,params[offset:offset+256],responses)
        # Preserve every returned candidate before rejecting malformed output.
        dump(out/'raw'/(unit+'.json'),raw);volume.commit()
        if (len(raw)!=len(part) or any(x['output_count']!=1 or x['candidate_id']!=row['candidate_id']
                or x['prompt_token_ids']!=row['input_ids'] for x,row in zip(raw,part))):
            raise ValueError('Original benchmark response identity differs')
        ack=dict(count=len(part),raw_sha256=digest(raw),seconds=time.monotonic()-tick)
        times.append(ack['seconds']);dump(out/'batch_acks'/(unit+'.json'),ack)
        if not store.put(key+'/batch_done/'+unit,ack,skip_if_exists=True):raise RuntimeError('Original benchmark acknowledgment already exists')
        volume.commit()
    if time.time()>deadline:raise TimeoutError('Original full benchmark deadline exceeded')
    return dict(run=run,new_outputs=count,batch_seconds=times,new_training_updates=0,
        new_checkpoint_loads=0,new_merge_operations=0,existing_conditions_reused=roster['reused'],
        identical_empty_cue_aliases=roster['aliases'],seconds=time.time()-started)
