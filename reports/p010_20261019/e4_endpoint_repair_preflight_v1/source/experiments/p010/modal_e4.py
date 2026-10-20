"""Two authorized P010 OLMo diagnostic cells. No P009 dispatch or G0 override elsewhere."""
from pathlib import Path
import modal
from experiments.p010.common import read
ROOT=Path(__file__).resolve().parents[2]
SPEC='reports/p010_20261019/e4_runtime_v1/SPEC.json'
spec=read(ROOT/SPEC)
app=modal.App('p010-olmo-diagnostic')
volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
image=(modal.Image.debian_slim(python_version='3.12')
    .pip_install_from_requirements(ROOT/'experiments/learning_regime_p009/requirements_p0.txt')
    .env({'PYTHONPATH':'/workspace','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TOKENIZERS_PARALLELISM':'false','VLLM_WORKER_MULTIPROC_METHOD':'spawn','VLLM_USE_V1':'1','CUBLAS_WORKSPACE_CONFIG':':4096:8'}))
for name in list(spec['source_files'])+[SPEC]:image=image.add_local_file(ROOT/name,'/workspace/'+name,copy=True)


@app.function(image=image,gpu='H100!',cpu=(4,4),memory=(32768,32768),timeout=4560,startup_timeout=600,
    retries=0,max_containers=2,min_containers=0,buffer_containers=0,scaledown_window=2,
    single_use_containers=True,serialized=True,include_source=False,volumes={'/evidence':volume})
def worker(n,execution,review):
    import multiprocessing,time,traceback
    from experiments.p010.common import dump,read,verify,digest,utc
    from experiments.p010.runtime_support import source_check,hard_timer,compact
    from experiments.p010.e4_process import child
    start=time.time();stop=start+4500;timer=hard_timer(4500);run='e4_s17_n'+str(n)
    out=Path('/evidence/p010-20261019/e4')/run;inputs=Path('/evidence/p010-20261019/inputs')
    store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False)
    try:
        s=read('/workspace/'+SPEC);source_check(s)
        if n not in (400,3200):raise ValueError('Unknown E4 cell')
        claim=dict(run=run,execution=execution,epoch=start)
        if not store.put('e4/'+run+'/claim',claim,skip_if_exists=True):raise RuntimeError('Already attempted E4 cell')
        volume.reload();out.mkdir(parents=True,exist_ok=False);verify(inputs,s['input_files'])
        cfg=read(inputs/f'e4_n{n}_config.json')
        identity=dict(run_id=run,config=cfg,input_files=s['input_files'],base_files=s['model']['files'],execution=execution,source_files=s['source_files'],A1_A2_review=review)
        dump(out/'INTENT.json',dict(identity=identity,claim=claim,worker_start_epoch=start,hard_deadline_epoch=stop));volume.commit()
        ctx=multiprocessing.get_context('spawn');parent,remote=ctx.Pipe()
        proc=ctx.Process(target=child,args=(remote,str(inputs),str(out),s['model'],identity,claim,start,stop))
        proc.start();remote.close()
        if not parent.poll(max(1,stop-time.time()-30)):raise TimeoutError('Training child deadline')
        kind,value=parent.recv();proc.join(timeout=max(1,min(30,stop-time.time()-15)))
        if kind!='complete' or proc.is_alive() or proc.exitcode!=0:raise RuntimeError('Training child failed or not exited: '+str(value))
        volume.reload();dump(out/'TRAINING_EXIT.json',dict(pid=proc.pid,exitcode=proc.exitcode,joined_before_vllm=True));volume.commit()
        from vllm import LLM,SamplingParams
        from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs,actual_engine
        from experiments.learning_regime_p009.stage0_generation_engine_v2 import returned_records
        llm=LLM(model=str(out/'merged'),tokenizer=str(out/'merged'),**engine_kwargs())
        dump(out/'ENGINE.json',actual_engine(llm.llm_engine.vllm_config))
        rows=read(inputs/'olmo_gsm_zero.json');alltimes=[]
        for startrow in range(0,len(rows),256):
            if time.time()>stop-20:raise TimeoutError('Original evaluation deadline')
            part=rows[startrow:startrow+256];unit=f'{startrow:04d}'
            params=[dict(n=1,temperature=0,top_p=1,top_k=-1,repetition_penalty=1,max_tokens=512,seed=17,stop=None,stop_token_ids=[100257],ignore_eos=False,detokenize=True,skip_special_tokens=False,include_stop_str_in_output=True) for _ in part]
            intent=dict(rows=part,sampling=params,epoch=time.time())
            if not store.put('e4/'+run+'/eval/'+unit,intent,skip_if_exists=True):raise RuntimeError('Endpoint batch repeated')
            dump(out/'eval_intents'/(unit+'.json'),intent);volume.commit();tick=time.monotonic()
            outputs=llm.generate([{'prompt_token_ids':r['input_ids']} for r in part],[SamplingParams(**p) for p in params],use_tqdm=False)
            raw=returned_records(part,params,outputs);dump(out/'raw'/(unit+'.json'),raw);volume.commit()
            if len(raw)!=len(part) or any(x['output_count']!=1 or x['prompt_token_ids']!=r['input_ids'] for r,x in zip(part,raw)):raise ValueError('Raw output shape/identity mismatch')
            ack=dict(count=len(part),seconds=time.monotonic()-tick,raw_sha256=digest(raw));alltimes.append(ack['seconds'])
            dump(out/'eval_acks'/(unit+'.json'),ack);store.put('e4/'+run+'/eval_done/'+unit,ack,skip_if_exists=True);volume.commit()
        result=dict(run=run,training=value,raw_endpoint_count=len(rows),eval_batch_seconds=alltimes,seconds=time.time()-start,score='not evaluated on GPU')
        dump(out/'RESULT.json',result);volume.commit();packed=compact(out);volume.commit()
        terminal=dict(status='completed',finished_utc=utc(),result=result,artifact=packed,seconds_including_pack=time.time()-start)
        dump(out/'TERMINAL.json',terminal);volume.commit();store.put('e4/'+run+'/terminal',terminal,skip_if_exists=True);return terminal
    except BaseException as e:
        if out.exists():
            dump(out/'FAILURE.json',dict(type=type(e).__name__,error=str(e),traceback=traceback.format_exc(),utc=utc(),retry=False));volume.commit()
            store.put('e4/'+run+'/terminal',dict(status='failed',error=str(e)),skip_if_exists=True)
        raise
    finally:
        if 'proc' in locals() and proc.is_alive():proc.kill();proc.join(timeout=5)
        timer.cancel()


@app.local_entrypoint()
def main(n:int,receipt_dir:str,review_json:str):
    import subprocess,time
    from experiments.p010.common import dump,sha,require_published,budget_check,digest
    if n not in (400,3200):raise ValueError('Unknown E4 cell')
    commit=require_published(ROOT);review=read(review_json)
    if (review.get('decision') not in ('PASS','PASS-WITH-NOTES') or review.get('scope')!='p010-C8-A1-A2'
        or review.get('spec_sha256')!=sha(ROOT/SPEC) or sha(review['local_report_file'])!=review['report_sha256']):
        raise ValueError('Real exact A1/A2 report required')
    for name,expected in spec['source_files'].items():
        if sha(ROOT/name)!=expected or subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)!=(ROOT/name).read_bytes():raise ValueError('Unpublished source')
    budget=budget_check('T',0 if n==400 else 6.55,6.55,6.36)
    out=Path(receipt_dir);out.mkdir(parents=True,exist_ok=False)
    dump(out/'INTENT.json',dict(n=n,execution=commit,budget=budget,epoch=time.time(),review=review))
    call=worker.spawn(n,commit,{k:v for k,v in review.items() if k!='local_report_file'})
    dump(out/'SUBMITTED.json',dict(app_id=app.app_id,call_id=call.object_id,n=n))
    try:dump(out/'RESULT.json',call.get())
    except BaseException as e:dump(out/'ERROR.json',dict(type=type(e).__name__,error=str(e)));raise
