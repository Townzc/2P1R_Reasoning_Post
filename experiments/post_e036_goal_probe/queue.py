"""One finite diagnostic queue on four previously trained frozen endpoints."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import time

from experiments.thursday_probe.common import stamp
from experiments.thursday_probe.lora import attach,parameter_digest
from experiments.thursday_probe_v2.training import restore_adapter
from experiments.thursday_probe_v2.config import REVISION
from scripts.audit_family_matching import verified_tokenizer
from src.sft_data import sha256_file
from .data import RELEASE, load_rows, load_operator_rows
from .generation import run_batches, _atomic, _read
from .operator_forward import run_operator

ROOT=Path('experiments/post_e036_goal_probe')
OUT=Path(os.environ.get('GOAL_PROBE_OUTPUT','runs/post_e036_goal_probe_v1'))
STATES=('C-S','C-P','B-S','B-P')
BASE_SHA='0fe3fc99f6a3895a6896bf62fdd42853481646a93b45aa167e1084fa116ae142'


def evaluation_queue():
    return [dict(name=f'{s}_{i}_{d}',state=s,interface=i,decoding=d,questions=48,
                 samples=1 if d=='greedy' else 4,sampling=d=='sampled',
                 generations=48 if d=='greedy' else 192)
            for d in ('greedy','sampled') for s in STATES for i in ('F','H','C') if d=='greedy' or i!='C']


def verify_release():
    manifest=_read(RELEASE/'manifest.json')
    for name,sha in manifest['files_sha256'].items():
        if sha256_file(RELEASE/name)!=sha:raise ValueError('Frozen release changed: '+name)
    for interface in 'FHC':
        rows=load_rows(interface)
        if len(rows)!=48 or len({r['problem_id'] for r in rows})!=48:raise ValueError('Release shape changed')
    return sha256_file(RELEASE/'manifest.json')


def dry_run():
    release=verify_release()
    return dict(status='prepared_not_run',planned_generations=2112,generation_cap=2304,
        training_updates=0,operator_contexts=192,candidate_scores=768,
        release_manifest_sha256=release,evaluations=evaluation_queue())


def worker(snapshot,endpoint_root):
    if os.environ.get('GOAL_PROBE_BOUNDED')!='post_e036_goal_probe_v1':raise ValueError('Bounded launcher required')
    from .launcher import GenerationBudget, source
    import torch
    from transformers import AutoModelForCausalLM
    release_hash=verify_release(); expected=_read(ROOT/'endpoint_identities.json')
    paths={s:Path(endpoint_root)/f'thu_v2_e{33+i:03d}_r1/checkpoint_256' for i,s in enumerate(STATES)}
    for state,path in paths.items():
        if _read(path/'checkpoint_identity.json')!=expected[state]:raise ValueError('Frozen endpoint identity changed')
        for name,sha in expected[state]['files_sha256'].items():
            if sha256_file(path/name)!=sha:raise ValueError('Frozen endpoint file changed')
    tokenizer,tok=verified_tokenizer(Path(snapshot));tokenizer.pad_token=tokenizer.eos_token
    torch.manual_seed(2026091703);torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    start=time.monotonic();deadline=float(os.environ['GOAL_PROBE_DEADLINE'])
    src=source(os.environ['GOAL_PROBE_PUBLISHED_COMMIT'])
    if isinstance(src,str):src=dict(source_commit=src)
    progress=dict(**src,status='running',started_at_utc=stamp(),release_manifest_sha256=release_hash,
        historical_generation_attempts=4784,historical_generation_cap=4864,
        historical_phase_ledger_sha256=sha256_file('experiments/thursday_probe_v2/PHASE_LEDGER_resume_r1.json'),
        model=dict(id='Qwen/Qwen2.5-1.5B',revision=REVISION,kind='base',parameters='float32',autocast='bfloat16',attention='sdpa',tf32=False),
        tokenizer=tok,peft=importlib.metadata.version('peft'),seed=2026091703,training_updates=0,
        evaluations=[],operators=[],forward_contexts=0,candidate_scores=0)
    OUT.mkdir(parents=True,exist_ok=True);budget=GenerationBudget(OUT/'generation_ledger.json')
    _atomic(OUT/'run_manifest.json',progress)
    def save():_atomic(OUT/'progress.json',progress)
    def termination(*_):raise TimeoutError('Bounded worker deadline')
    signal.signal(signal.SIGTERM,termination)
    status='failed:not_started';model=None;peak=0
    try:
        base=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.float32,attn_implementation='sdpa',local_files_only=True).cuda()
        model=attach(base);model.eval()
        if any(p.dtype!=torch.float32 for p in model.parameters()):raise ValueError('FP32 required')
        base_hash=parameter_digest(model)
        if base_hash['sha256']!=BASE_SHA:raise ValueError('Base identity changed')
        progress['base_parameter_digest']=base_hash
        current=None;durations=[]
        for event in evaluation_queue():
            state=event['state']
            if current!=state:
                identity=restore_adapter(model,paths[state]);model.eval();current=state
            result=run_batches(model,tokenizer,load_rows(event['interface']),OUT/(event['name']+'.jsonl'),event,
                dict(model_hash=expected[state]['parameter_digest']['sha256'],split_hash=release_hash,
                    batch_time_reserve_seconds=max(120.,max(durations,default=0)*1.5+30),exit_reserve_seconds=30.),
                10000,budget,deadline)
            durations.extend(t['generation_seconds'] for t in result['batch_timings'])
            view=dict(**event,status=result['status'],completed_records=result['completed_records'],
                predictions_sha256=sha256_file(OUT/(event['name']+'.jsonl')),adapter=expected[state]['parameter_digest'],
                release_manifest_sha256=release_hash,reason=result['reason'])
            _atomic(OUT/(event['name']+'.summary.json'),view);progress['evaluations'].append(view);save()
            peak=max(peak,torch.cuda.max_memory_allocated())
            if result['status']!='completed':status='paused_resource';break
            if event['interface']=='C':
                op=run_operator(model,load_operator_rows(),OUT,state,expected[state]['parameter_digest']['sha256'],release_hash,deadline)
                progress['operators'].append({k:v for k,v in op.items() if k!='records'})
                progress['forward_contexts']=sum(x['forward_contexts'] for x in progress['operators'])
                progress['candidate_scores']=sum(x['candidate_scores'] for x in progress['operators'])
                progress['recorded_contexts']=sum(x['recorded_contexts'] for x in progress['operators'])
                progress['unavailable_contexts']=sum(x['unavailable_contexts'] for x in progress['operators'])
                progress['forward_calls']=sum(x['forward_calls'] for x in progress['operators'])
                progress['forward_tokens']=sum(x['input_tokens'] for x in progress['operators'])
                progress['forward_seconds']=sum(x['seconds'] for x in progress['operators']);save()
                peak=max(peak,torch.cuda.max_memory_allocated())
                if op['status']!='completed':status='paused_resource';break
        else:status='completed'
        if parameter_digest(model)!=base_hash:raise ValueError('Frozen base changed')
        if parameter_digest(model,True)!=expected[current]['parameter_digest']:raise ValueError('Frozen adapter changed')
    except TimeoutError as exc:
        status='paused_resource';progress['exception']=str(exc)
    except BaseException as exc:
        status='failed:'+type(exc).__name__;progress['exception']=str(exc);raise
    finally:
        progress.update(status=status,finished_at_utc=stamp(),seconds=time.monotonic()-start,
            generation_attempts=budget.used,peak_memory_allocated_bytes=peak)
        save();_atomic(OUT/'run_manifest_final.json',progress)
    return 0 if status=='completed' else 75 if status=='paused_resource' else 1


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',action='store_true');p.add_argument('--snapshot');p.add_argument('--endpoint-root');a=p.parse_args()
    if a.worker:raise SystemExit(worker(a.snapshot,a.endpoint_root))
    print(json.dumps(dry_run(),indent=2))

if __name__=='__main__':main()
