"""Only the original unattempted T72 C6 cell; all prior raw bytes stay preserved."""
from pathlib import Path
from math import isfinite
import time
from experiments.p010.common import read,dump,digest,budget_check,verify
from experiments.p010.cue_benchmark_group import model_reuse

KEY='cue/t72_remaining_r1'
PARENT='cue/benchmark_group_r1'
RUN='t72_n400_math'
HARD_SECONDS=1200
RESERVE='2.52'
RATE=.001097+4*.0000131+32*.00000222


def forecast(elapsed,completed,times,observed,prior_I):
    if (type(completed) is not int or not 0<=completed<=10 or len(times)!=completed
            or not observed or not isfinite(elapsed) or elapsed<0
            or any(not isfinite(x) or x<=0 for x in list(times)+list(observed))):
        raise ValueError('All old and new completed batch times required')
    maximum=max(list(observed)+list(times));remaining=1.2*(maximum*(10-completed)+600)
    total=elapsed+remaining
    if total>1170:raise TimeoutError('Original1200 window cannot contain remaining work')
    return dict(elapsed_seconds=elapsed,completed_batches=completed,total_batches=10,
        original_observed_seconds=list(observed),new_completed_seconds=list(times),
        maximum_observed_seconds=maximum,remaining_seconds=remaining,total_seconds=total,
        uncalibrated_setup_and_closeout_seconds=600,margin=1.2,first_paid_measurement_exceptions=0,
        not_a_future_host_bound=True,budget=budget_check('I',prior_I,RESERVE,(total+700)*RATE))


def check_parent(spec,store):
    b=spec['failed_parent']
    if (store.get(PARENT+'/claim')!=b['claim'] or store.get(PARENT+'/terminal')!=b['terminal']
            or b['terminal']['status']!='failed' or store.get(PARENT+'/'+RUN+'/cell')!=b['cell']):
        raise ValueError('Original failed claim/terminal/cell reservation must remain')
    for first in range(0,2500,256):
        for kind in ('batch','batch_done'):
            if store.get(PARENT+'/'+RUN+'/'+kind+f'/{first:05d}') is not None:
                raise ValueError('An original T72 output may already have been attempted')


def generate(inputs,out,spec,claim,started,deadline,prior,store,volume):
    import torch
    from vllm import LLM,SamplingParams
    from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs,actual_engine
    from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
    inputs,out=Path(inputs),Path(out)
    if (torch.cuda.device_count()!=1 or 'H100' not in torch.cuda.get_device_name(0)
            or torch.cuda.get_device_properties(0).total_memory<75*1024**3
            or abs(deadline-started-HARD_SECONDS)>.001 or store.get(KEY+'/claim')!=claim):
        raise ValueError('One original H100 and true bounded claim required')
    check_parent(spec,store);verify(inputs,spec['input_files'])
    roster=read(inputs/(RUN+'.json'));binding=spec['corrected_model_binding']
    if (roster['run']!=RUN or roster['new_outputs']!=2500 or len(roster['rows'])!=2500
            or roster['selected_cue']!=[1249] or roster['new_training_updates']!=0
            or binding['remote_path']!='/evidence/p010-20261019/students/t72_s17_n400_k1/merged'):
        raise ValueError('Only original2500 requests and exact existing merged model')
    dump(out/'BENCHMARK_ROSTER.json',roster)
    dump(out/'BEFORE_MODEL_FORECAST.json',forecast(time.time()-started,0,[],spec['observed_batch_seconds'],prior));volume.commit()
    # Original pure verifier checks every saved weight/tokenizer hash and terminal.
    dump(out/'MODEL_REUSE_PROOF.json',model_reuse(RUN,binding,store));volume.commit()
    rows=roster['rows'];params=[x['sampling'] for x in rows];constructed=[SamplingParams(**x) for x in params]
    llm=LLM(model=binding['remote_path'],tokenizer=binding['remote_path'],**engine_kwargs())
    dump(out/'ENGINE.json',actual_engine(llm.llm_engine.vllm_config));volume.commit();times=[]
    for first in range(0,2500,256):
        unit=f'{first:05d}';part=rows[first:first+256]
        if store.get(KEY+'/claim')!=claim:raise ValueError('New once-only claim changed')
        if store.get(binding['parent']['terminal_key'])!=binding['parent']['terminal']:raise ValueError('Completed model parent changed')
        f=forecast(time.time()-started,len(times),times,spec['observed_batch_seconds'],prior)
        dump(out/'batch_forecasts'/(unit+'.json'),f)
        intent=dict(rows=part,sampling=params[first:first+256],epoch=time.time())
        if not store.put(KEY+'/batch/'+unit,intent,skip_if_exists=True):raise RuntimeError('Remaining batch already attempted')
        dump(out/'batch_intents'/(unit+'.json'),intent);volume.commit();tick=time.monotonic()
        outputs=llm.generate([dict(prompt_token_ids=x['input_ids']) for x in part],constructed[first:first+256],use_tqdm=False)
        raw=returned_records(part,params[first:first+256],outputs);dump(out/'raw'/(unit+'.json'),raw);volume.commit()
        if len(raw)!=len(part) or any(x['output_count']!=1 or x['candidate_id']!=q['candidate_id'] or x['prompt_token_ids']!=q['input_ids'] for x,q in zip(raw,part)):
            raise ValueError('Original returned raw identity differs; preserve raw')
        ack=dict(count=len(part),raw_sha256=digest(raw),seconds=time.monotonic()-tick)
        dump(out/'batch_acks'/(unit+'.json'),ack);times.append(ack['seconds'])
        if not store.put(KEY+'/batch_done/'+unit,ack,skip_if_exists=True):raise RuntimeError('Remaining batch ack exists')
        volume.commit()
    if time.time()>=deadline-15:raise TimeoutError('Bounded original closeout window')
    result=dict(run=RUN,new_outputs=2500,batch_seconds=times,new_training_updates=0,
        new_checkpoint_loads=0,new_merge_operations=0,prior18871_regenerated=0,parent_remains_failed=True)
    dump(out/'RESULT.json',result);volume.commit();return result
