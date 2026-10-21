"""One engineering preflight per arm; original train/export/join/engine functions.

No scientific scores, formal cell results, retry or checkpoint resume.
"""
from pathlib import Path
import os,time,traceback,multiprocessing
from experiments.p011 import long_execution as original,long_training as full
from experiments.p011.long_preflight import subset,training
from experiments.p011.long_evaluation import sampling
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,verify


class PhaseJournal(original.WholeAnswerJournal):
    """Original whole-update journal plus terminal phases through their final commit."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        base_commit=self.commit;self.phase_start=None;self.close_phase=None;self.phases=[]
        def commit():
            base_commit()
            if self.close_phase is not None:
                self.phases.append({'phase':self.close_phase,'seconds':time.monotonic()-self.phase_start,
                                    'final_volume_commit_included':True})
                self.close_phase=None;self.phase_start=None
        self.commit=commit
    def begin(self,name,record):
        if name in ('terminal_state','terminal_model_export'):
            if self.phase_start is not None:raise ValueError('Prior terminal phase not durably closed')
            self.phase_start=time.monotonic()
        return super().begin(name,record)
    def end(self,name,record):
        result=super().end(name,record)
        if name in ('terminal_state','terminal_model_export'):self.close_phase=name
        return result
    def complete(self):
        super().complete()
        if self.phase_start is not None or [x['phase'] for x in self.phases]!=['terminal_state','terminal_model_export']:
            raise ValueError('Complete state/export duration records required')


def hard_measurement_note(check,phase,remaining,observed):
    check()
    return {'engineering_preflight':True,'forecast_performed':False,
            'owner_decision_sha256':subset.OWNER_SHA,'phase':phase,
            'remaining_units':remaining,'complete_observations':list(observed),
            'bounded_measurement_exception':True,'not_formal_runtime_admission':True}


def child(conn,model_assets,arm,inputs,out,identity,key,claim,stop,timing):
    try:
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG')!=':4096:8':raise ValueError('Original deterministic CUDA setting required')
        import modal
        volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
        store=modal.Dict.from_name('p011-once-20261020',create_if_missing=False);volume.reload()
        def check():
            if time.time()>=stop-30:raise TimeoutError('Original engineering hard window')
            if store.get(key+'/claim')!=claim:raise RuntimeError('Original engineering claim changed')
        encoded,plan,rates=[read(Path(inputs)/n) for n in ('encoded.json','plan.json','rates_'+arm+'.json')]
        subset.validate(encoded,plan,rates,arm);check()
        dump(Path(out)/'TRAINING_ENVIRONMENT.json',original.software());volume.commit()
        tick=time.monotonic();model,tokenizer,optimizer=full.load_model(model_assets,arm)
        dump(Path(out)/'MODEL_LOAD_TIMING.json',{'seconds':time.monotonic()-tick,'arm':arm,'engineering_preflight':True});volume.commit();check()
        journal=PhaseJournal(out,key,store,volume.commit,check,encoded,plan,rates,
            lambda left,obs:hard_measurement_note(check,'training',left,obs))
        result=training.train_terminal_subset(model,tokenizer,optimizer,encoded,plan,rates,arm,out,journal,identity)
        journal.complete();dump(Path(out)/'TRAINING_COMPLETE_CYCLES.json',journal.cycles)
        dump(Path(out)/'TERMINAL_PHASE_TIMINGS.json',journal.phases)
        dump(Path(out)/'TRAINING_PROCESS_RESULT.json',{'result':result,'update_seconds':journal.times,'pid':os.getpid()})
        volume.commit();check();conn.send(('complete',result,journal.times))
    except BaseException:
        conn.send(('error',traceback.format_exc(),[]));raise
    finally:conn.close()


def joined_training(inputs, out, assets, arm, identity, key, claim, stop, timing,
                    commit, reload_volume, context=None):
    """The parent does not import torch or retain training CUDA allocations."""
    ctx = context or multiprocessing.get_context('spawn')
    parent, remote = ctx.Pipe()
    process = ctx.Process(target=child, args=(remote,assets,arm,str(inputs),str(out),
                                             identity,key,claim,stop,timing))
    try:
        process.start()
        remote.close()
        if not parent.poll(max(0,stop-time.time()-30)):
            raise TimeoutError('Training original window expired')
        kind, result, times = parent.recv()
        process.join(timeout=max(0,min(30,stop-time.time()-15)))
        if kind!='complete' or process.is_alive() or process.exitcode!=0:
            raise RuntimeError('Training child failed or did not exit: '+str(result))
        reload_volume()
        export = read(Path(out)/'MODEL_EXPORT.json')
        if (digest(export)!=result['model_export_sha256']
                or export['relative_path']!='model_for_vllm'
                or export['final_state']!=result['terminal_state']
                or export['optimizer_updates_after_terminal_state']!=0):
            raise ValueError('Full terminal model/export binding differs')
        verify(Path(out)/'model_for_vllm', export['files'])
        dump(Path(out)/'TRAINING_EXIT.json',dict(pid=process.pid,exitcode=process.exitcode,
            joined_before_vllm=True,model_export_file_sha256=sha(Path(out)/'MODEL_EXPORT.json')))
        commit()
        return result,times,str(Path(out)/'model_for_vllm')
    finally:
        if process.pid is not None and process.is_alive():
            process.kill()
            process.join(timeout=5)
        parent.close()
        remote.close()


def worker_body(job,inputs,out,identity,key,claim,stop,timing,store,volume):
    if (job['kind']!='engineering_preflight' or job['arm'] not in full.ARMS
            or job['model']['model_id']!=full.ARMS[job['arm']]['model_id']
            or job['model']['revision']!=full.ARMS[job['arm']]['revision']
            or identity['engineering_preflight'] is not True or identity['job_sha256']!=digest(job)
            or stop!=timing['worker_start_epoch']+timing['worker_hard_seconds']
            or timing.get('owner_decision_sha256')!=subset.OWNER_SHA
            or os.environ.get('VLLM_USE_V1')!='1'):
        raise ValueError('Exact admitted engineering-only identity required')
    inputs,out=Path(inputs),Path(out)
    def check():
        if time.time()>=stop-30:raise TimeoutError('Original engineering hard window')
        if store.get(key+'/claim')!=claim:raise RuntimeError('Engineering claim changed')
    check();verify(inputs,job['input_files'])
    rows=read(inputs/'ENDPOINT_GPU.json');subset.validate_requests(rows,job['context'])
    proof=read(inputs/'SUBSET_PROOF.json')
    if proof['selected_requests_sha256']!=digest(rows) or proof['arm']!=job['arm']:
        raise ValueError('Actual admitted engineering subset differs')
    tick=time.monotonic()
    result,training_times,model_path=joined_training(inputs,out,job['model'],job['arm'],
        identity,key,claim,stop,timing,volume.commit,volume.reload)
    dump(out/'TRAINING_PARENT_INTERVAL.json',{'seconds':time.monotonic()-tick,'includes_spawn_load_training_state_export_exit_join':True})
    check()
    from transformers import AutoTokenizer
    from vllm import LLM,SamplingParams
    environment=original.software()
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,trust_remote_code=False,use_fast=True)
    if tokenizer.eos_token_id!=151645:raise ValueError('Original tokenizer EOS differs')
    for row in rows:
        text=tokenizer.decode(row['prompt_token_ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
        if digest(text)!=row['prompt_text_sha256']:raise ValueError('Original native prompt differs')
        SamplingParams(**sampling(row,job['eos_token_ids']))
    dump(out/'LINUX_CONSTRUCTORS.json',{'count':len(rows),'environment':environment,
        'before_vllm_model_allocation':True,'all_native_prompt_texts_verified':True});volume.commit();check()
    tick=time.monotonic();llm=LLM(model=model_path,tokenizer=model_path,**original.engine_settings(job['context']))
    config=llm.llm_engine.vllm_config;native=config.model_config.hf_config.eos_token_id
    native=native if isinstance(native,list) else [native]
    if (not native or not set(native)<=set(job['eos_token_ids'])
            or config.model_config.hf_config.architectures!=['Qwen2ForCausalLM']):raise ValueError('Pinned Qwen EOS/config differs')
    dump(out/'ENGINE.json',{'actual':original.validate_engine(config,job['context']),
        'requested':original.engine_settings(job['context']),'model_path':model_path})
    volume.commit();dump(out/'ENGINE_START_TIMING.json',{'seconds':time.monotonic()-tick,'engine_commit_included':True});check()
    endpoint_times=original.evaluate(llm,SamplingParams,rows,job['eos_token_ids'],out,key,store,
        volume.commit,check,lambda n,t:hard_measurement_note(check,'endpoint',n,t))
    check();raw=read(out/'raw/eval_0000.json')
    # Token counts are timing metadata only; no decoding/scoring/answer extraction.
    tokens=sum(len(x['answers'][0]['token_ids']) for x in raw)
    value={'engineering_preflight':True,'scientific_cell_result':False,'no_correctness_scoring':True,
        'training':result,'raw_endpoint_count':len(rows),'training_update_seconds':training_times,
        'endpoint_batch_seconds':endpoint_times,'generated_tokens':tokens,
        'tokens_per_whole_batch_second':tokens/endpoint_times[0],
        'actual_engine_request_count':32,'formal_engine_batch_count':512,
        'formal_batch_throughput_is_not_measured':True,'not_a_timing_upper_bound':True,
        'model_export_relative_path':'model_for_vllm'}
    dump(out/'RESULT.json',value);volume.commit();return value
