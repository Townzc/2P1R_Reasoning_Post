"""New extension process routing; frozen model/update/eval constructors are reused.

Only resume cursor/prefix selection differs. Forecasts remain observational,
while an independent per-attempt cost-bounded process-tree hard timer applies.
"""
from copy import deepcopy
import multiprocessing
import os
from pathlib import Path
import time
import traceback
import shutil
from experiments.sft_allocation_midpoint.common import dump,read,sha,digest,verify
from experiments.p011 import long_lr_r2_training as training
from experiments.p011.long_owner_execution import (engine_settings,validate_engine,software,
    validate_endpoint,save_raw)
from experiments.p011.long_evaluation import sampling
from experiments.p011.long_protocol import ENDPOINT_BATCH,ENDPOINT_BATCHES,endpoint_batches
from experiments.p011.ext4b_runtime_contract import STORE
from experiments.p011.ext3b_math_scope import math_requests,BATCHES
from experiments.p011.ext4b_encoded import EncodedRows
from experiments.p011.ext4b_training import ResumableJournal,train_with_checkpoints


def reuse_terminal_training(resume,out,identity,job,commit):
    """Copy an uncollected completed training stage; never allocate/train it again."""
    parent=Path(resume['parent_output']);out=Path(out)
    if not resume.get('training_terminal_complete'):return None
    child=read(parent/'TRAINING_PROCESS_RESULT.json');export=read(parent/'MODEL_EXPORT.json')
    joined=read(parent/'TRAINING_EXIT.json');trained=child['result'];step=job['U']
    if (read(parent/'IDENTITY.json')!=identity or trained['U']!=step
            or trained['model_export_sha256']!=digest(export)
            or trained['terminal_state']!=export['final_state']
            or joined.get('exitcode')!=0 or joined.get('joined_before_vllm') is not True
            or joined.get('model_export_file_sha256')!=sha(parent/'MODEL_EXPORT.json')
            or export['optimizer_updates_after_terminal_state']!=0 or export['evaluation_performed'] is not False):
        raise ValueError('Cannot reuse incomplete or foreign terminal training')
    state=parent/f'checkpoint_{step:04d}';record=read(state/'manifest.json')
    if record!=trained['terminal_state'] or sha(state/'state.pt')!=record['sha256'] or (state/'state.pt').stat().st_size!=record['bytes']:
        raise ValueError('Parent final state differs')
    verify(parent/'model_for_vllm',export['files'])
    names=['TRAINING_ENVIRONMENT.json','TRAINING_PROCESS_RESULT.json','TRAINING_COMPLETE_CYCLES.json','MODEL_EXPORT.json','TRAINING_EXIT.json']
    for folder in ('completed','intents','forecasts'):
        names += [str(p.relative_to(parent)) for p in sorted((parent/folder).glob('*.json'))
                  if p.stem.startswith('update_') or p.stem in ('terminal_state','terminal_model_export')]
    for folder in (f'checkpoint_{step:04d}','model_for_vllm'):
        names += [str(p.relative_to(parent)) for p in sorted((parent/folder).rglob('*')) if p.is_file()]
    copied={}
    for n in names:
        src=parent/n;dest=out/n;dest.parent.mkdir(parents=True,exist_ok=True)
        if src.is_symlink() or dest.exists():raise ValueError('Unsafe or repeated completed-stage copy')
        shutil.copyfile(src,dest);copied[n]={'bytes':dest.stat().st_size,'sha256':sha(dest)}
    dump(out/'RESTORED_COMPLETED_TRAINING.json',{'parent_output':str(parent),'files':copied,
        'optimizer_updates_reexecuted':0,'export_reexecuted':False,'binary_byte_copy_only':True,
        'prior_training_child_joined_and_parent_app_stopped':True})
    commit();return trained,child['update_seconds'],str(out/'model_for_vllm')


def evaluate_with_prefix(llm, constructor, rows, model_eos, out, key, store, commit, check, forecast, resume):
    """Reuse only previously committed complete endpoint batches; new tail once."""
    out=Path(out);times=[];cycles=[];prefix=[]
    parent=Path(resume['parent_output']) if resume is not None else None
    # Full cycle evidence is independently durable per batch in this new path.
    for first in range(0,len(rows),ENDPOINT_BATCH):
        index=first//ENDPOINT_BATCH;name=f'eval_{index:04d}';part=rows[first:first+ENDPOINT_BATCH]
        params=[sampling(r,model_eos) for r in part];intent={'requests':part,'sampling':params}
        check()
        prior=(parent/'completed'/(name+'.json')) if parent is not None else None
        if prior is not None and prior.exists() and not (parent/'endpoint_cycles'/(name+'.json')).exists():
            raise ValueError('Acknowledged endpoint lacks durable cycle evidence; never regenerate it')
        if prior is not None and prior.exists():
            ack=read(prior);rawfile=parent/'raw'/(name+'.json');raw=read(rawfile);cycle=read(parent/'endpoint_cycles'/(name+'.json'))
            if (read(parent/'intents'/(name+'.json'))!=intent or ack['count']!=len(part)
                    or ack['request_ids']!=[r['id'] for r in part] or ack['raw_file_sha256']!=sha(rawfile)
                    or len(raw)!=len(part) or cycle['batch']!=index or cycle['body_seconds']!=ack['seconds']
                    or cycle['seconds']<ack['seconds']):raise ValueError('Prior complete endpoint prefix differs')
            for folder in ('intents','completed','raw','forecasts','endpoint_cycles'):
                src=parent/folder/(name+'.json');dest=out/folder/(name+'.json');dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb') as f:f.write(src.read_bytes())
            prefix.append(name);times.append(cycle['seconds']);cycles.append(cycle)
            continue
        if parent is not None and any((parent/'completed'/f'eval_{j:04d}.json').exists() for j in range(index+1,BATCHES)):
            raise ValueError('Non-prefix prior endpoint completion is invalid')
        started=time.monotonic();dump(out/'forecasts'/(name+'.json'),forecast(endpoint_batches(len(rows)-first),list(times)))
        if not store.put(key+'/unit/'+name,intent,skip_if_exists=True):raise RuntimeError('New endpoint unit already attempted')
        dump(out/'intents'/(name+'.json'),intent);commit();tick=time.monotonic()
        returned=llm.generate([{'prompt_token_ids':r['prompt_token_ids']} for r in part],
                             [constructor(**p) for p in params],use_tqdm=False)
        raw=save_raw(part,params,returned);dump(out/'raw'/(name+'.json'),raw);commit()
        if (len(raw)!=len(part) or any(len(o['answers'])!=1 or o['id']!=r['id']
                or o['prompt_token_ids']!=r['prompt_token_ids'] for o,r in zip(raw,part))):
            raise ValueError('Partial backend batch is retained, never treated as complete')
        check();ack={'count':len(part),'raw_file_sha256':sha(out/'raw'/(name+'.json')),
            'request_ids':[r['id'] for r in part],'seconds':time.monotonic()-tick}
        dump(out/'completed'/(name+'.json'),ack)
        if not store.put(key+'/done/'+name,ack,skip_if_exists=True):raise RuntimeError('Duplicate new endpoint completion')
        commit();cycle={'batch':index,'seconds':time.monotonic()-started,'body_seconds':ack['seconds'],
            'volume_commits_included':3,'remote_unit_and_done_included':True}
        # This metadata commit is outside the original recorded three-commit cycle.
        dump(out/'endpoint_cycles'/(name+'.json'),cycle);commit();cycles.append(cycle);times.append(cycle['seconds'])
    dump(out/'REUSED_ENDPOINT_PREFIX.json',{'parent_output':str(parent) if parent else None,'batches':prefix,
        'old_completed_generations_repeated':False})
    dump(out/'ENDPOINT_COMPLETE_CYCLES.json',cycles)
    return times


def child(conn, model_assets, arm, inputs, out, identity, key, claim, stop, timing, job, resume):
    """Spawn-only actual training; its process must exit before vLLM allocation."""
    try:
        if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
            raise ValueError('Required deterministic CUDA environment missing')
        import modal
        from experiments.p011.long_owner_numeric import forecast
        volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
        store = modal.Dict.from_name(STORE, create_if_missing=False)
        volume.reload()
        def check():
            if time.time() >= stop-30: raise TimeoutError('Original full worker deadline')
            if store.get(key+'/claim') != claim: raise RuntimeError('Original claim changed')
        encoded = EncodedRows(Path(inputs)/'ENCODED.jsonl',read(Path(inputs)/'ROW_METADATA.json'),job['questions'])
        plan=read(Path(inputs)/(job['logical_id']+'_PLAN.json'));rates=read(Path(inputs)/'RATES_S-F15.json')
        training.validate_plan(encoded, plan, rates, arm)
        check()
        dump(Path(out)/'TRAINING_ENVIRONMENT.json',software())
        volume.commit()
        model, tokenizer, optimizer = training.load_model(model_assets, arm)
        journal = ResumableJournal(out,key,store,volume.commit,check,encoded,plan,rates,
            lambda left, observed: forecast(timing, left, ENDPOINT_BATCHES, observed, [], time.time()))
        result = train_with_checkpoints(model,tokenizer,optimizer,encoded,plan,rates,arm,
                                         out,journal,identity,resume)
        journal.complete()
        dump(Path(out)/'TRAINING_COMPLETE_CYCLES.json',journal.cycles)
        dump(Path(out)/'TRAINING_PROCESS_RESULT.json',dict(result=result,update_seconds=journal.times,
                                                          pid=os.getpid()))
        volume.commit()
        conn.send(('complete', result, journal.times))
    except BaseException:
        conn.send(('error', traceback.format_exc(), []))
        raise
    finally:
        conn.close()


def joined_training(inputs, out, assets, arm, identity, key, claim, stop, timing,
                    commit, reload_volume, job, resume=None, context=None):
    """The parent does not import torch or retain training CUDA allocations."""
    ctx = context or multiprocessing.get_context('spawn')
    parent, remote = ctx.Pipe()
    process = ctx.Process(target=child, args=(remote,assets,arm,str(inputs),str(out),
                                             identity,key,claim,stop,timing,job,resume))
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


def worker_body(job, inputs, out, identity, key, claim, stop, timing, store, volume, resume=None):
    """Exact admitted payload through train-exit, vLLM and durable raw completion.

    The outer entry owns source/review/budget/resource checks, atomic dispatch
    and claim, a process-tree hard timer and original failure preservation.
    This function is not a separately callable cloud entry or approval bypass.
    """
    from experiments.p011.long_owner_numeric import forecast
    if (job['kind'] not in ('student','baseline') or job['arm'] not in training.ARMS
            or job['model']['model_id'] != training.ARMS[job['arm']]['model_id']
            or job['model']['revision'] != training.ARMS[job['arm']]['revision']
            or identity['job_sha256'] != digest(job)
            or stop <= time.time()
            or os.environ.get('VLLM_USE_V1') != '1'):
        raise ValueError('Exact admitted long payload, identity and original deadline required')
    inputs,out = Path(inputs),Path(out)
    def check():
        if time.time() >= stop-30:raise TimeoutError('Original long worker deadline')
        if store.get(key+'/claim') != claim:raise RuntimeError('Original claim changed')
    check()
    verify(inputs,job['input_files'])
    rows = read(inputs/'ENDPOINT_GPU.json')
    validate_endpoint(rows,job['context'])
    if job['kind']=='student':
        reused=reuse_terminal_training(resume,out,identity,job,volume.commit) if resume else None
        result,training_times,model_path = reused or joined_training(inputs,out,job['model'],job['arm'],
            identity,key,claim,stop,timing,volume.commit,volume.reload,job,resume)
    else:
        if job['arm']=='S-F15':raise ValueError('The 1.5B baseline is shared, never duplicated')
        verify(job['model']['remote_path'],job['model']['files'])
        result,training_times,model_path = None,[],job['model']['remote_path']
        dump(out/'BASELINE_PROOF.json',dict(training_updates=0,model=job['model']))
        volume.commit()
    check()
    from transformers import AutoTokenizer
    from vllm import LLM,SamplingParams
    environment=software()
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,
                                             trust_remote_code=False,use_fast=True)
    if tokenizer.eos_token_id!=151645:raise ValueError('Original Instruct tokenizer EOS differs')
    for r in rows:
        text=tokenizer.decode(r['prompt_token_ids'],skip_special_tokens=False,
                              clean_up_tokenization_spaces=False)
        if digest(text)!=r['prompt_text_sha256']:
            raise ValueError('Native prompt tokenization differs from admitted exact text')
        SamplingParams(**sampling(r,job['eos_token_ids']))
    dump(out/'LINUX_CONSTRUCTORS.json',dict(count=len(rows),environment=environment,
        before_vllm_model_allocation=True,all_native_prompt_texts_verified=True))
    volume.commit()
    rows=math_requests(rows)
    dump(out/'MATH_SCOPE.json',{'original_bound_inputs':3300,'generated_scope':2500,
        'order':'greedy500 then sample seeds0,1,2,3 each500','batch_size':ENDPOINT_BATCH,
        'AIME24_AIME25_AMC23':'NOT_RUN_BY_OWNER_OPTION2','partial_complete_endpoints_authorized':True})
    volume.commit()
    projection=forecast(timing,0,endpoint_batches(len(rows)),training_times,[],time.time())
    dump(out/'PRE_ENGINE_FORECAST.json',projection)
    llm=LLM(model=model_path,tokenizer=model_path,**engine_settings(job['context']))
    config=llm.llm_engine.vllm_config
    native=config.model_config.hf_config.eos_token_id
    native=native if isinstance(native,list) else [native]
    if (not native or not set(native)<=set(job['eos_token_ids'])
            or config.model_config.hf_config.architectures!=['Qwen2ForCausalLM']):
        raise ValueError('Pinned Qwen model architecture or automatic EOS differs')
    dump(out/'ENGINE.json',dict(actual=validate_engine(config,job['context']),
        requested=engine_settings(job['context']),model_path=model_path))
    volume.commit()
    endpoint_times=evaluate_with_prefix(llm,SamplingParams,rows,job['eos_token_ids'],out,key,store,
        volume.commit,check,lambda n,t:forecast(timing,0,n,training_times,t,time.time()),resume)
    check()
    value=dict(training=result,raw_endpoint_count=len(rows),unique_questions=500,
        evaluation_scope='MATH500_ONLY_COMPLETE_ENDPOINTS',descriptive_benchmarks='NOT_RUN_BY_OWNER_OPTION2',
        endpoint_batch_seconds=endpoint_times,training_update_seconds=training_times,
        score='NOT_SCORED; full raw oracle and original frozen local scorer required',
        model_export_relative_path='model_for_vllm' if result is not None else None,
        restored_training_prefix_step=(job['U'] if resume.get('training_terminal_complete') else read(out/'RESTORED_CHECKPOINT.json')['step']) if resume else 0,
        reused_terminal_training=bool(resume and resume.get('training_terminal_complete')),
        reused_endpoint_prefix=read(out/'REUSED_ENDPOINT_PREFIX.json')['batches'])
    dump(out/'RESULT.json',value)
    volume.commit()
    return value
