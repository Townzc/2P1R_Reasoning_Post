"""One finite exploratory W/C/R screen. Never starts a server or retries a phase.

The parent runs fresh owned worker groups sequentially, with a shared absolute
wall-clock deadline. Benchmark code runs only on the isolated Linux GPU host.
EvalPlus is process isolation, not a security sandbox. Inner FAIL attribution
retains the documented EvalPlus limitation; outer faults never become rewards.
"""
from __future__ import annotations
import argparse
from collections import Counter
import importlib.metadata
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import pickle
import platform
import re
import shutil
import signal
import subprocess
import sys
import time

from . import screen_plan as spec
from .contracts import (SuiteVerdict, VerdictStatus, identity_hash, reserve_batch,
                        record_sample, seal_batch, reward_from_verdicts,
                        build_fresh_fork_manifest, reserve_fork, read_records)
from .gpu_profile import (ProfileError, sha256, durable_json, pinned_json,
                          verify_model, launch_guarded, receive,
                          record_generation_return)
from .screen_scoring import load_problems, scoring_process


def remaining(args):
    value=args.worker_deadline_epoch-time.time()
    if value<=0: raise TimeoutError('shared screen deadline reached; no retry')
    return value


def disk_gate(root, *, initial=False):
    data=shutil.disk_usage(root).free; system=shutil.disk_usage('/').free
    if data < (40 if initial else 10)*1024**3 or system<3*1024**3:
        raise ProfileError('disk reserve exhausted; no deletion or retry')
    return {'data_free_bytes':data,'system_free_bytes':system}


def checked_files(root, hashes):
    root=Path(root).resolve()
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if actual!=set(hashes): raise ProfileError('checkpoint file set differs')
    for name,digest in hashes.items():
        p=root/name
        if p.is_symlink() or not p.resolve().is_relative_to(root) or sha256(p)!=digest:
            raise ProfileError('checkpoint file identity differs')
    return identity_hash(hashes)


def source_for(args,state):
    if state=='R':
        # Monotonic deadline expected by the original reusable hash verifier.
        identity=verify_model(args.model_path,args.model_manifest,time.monotonic()+remaining(args))
        return Path(args.model_path),identity,None
    if state not in {p[0] for p in spec.PHASES}: raise ProfileError('unknown source state')
    phase=Path(args.out)/state
    manifest=json.loads((phase/'checkpoint_manifest.json').read_text())
    completed=json.loads((phase/'phase_complete.json').read_text())
    if manifest['state']!=state or completed['committed_updates']!=spec.PREFIX_UPDATES:
        raise ProfileError('source phase is not complete')
    if manifest['plan_sha256']!=args.plan_identity or completed['plan_sha256']!=args.plan_identity:
        raise ProfileError('source belongs to a different plan')
    checked_files(phase/'final_model',manifest['files'])
    return phase/'final_model',identity_hash(manifest),phase


def validate_environment(args,plan):
    if platform.system()!='Linux' or sys.version_info[:2]!=(3,11):
        raise ProfileError('screen requires pinned Linux Python3.11')
    expected=dict(torch='2.11.0',transformers='4.56.2',trl='1.7.0',vllm='0.23.0',evalplus='0.3.1')
    versions={k:importlib.metadata.version(k) for k in expected}
    if any(versions[k].split('+')[0]!=v for k,v in expected.items()):
        raise ProfileError('locked package version mismatch')
    libc,version=platform.libc_ver()
    if libc!='glibc' or tuple(map(int,version.split('.')[:2]))<(2,35):
        raise ProfileError('pinned runtime needs glibc >=2.35')
    driver=subprocess.check_output(['nvidia-smi','--query-gpu=driver_version','--format=csv,noheader'],text=True).strip()
    if not driver or any(int(x.split('.')[0])<580 for x in driver.splitlines()):
        raise ProfileError('CUDA13 needs R580+ driver')
    if sha256(args.data_json)!=args.data_sha256: raise ProfileError('data changed')
    return versions


def start_scorer(args,selected):
    ctx=mp.get_context('spawn');conn,other=ctx.Pipe()
    proc=ctx.Process(target=scoring_process,args=(other,args.data_json,args.data_sha256,
        str(Path(args.out)/'references'),selected,args.scoring_fast_check,
        getattr(args,'recover_initialization_timeout',False),
        getattr(args,'recover_suite_watchdog',False)),daemon=False)
    proc.start();other.close()
    ready=receive(conn,min(180,remaining(args)),time.monotonic()+remaining(args))
    if not ready.get('ready'): raise ProfileError('scorer did not initialize')
    return conn,proc,ready['prompts']


def stop_scorer(args,conn,proc):
    conn.send(None);proc.join(timeout=min(5,remaining(args)));conn.close()
    if proc.is_alive() or proc.exitcode!=0: raise ProfileError('scorer did not exit cleanly')


def extract_code(text):
    blocks=re.findall(r'```(?:python|py)?\s*\n(.*?)```',text,re.S)
    return (blocks[-1] if blocks else text).strip()


def score_batch(args,batch,texts,token_ids,tasks,conn,mode,finish_reasons):
    if not(len(texts)==len(token_ids)==len(tasks)==len(finish_reasons)==len(batch.intent()['tasks'])):
        raise ProfileError('scoring batch shape mismatch')
    if tasks!=batch.intent()['tasks']: raise ProfileError('scoring task order mismatch')
    codes=[extract_code(t) for t in texts]
    durable_json(batch.directory/'scoring_inputs.json',{'codes':codes,'reward_mode':mode,
        'code_sha256':[identity_hash({'code':x}) for x in codes]})
    rewards=[];fatal=None
    for i,(text,ids,task,code,reason) in enumerate(zip(texts,token_ids,tasks,codes,finish_reasons)):
        base=extra=SuiteVerdict(VerdictStatus.MISSING,'not scored after earlier batch failure')
        if fatal is None:
            try:
                conn.send((task,code))
                request_limit=(600 if getattr(args,'recover_suite_watchdog',False) else
                    300 if getattr(args,'recover_initialization_timeout',False) else spec.SCORER_TIMEOUT_SECONDS)
                value=receive(conn,request_limit,time.monotonic()+remaining(args))
                base,extra=(SuiteVerdict(**value[k]) for k in ['base','extra'])
                rewards.append(float(reward_from_verdicts(base,extra,mode)))
            except BaseException as exc:
                fatal=exc
                if base.status==VerdictStatus.MISSING:
                    base=SuiteVerdict(VerdictStatus.TIMEOUT if isinstance(exc,TimeoutError)
                                     else VerdictStatus.SCORER_ERROR,repr(exc))
        record_sample(batch,sample_index=i,completion_text=text,completion_token_ids=ids,
                      base=base,extra=extra,finish_reason=reason)
    seal_batch(batch)
    if fatal is not None: raise ProfileError('unresolved scoring; saved batch cannot authorize update') from fatal
    return rewards


def reference_worker(args,plan):
    out=Path(args.out)/'references';os.environ['CUDA_VISIBLE_DEVICES']=''
    os.environ['XDG_CACHE_HOME']=str((out/'cache').resolve())
    problems=load_problems(args.data_json,args.data_sha256)
    selected=sorted(plan['train_ids']+plan['eval_ids'])
    if sorted(problems)!=selected: raise ProfileError('frozen split/data universe mismatch')
    from evalplus.evaluate import get_groundtruth
    from evalplus.eval import MBPP_OUTPUT_NOT_NONE_TASKS
    key=identity_hash({'plan':args.plan_identity,'data':args.data_sha256,'task_ids':selected})
    remaining(args)
    gt=get_groundtruth(problems,key,MBPP_OUTPUT_NOT_NONE_TASKS)
    if sorted(gt)!=selected: raise ProfileError('incomplete canonical references')
    empty=[]
    for task in selected:
        for suite in ['base','plus']:
            if len(gt[task][suite])!=len(problems[task][suite+'_input']) or len(gt[task][suite+'_time'])!=len(gt[task][suite]):
                raise ProfileError('reference timing/answer count mismatch')
        if not problems[task]['base_input']: raise ProfileError('empty base suite')
        if not problems[task]['plus_input']: empty.append(task)
    if empty!=['Mbpp/793']: raise ProfileError('unexpected empty-extra task roster')
    with (out/'groundtruth.pickle').open('xb') as f:
        pickle.dump(gt,f);f.flush();os.fsync(f.fileno())
    durable_json(out/'manifest.json',{'sha256':sha256(out/'groundtruth.pickle'),
        'task_ids':selected,'data_sha256':args.data_sha256,'plan_sha256':args.plan_identity,
        'empty_extra_pass_by_conjunction':empty,'canonical_reference_tasks':len(selected)})
    remaining(args)


def train_worker(args,plan):
    phase=next(x for x in plan['training_phases'] if x['name']==args.phase)
    out=Path(args.out)/args.phase;selected=plan['train_ids'];schedule=plan['schedules'][phase['schedule']]
    versions=validate_environment(args,plan)
    source,source_identity,source_phase=source_for(args,phase['source_state'])
    conn,scorer,prompts=start_scorer(args,selected)
    import torch
    from datasets import Dataset
    from transformers import AutoTokenizer, TrainerCallback
    from trl import GRPOConfig, GRPOTrainer
    if torch.cuda.device_count()!=1 or torch.cuda.get_device_properties(0).total_memory<75*1024**3 or not torch.cuda.is_bf16_supported():
        raise ProfileError('one >=75GiB bf16 GPU required')
    torch.cuda.reset_peak_memory_stats()
    tokenizer=AutoTokenizer.from_pretrained(source,local_files_only=True,trust_remote_code=False)
    rows=[{'task_id':task,'prompt':[{'role':'user','content':spec.INSTRUCTION+prompts[task].strip()}]} for task in selected]
    ds=Dataset.from_list(rows)
    maxlen=max(len(tokenizer.apply_chat_template(x['prompt'],add_generation_prompt=True)) for x in rows)+640
    config=GRPOConfig(output_dir=str(out/'trainer'),seed=phase['trainer_seed'],**plan['training_config'],
        model_init_kwargs={'dtype':'bfloat16','local_files_only':True,'trust_remote_code':False,'attn_implementation':'sdpa'},
        vllm_max_model_length=maxlen)
    if args.recover_initialization_timeout:
        from transformers.trainer_utils import SaveStrategy
        config.save_strategy=SaveStrategy.STEPS
        config.save_steps=32
        config.save_total_limit=None
        durable_json(out/'execution_repair.json',{
            'policy':'diagnose_only_unknown_candidate_initialization_timeout',
            'known_verdicts_unchanged':True,'scorer_request_cap_seconds':300,
            'periodic_checkpoint_steps':32,'checkpoint_deletion':False,
            'exact_resume_including_vllm_rng_verified':False})
    config_identity=identity_hash({'training':plan['training_config'],'maxlen':maxlen,'phase':phase,
                                   'schedule_sha256':plan['schedule_sha256'][phase['schedule']]})
    allfiles={str(p.relative_to(source)):p for p in source.rglob('*') if p.is_file()}
    tokenizer_files={k:v for k,v in allfiles.items() if 'token' in k or k in ['vocab.json','merges.txt','chat_template.jinja']}
    policy_files={k:v for k,v in allfiles.items() if k not in tokenizer_files}
    fork=build_fresh_fork_manifest(run_id=plan['run_id'],phase_id=args.phase,policy_files=policy_files,
        tokenizer_files=tokenizer_files,phase_config={'phase':phase,'training':plan['training_config'],'vllm_engine_seed':0},
        phase_seed=phase['trainer_seed'],prompt_schedule_sha256=plan['schedule_sha256'][phase['schedule']])
    reserve_fork(out/'fork',fork)
    durable_json(out/'input_receipt.json',{'plan_sha256':args.plan_identity,'source_state':phase['source_state'],
        'source_identity':source_identity,'config_identity':config_identity,'versions':versions,
        'max_model_length':maxlen,'train_ids':selected,'phase':phase,'fork_sha256':fork['record_sha256']})
    state={'batches':0,'active':None,'steps':0};started=time.monotonic()

    def reward(prompts,completions,completion_ids,task_id,trainer_state=None,**kwargs):
        remaining(args)
        batch=state['active']
        texts=[c[0]['content'] if isinstance(c,list) and len(c)==1 else c for c in completions]
        if batch is None or len(texts)!=16 or any(not isinstance(t,str) for t in texts):
            raise ProfileError('unexpected trainer reward contract')
        returned=json.loads((batch.directory/'generation_return.json').read_text())
        if returned['completion_ids']!=completion_ids or returned['decoded_text']!=texts:
            raise ProfileError('reward input differs from saved backend return')
        durable_json(batch.directory/'raw_generations.json',{'texts':texts,'completion_ids':completion_ids,
            'task_id':list(task_id),'committed_updates':int(trainer_state.global_step),
            'policy_identity_kind':'source_manifest_and_committed_update_lineage'})
        return score_batch(args,batch,texts,completion_ids,list(task_id),conn,phase['reward'],
                           ['generation_boundary_not_provided_by_trl_reward_hook']*16)

    class FixedSampler:
        def __iter__(self): return iter(spec.sampler_indices(selected,schedule))
        def __len__(self): return len(schedule)*16*4
        def set_epoch(self,epoch):
            if epoch!=0: raise ProfileError('unexpected extra training epoch')

    class Callback(TrainerCallback):
        def on_train_begin(self,a,s,c,model=None,optimizer=None,**kwargs):
            inner=getattr(optimizer,'optimizer',optimizer)
            if type(inner).__name__!='Adafactor' or len(inner.state)!=0 or s.global_step!=0 or not all(p.requires_grad for p in model.parameters()):
                raise ProfileError('phase must start from fresh full-model Adafactor')
            durable_json(out/'fresh_optimizer.json',{'class':type(inner).__name__,'state_entries':len(inner.state),
                'initial_global_step':0,'full_model_parameters':sum(p.numel() for p in model.parameters())})
        def on_pre_optimizer_step(self,a,s,c,model=None,**kwargs):
            remaining(args);disk_gate(args.out)
            grads=[p.grad for p in model.parameters() if p.grad is not None]
            if not grads or any(not bool(torch.isfinite(g).all()) for g in grads):
                raise ProfileError('missing/nonfinite gradients; update forbidden')
            step=int(s.global_step)+1
            durable_json(out/f'pre_update_{step:04d}.json',{'step':step,'all_finite':True,'gradient_tensors':len(grads)})
        def on_step_end(self,a,s,c,**kwargs):
            step=int(s.global_step)
            if step!=state['steps']+1 or not 1<=step<=phase['updates'] or state['batches']!=step:
                raise ProfileError('unexpected update/generation dose')
            state['steps']=step
            durable_json(out/f'update_{step:04d}.json',{'committed_update':step,'elapsed_seconds':time.monotonic()-started,
                'cuda_peak_allocated':torch.cuda.max_memory_allocated(),'cuda_peak_reserved':torch.cuda.max_memory_reserved()})
            remaining(args)
        def on_log(self,a,s,c,logs=None,**kwargs):
            clean={k:v for k,v in (logs or {}).items() if isinstance(v,(str,int,float,bool)) or v is None}
            if any(isinstance(v,(int,float)) and not math.isfinite(v) for v in clean.values()):
                raise ProfileError('nonfinite trainer metric')
            target=out/'metrics';target.mkdir(exist_ok=True)
            # Trainer can emit both a final summary and a final step at the same global step.
            durable_json(target/f'{len(list(target.iterdir())):05d}.json',{'step':int(s.global_step),'logs':clean})

    class Trainer(GRPOTrainer):
        def _get_train_sampler(self,dataset=None): return FixedSampler()
        def _generate_single_turn(self,prompt_ids,images,multimodal_fields):
            result=super()._generate_single_turn(prompt_ids,images,multimodal_fields)
            ids,_=result
            if state['active'] is None: raise ProfileError('unreserved generation')
            record_generation_return(state['active'],prompt_ids,ids,
                self.processing_class.batch_decode(ids,skip_special_tokens=True),
                self.processing_class.batch_decode(ids,skip_special_tokens=False))
            return result
        def _generate_and_score_completions(self,inputs):
            remaining(args);disk_gate(args.out)
            i=state['batches']
            if i>=phase['updates'] or self.state.global_step!=i: raise ProfileError('extra generation or replay')
            tasks=[x['task_id'] for x in inputs]
            if tasks!=schedule[i]: raise ProfileError('prompt schedule differs from frozen paired schedule')
            state['active']=reserve_batch(out/'batches',run_id=plan['run_id'],phase_id=args.phase,
                batch_index=i,tasks=tasks,config_sha256=config_identity,
                policy_sha256=identity_hash({'source':source_identity,'phase':args.phase,'committed_updates':i}))
            t=time.monotonic();result=super()._generate_and_score_completions(inputs)
            state['batches']+=1
            durable_json(state['active'].directory/'generation_complete.json',{'global_step':int(self.state.global_step),
                'last_loaded_step':int(self._last_loaded_step),'seconds':time.monotonic()-t})
            if self._last_loaded_step!=self.state.global_step: raise ProfileError('rollout weights not synchronized')
            state['active']=None
            return result

    trainer=Trainer(model=str(source),args=config,train_dataset=ds,processing_class=tokenizer,
                    reward_funcs=reward,callbacks=[Callback()])
    if source_phase is not None:
        probe_manifest=json.loads((source_phase/'reload_probe_manifest.json').read_text())
        if sha256(source_phase/'reload_probe.pt')!=probe_manifest['sha256']: raise ProfileError('source probe changed')
        probe=torch.load(source_phase/'reload_probe.pt',map_location='cpu',weights_only=True)
        ids=tokenizer.apply_chat_template(probe_manifest['prompt'],add_generation_prompt=True,return_tensors='pt')
        if not torch.equal(ids,probe['input_ids']): raise ProfileError('source tokenizer rendering changed')
        trainer.model.eval()
        with torch.inference_mode(): actual=trainer.model(input_ids=ids.to('cuda')).logits[:,-1,:].float().cpu()
        ok=bool(torch.allclose(actual,probe['logits'],atol=0.02,rtol=0.002))
        durable_json(out/'source_reload_check.json',{'passed':ok,'max_abs_logit_difference':float((actual-probe['logits']).abs().max()),
                    'scope':'one_TRAIN_prompt_last_token_fresh_model_not_optimizer_resume'})
        if not ok: raise ProfileError('fork reload mismatch')
    try:
        trainer.train(resume_from_checkpoint=False)
    except BaseException:
        if args.recover_initialization_timeout:
            try:
                remaining(args);disk_gate(args.out)
                step=int(trainer.state.global_step)
                if (step!=state['steps'] or (step and not (out/f'update_{step:04d}.json').exists())
                    or (out/f'pre_update_{step+1:04d}.json').exists()):
                    raise ProfileError('cannot snapshot uncertain optimizer commit')
                checkpoint=out/'trainer'/f'checkpoint-{step}'
                if not checkpoint.exists():trainer._save_checkpoint(trainer.model,None)
                durable_json(out/'failure_checkpoint.json',{
                    'committed_updates':step,'path':str(checkpoint),
                    'pending_batch_must_not_be_replayed':True,
                    'exact_resume_including_vllm_rng_verified':False})
            except BaseException as save_error:
                durable_json(out/'failure_checkpoint_error.json',{'error':repr(save_error)})
        raise
    if state['steps']!=phase['updates'] or state['batches']!=phase['updates']:
        raise ProfileError('phase incomplete')
    remaining(args);disk_gate(args.out)
    if any(not bool(torch.isfinite(p).all()) for p in trainer.model.parameters()):
        raise ProfileError('nonfinite final weights; checkpoint cannot be accepted')
    final=out/'final_model';trainer.save_model(str(final));tokenizer.save_pretrained(final)
    hashes={}
    for f in sorted(final.rglob('*')):
        if f.is_file():
            remaining(args)
            with f.open('rb') as stream: os.fsync(stream.fileno())
            hashes[str(f.relative_to(final))]=sha256(f)
    if 'model.safetensors' not in hashes: raise ProfileError('complete model export absent')
    fd=os.open(final,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
    durable_json(out/'checkpoint_manifest.json',{'state':args.phase,'source_identity':source_identity,
        'plan_sha256':args.plan_identity,'updates':state['steps'],'files':hashes,'optimizer_state_retained':False})
    ids=tokenizer.apply_chat_template(rows[0]['prompt'],add_generation_prompt=True,return_tensors='pt').to('cuda')
    trainer.model.eval()
    with torch.inference_mode(): logits=trainer.model(input_ids=ids).logits[:,-1,:].float().cpu()
    with (out/'reload_probe.pt').open('xb') as f:
        torch.save({'input_ids':ids.cpu(),'logits':logits},f);f.flush();os.fsync(f.fileno())
    durable_json(out/'reload_probe_manifest.json',{'sha256':sha256(out/'reload_probe.pt'),'prompt':rows[0]['prompt']})
    stop_scorer(args,conn,scorer)
    durable_json(out/'phase_complete.json',{'phase':args.phase,'plan_sha256':args.plan_identity,
        'committed_updates':state['steps'],'training_completions':16*state['batches'],
        'elapsed_seconds':time.monotonic()-started,'cuda_peak_allocated':torch.cuda.max_memory_allocated(),
        'cuda_peak_reserved':torch.cuda.max_memory_reserved(),'fresh_optimizer':True,'retry':False})


def evaluation_worker(args,plan):
    state_name=args.phase.removeprefix('eval_')
    if state_name not in spec.EVAL_STATES: raise ProfileError('unplanned evaluation state')
    out=Path(args.out)/args.phase;selected=plan['eval_ids'];versions=validate_environment(args,plan)
    source,source_identity,_=source_for(args,state_name)
    conn,scorer,prompts=start_scorer(args,selected)
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    tokenizer=AutoTokenizer.from_pretrained(source,local_files_only=True,trust_remote_code=False)
    prompt_ids={t:tokenizer.apply_chat_template([{'role':'user','content':spec.INSTRUCTION+prompts[t].strip()}],add_generation_prompt=True) for t in selected}
    maxlen=max(map(len,prompt_ids.values()))+640
    durable_json(out/'input_receipt.json',{'state':state_name,'source_identity':source_identity,
        'plan_sha256':args.plan_identity,'eval_ids':selected,'versions':versions,'max_model_len':maxlen,
        'sampling':plan['evaluation'],'request_seeds':{t:spec.eval_seed(t) for t in selected}})
    llm=LLM(model=str(source),tokenizer=str(source),dtype='bfloat16',trust_remote_code=False,
            tensor_parallel_size=1,gpu_memory_utilization=0.3,max_model_len=maxlen,
            max_num_seqs=32,max_num_batched_tokens=4096,seed=0)
    config_identity=identity_hash(plan['evaluation']);completed=0;started=time.monotonic()
    for start in range(0,len(selected),spec.EVAL_TASKS_PER_BATCH):
        remaining(args);disk_gate(args.out)
        ts=selected[start:start+spec.EVAL_TASKS_PER_BATCH];tasks=[t for t in ts for _ in range(spec.EVAL_SAMPLES)]
        batch=reserve_batch(out/'batches',run_id=plan['run_id'],phase_id=args.phase,
            batch_index=start//spec.EVAL_TASKS_PER_BATCH,tasks=tasks,config_sha256=config_identity,policy_sha256=source_identity)
        params=[SamplingParams(n=8,temperature=1.0,top_p=1.0,top_k=-1,max_tokens=640,seed=spec.eval_seed(t)) for t in ts]
        results=llm.generate([{'prompt_token_ids':prompt_ids[t]} for t in ts],sampling_params=params,use_tqdm=False)
        # Save everything returned before validation/scoring; an exception here leaves the intent ambiguous.
        raw=[{'prompt_token_ids':r.prompt_token_ids,'request_id':r.request_id,
              'outputs':[{'index':x.index,'text':x.text,'token_ids':list(x.token_ids),
                          'finish_reason':x.finish_reason,'stop_reason':x.stop_reason} for x in r.outputs]} for r in results]
        durable_json(batch.directory/'backend_return.json',raw)
        if len(results)!=len(ts): raise ProfileError('evaluation request count differs')
        texts=[];ids=[];reasons=[]
        for task,result in zip(ts,results):
            if list(result.prompt_token_ids)!=prompt_ids[task] or len(result.outputs)!=8 or sorted(x.index for x in result.outputs)!=list(range(8)):
                raise ProfileError('evaluation output identity/count differs')
            for x in sorted(result.outputs,key=lambda v:v.index):
                texts.append(x.text);ids.append(list(x.token_ids));reasons.append(x.finish_reason or 'unknown_backend_finish')
        durable_json(batch.directory/'raw_generations.json',{'texts':texts,'completion_ids':ids,'task_id':tasks,'state':state_name})
        score_batch(args,batch,texts,ids,tasks,conn,'union',reasons)
        completed+=len(tasks)
        durable_json(batch.directory/'generation_complete.json',{'samples':len(tasks),'completed_total':completed,'elapsed_seconds':time.monotonic()-started})
    if completed!=spec.EVAL_IDS*spec.EVAL_SAMPLES: raise ProfileError('evaluation incomplete')
    stop_scorer(args,conn,scorer)
    durable_json(out/'evaluation_complete.json',{'state':state_name,'plan_sha256':args.plan_identity,
        'completions':completed,'elapsed_seconds':time.monotonic()-started,'development_only':True})


def parse(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['model-path','model-manifest','data-json','data-sha256','split-json','split-sha256','plan-json','plan-sha256','out']:
        p.add_argument('--'+name,required=True)
    p.add_argument('--source-commit',required=True)
    p.add_argument('--provider-deadline-epoch',type=float,required=True)
    p.add_argument('--execute-screen',action='store_true')
    p.add_argument('--recover-initialization-timeout',action='store_true')
    p.add_argument('--recover-suite-watchdog',action='store_true')
    p.add_argument('--_worker',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--phase',help=argparse.SUPPRESS)
    p.add_argument('--worker-deadline-epoch',type=float,help=argparse.SUPPRESS)
    return p.parse_args(argv)


def main(argv=None):
    args=parse(argv)
    if not args.execute_screen or platform.system()!='Linux': raise ProfileError('explicit Linux screen execution required')
    if not re.fullmatch('[0-9a-f]{40}',args.source_commit): raise ProfileError('published source commit required')
    split=pinned_json(args.split_json,args.split_sha256)
    plan=spec.validate_plan(pinned_json(args.plan_json,args.plan_sha256),split)
    args.plan_identity=identity_hash(plan)
    args.scoring_fast_check=plan.get('scoring_policy')=='first_failure_per_suite'
    if args._worker:
        if os.environ.get('Q2_PROFILE_PARENT_PID')!=str(os.getppid()): raise ProfileError('worker must have owned parent')
        if not args.worker_deadline_epoch or args.worker_deadline_epoch>args.provider_deadline_epoch-600:
            raise ProfileError('worker deadline lacks shutdown reserve')
        try:
            remaining(args)
            if args.phase=='references': reference_worker(args,plan)
            elif args.phase in {p[0] for p in spec.PHASES}: train_worker(args,plan)
            elif args.phase.startswith('eval_'): evaluation_worker(args,plan)
            else: raise ProfileError('unknown phase')
        except BaseException as exc:
            try:
                durable_json(Path(args.out)/args.phase/'worker_failure.json',{'error':repr(exc),'retry':False,'phase':args.phase})
            finally:
                os._exit(1)
        os._exit(0)
    if args.phase or args.worker_deadline_epoch: raise ProfileError('phases/deadlines are parent controlled')
    now=time.time()
    worker_cap=plan['limits']['worker_seconds']
    if not math.isfinite(args.provider_deadline_epoch) or not worker_cap+600<=args.provider_deadline_epoch-now<=spec.POWERED_CAP_SECONDS:
        raise ProfileError('admission needs full shared worker cap and shutdown reserve within four-hour window')
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False);args.out=str(out)
    disk=disk_gate(out,initial=True)
    gpu_pids=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    if gpu_pids: raise ProfileError('GPU already has workers; refusing duplicate/unrelated work')
    args.worker_deadline_epoch=now+worker_cap
    versions=validate_environment(args,plan)
    initial_identity=verify_model(args.model_path,args.model_manifest,time.monotonic()+remaining(args))
    durable_json(out/'screen_intent.json',{'plan':plan,'plan_sha256':args.plan_identity,'source_commit':args.source_commit,
        'initial_model_identity':initial_identity,'versions':versions,
        'execution_module_sha256':{name:sha256(Path(__file__).parent/name) for name in
            ['screen_runtime.py','screen_plan.py','screen_scoring.py','gpu_profile.py','contracts.py']},
        'provider_deadline_epoch':args.provider_deadline_epoch,'worker_deadline_epoch':args.worker_deadline_epoch,
        'started_epoch':now,'disk':disk,'automatic_retry':False})
    command=[sys.executable,'-m','experiments.q2_supervision_migration.screen_runtime',
             *(argv if argv is not None else sys.argv[1:]),'--_worker']
    def interrupted(signum,frame): raise InterruptedError(f'screen parent received {signum}')
    old=signal.signal(signal.SIGTERM,interrupted)
    phases=['references']+[x[0] for x in spec.PHASES]+['eval_'+s for s in spec.EVAL_STATES]
    try:
        for phase in phases:
            remaining(args);disk_gate(out)
            phase_out=out/phase;phase_out.mkdir(exist_ok=False)
            phase_limit=plan['limits']['reference_phase_seconds' if phase=='references' else
                                      'evaluation_phase_seconds' if phase.startswith('eval_') else 'training_phase_seconds']
            phase_end=min(args.worker_deadline_epoch,time.time()+phase_limit)
            phase_command=command+['--worker-deadline-epoch',str(phase_end),'--phase',phase]
            rc=launch_guarded(phase_command,phase_out,phase_end-time.time(),phase='process')
            if rc:
                durable_json(out/'screen_failure.json',{'phase':phase,'retry':False,'remaining_phases_not_run':phases[phases.index(phase)+1:]})
                return 1
        durable_json(out/'screen_complete.json',{'plan_sha256':args.plan_identity,'dose':plan['dose'],
            'finished_epoch':time.time(),'elapsed_seconds':time.time()-now,'exploratory':True,'automatic_continuation':False})
        return 0
    except BaseException as exc:
        durable_json(out/'parent_failure.json',{'error':repr(exc),'retry':False})
        raise
    finally: signal.signal(signal.SIGTERM,old)

if __name__=='__main__': raise SystemExit(main())
