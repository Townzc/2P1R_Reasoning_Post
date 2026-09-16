"""Finite, source-published E018 LoRA calibration. Never launches descendants."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from experiments.thursday_probe.common import ROOT, ALIASES, dump, stamp, verify_manifest
from experiments.thursday_probe.e018_prepare import OUT as INPUTS, PROPOSAL
from experiments.thursday_probe.lora import attach, parameter_digest, save_adapter, train
from analyses.e017_stopping import generate
from analyses.e017_audit import audit_predictions, decisions
from scripts.audit_family_matching import verified_tokenizer
from scripts.run_relation_engineering import server_preflight
from src.relation_experiment import reference_nll
from src.sft_data import read_jsonl, encode_row, sha256_file

LEDGER_HASH='48541b40ec441c1c5d5870d7c198c00a5e567ef7bc3804e03ccc1d61a63fda8e'
RUN=Path('runs')/ALIASES['E018']


def source():
    def git(*a): return subprocess.check_output(['git',*a],text=True).strip()
    head=git('rev-parse','HEAD')
    if git('status','--porcelain','--untracked-files=no') or head != git('rev-parse','origin/codex/iclr-2027-sprint'):
        raise ValueError('Publish clean assigned branch before running')
    files=[str(p) for d in ('src','analyses','scripts','experiments/thursday_probe') for p in Path(d).glob('*.py')]
    return {'source_commit':head,'source_files_sha256':{p:sha256_file(p) for p in files}}


def worker(snapshot):
    if os.environ.get('THU_BOUNDED_RUN') != ALIASES['E018']:
        raise ValueError('Bounded parent launcher required')
    import torch
    from transformers import AutoModelForCausalLM
    from peft import PeftModel
    cfg=json.loads(PROPOSAL.read_text()); gen=json.loads(Path('configs/real_math_e017/stopping.json').read_text())
    inputs=verify_manifest(INPUTS)
    quality=json.loads((ROOT/'E018_QUALITY_REVIEW.json').read_text())
    if quality['decision'] != 'retain_original_253_for_engineering_only' or quality['sample_sha256'] != sha256_file(INPUTS/'quality_32.jsonl'):
        raise ValueError('Documented quality disposition required')
    tokenizer,tok=verified_tokenizer(Path(snapshot)); tokenizer.pad_token=tokenizer.eos_token
    rows=read_jsonl(INPUTS/'train.jsonl'); dev=read_jsonl(INPUTS/'dev.jsonl')
    encoded=[encode_row(r,tokenizer,1024) for r in rows]
    schedule=json.loads((INPUTS/'schedule.json').read_text()); lrs=json.loads((INPUTS/'learning_rates.json').read_text())
    torch.manual_seed(17); torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False
    m={**source(),'phase':'E018','status':'running','started_at_utc':stamp(),'model':cfg['model'],
       'adapter':cfg['training']['lora'],'peft':importlib.metadata.version('peft'),
       'input_manifest_sha256':sha256_file(INPUTS/'manifest.json'),'quality_review_sha256':sha256_file(ROOT/'E018_QUALITY_REVIEW.json'),
       'tokenizer':tok,'seed':17,'optimizer_reset':True,'generation_cap':160,
       'reserved_access':False,'old_ledger_sha256':LEDGER_HASH}
    dump(RUN/'run_manifest.json',m)
    start=time.monotonic(); phases={}
    def stop(*_): raise TimeoutError('Finite E018 process cap reached')
    signal.signal(signal.SIGTERM,stop)
    try:
        tick=time.monotonic()
        base=AutoModelForCausalLM.from_pretrained(snapshot,dtype=torch.float32,attn_implementation='sdpa',local_files_only=True).cuda()
        model=attach(base)
        if any(p.dtype != torch.float32 for p in model.parameters()): raise ValueError('FP32 parameters required')
        initial_base=parameter_digest(model); initial_adapter=parameter_digest(model,True)
        if initial_adapter['parameters'] != 18464768: raise ValueError('Adapter size differs')
        phases['load_and_identity']=time.monotonic()-tick
        torch.cuda.reset_peak_memory_stats(); tick=time.monotonic()
        b=generate(model,tokenizer,dev,gen,RUN/'base.jsonl')
        audit_predictions(RUN/'base.jsonl',dev,tokenizer,gen)
        base_gate=decisions(b,gen); dump(RUN/'base_usability.json',base_gate)
        phases['base_generation']=time.monotonic()-tick
        tick=time.monotonic(); before=reference_nll(model,encoded,tokenizer,1)
        dump(RUN/'base_reference_nll.json',before); phases['base_nll']=time.monotonic()-tick
        if not base_gate['operational_usability_passed']: raise ValueError('Base usability failed; stop before training')
        tick=time.monotonic(); history,_=train(model,encoded,schedule,lrs,tokenizer,RUN)
        phases['training']=time.monotonic()-tick
        tick=time.monotonic(); after=reference_nll(model,encoded,tokenizer,1)
        dump(RUN/'final_reference_nll.json',after); phases['final_nll']=time.monotonic()-tick
        tick=time.monotonic(); checkpoint=save_adapter(model,RUN/'checkpoint_final')
        end_base=parameter_digest(model); end_adapter=parameter_digest(model,True)
        if end_base != initial_base: raise ValueError('Frozen base changed')
        # Verify a separately loaded CPU adapter state against the saved tensor map.
        from safetensors.torch import load_file
        from peft import get_peft_model_state_dict
        saved=load_file(str(RUN/'checkpoint_final/adapter_model.safetensors'))
        current=get_peft_model_state_dict(model)
        if set(saved) != set(current) or any(not torch.equal(saved[k],current[k].cpu()) for k in saved):
            raise ValueError('Serialized adapter differs from trained parameters')
        phases['save_and_identity']=time.monotonic()-tick
        tick=time.monotonic(); f=generate(model,tokenizer,dev,gen,RUN/'final.jsonl')
        audit_predictions(RUN/'final.jsonl',dev,tokenizer,gen)
        final_gate=decisions(f,gen)
        train_ids=cfg['training']['final_train_decode_sample']['problem_ids']
        train_rows=[next(r for r in rows if r['problem_id']==pid) for pid in train_ids]
        tr=generate(model,tokenizer,train_rows,gen,RUN/'final_train.jsonl')
        audit_predictions(RUN/'final_train.jsonl',train_rows,tokenizer,gen)
        phases['final_generation']=time.monotonic()-tick
        bc=[r['task_score']['task_answer_correct'] for r in b]; fc=[r['task_score']['task_answer_correct'] for r in f]
        both=sum(x and y for x,y in zip(bc,fc)); lost=sum(x and not y for x,y in zip(bc,fc)); gained=sum(y and not x for x,y in zip(bc,fc))
        reduction=1-after['nll']/before['nll']
        checks={'base_usability':base_gate['operational_usability_passed'],'final_usability':final_gate['operational_usability_passed'],
                'retention':10*both >= 9*sum(bc),'net_loss':sum(bc)-sum(fc)<=4,
                'nll_reduction':reduction>=.1,'base_unchanged':end_base==initial_base,
                'adapter_changed':end_adapter!=initial_adapter,'complete_dose':len(history)==64 and sum(r['supervised_tokens'] for r in history)==77192}
        metrics={'base':base_gate,'final':final_gate,'both_correct':both,'lost':lost,'gained':gained,
                 'both_wrong':64-both-lost-gained,'reference_nll_reduction_fraction':reduction,
                 'initial_base':initial_base,'final_base':end_base,'initial_adapter':initial_adapter,'final_adapter':end_adapter,
                 'checkpoint':checkpoint,'training_decode_correct':sum(r['task_score']['task_answer_correct'] for r in tr),
                 'checks':checks,'passed':all(checks.values()),'free_generations':len(b)+len(f)+len(tr),
                 'training_label_defects_known':quality['material_errors'],'scientific_effect_claim':False}
        dump(RUN/'metrics.json',metrics); m['status']='completed'
        print(json.dumps({'E018_passed':metrics['passed'],'base_correct':sum(bc),'final_correct':sum(fc),'both_correct':both,'lost':lost,'gained':gained,'nll_reduction':reduction}),flush=True)
    except BaseException as exc:
        m.update(status='failed',exception_type=type(exc).__name__,exception_message=str(exc)); raise
    finally:
        dump(RUN/'phase_timings.json',{'phases_seconds':phases,'process_wall_seconds':time.monotonic()-start,
             'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_reserved_bytes':torch.cuda.max_memory_reserved()})
        m['finished_at_utc']=stamp(); dump(RUN/'run_manifest_final.json',m)


def launch(snapshot, ledger, power_on):
    from datetime import datetime,timezone
    source(); verify_manifest(INPUTS)
    if sha256_file(ledger) != LEDGER_HASH: raise ValueError('Historical ledger changed; reconcile first')
    if RUN.exists(): raise FileExistsError('No E018 retry or overwrite')
    now=datetime.now(timezone.utc); started=datetime.fromisoformat(power_on.replace('Z','+00:00'))
    age=(now-started).total_seconds()
    if not 0<=age<=2700-1215: raise ValueError('Insufficient 45-minute setup/calibration window; do not load model')
    server=server_preflight({'min_free_gib':1},Path(snapshot))
    RUN.mkdir()
    dump(RUN/'preflight.json',{'server':server,'power_on_at_utc':power_on,'age_seconds':age,
        'process_cap_seconds':900,'guard_seconds':15,'old_ledger_sha256':LEDGER_HASH,
        'phase_allowance_seconds':915,'rate_cny_per_hour':7.98,'whole_window_cap_seconds':2700,
        'whole_window_cost_bound_cny':5.985,'old_ledger_will_not_be_mutated':True,
        'window_note':'Owner started before preparation completed; setup included; model process unchanged at900 seconds.'})
    tick=time.monotonic(); command=['timeout','--signal=TERM','--kill-after=15s','900s',sys.executable,'-m','experiments.thursday_probe.e018','worker','--snapshot',snapshot]
    with (RUN/'stdout.log').open('x') as f:
        code=subprocess.call(command,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'THU_BOUNDED_RUN':ALIASES['E018'],'TOKENIZERS_PARALLELISM':'false'})
    elapsed=time.monotonic()-tick
    receipt={'run_id':ALIASES['E018'],'exit_code':code,'wall_seconds':elapsed,'charged_seconds':math.ceil(elapsed),
             'process_cap_seconds':900,'guard_seconds':15,'started_at_utc':now.isoformat(),'finished_at_utc':stamp(),
             'old_ledger_sha256':LEDGER_HASH,'new_phase_allowance_seconds':915,'old_ledger_unchanged':sha256_file(ledger)==LEDGER_HASH,
             'status':'completed' if code==0 else 'failed','command':command[:-1]+['PINNED_MODEL_SNAPSHOT']}
    dump(RUN/'resource_receipt.json',receipt)
    print(json.dumps(receipt,indent=2)); return code


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['launch','worker']); p.add_argument('--snapshot',required=True)
    p.add_argument('--ledger'); p.add_argument('--power-on-at-utc'); a=p.parse_args()
    if a.action=='worker': worker(a.snapshot)
    else: sys.exit(launch(a.snapshot,a.ledger,a.power_on_at_utc))
