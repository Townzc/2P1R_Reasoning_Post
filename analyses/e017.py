"""Prepare/inspect E017 locally; explicit bounded launch on an owner-started A800."""
import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import time

from analyses import e016
from analyses.e014 import check_generation_settings, effective_generation_config
from analyses.e017_stopping import generate
from analyses.e017_audit import audit_predictions, decisions
from scripts.audit_family_matching import verified_tokenizer
from scripts.run_relation_engineering import check_ledger, server_preflight
from src.real_math_engineering import dump, git, write_rows
from src.sft_data import read_jsonl, sha256_file

CONFIG = Path('configs/real_math_e017/stopping.json')
RELEASE = Path('configs/real_math_e017/release.json')
INPUTS = Path('reports/real_math_e017_inputs_r1')


def dependencies():
    return sorted(set(e016.dependencies() + [str(CONFIG), 'analyses/completion_contract.py',
        'analyses/e017.py', 'analyses/e017_stopping.py', 'analyses/e017_audit.py',
        'analyses/verify_e017_inputs.py', 'tests/test_e017.py', 'tests/test_completion_contract.py']))


def provenance():
    if git('status','--porcelain','--untracked-files=no') or git('rev-parse','HEAD') != git('rev-parse','origin/main'):
        raise ValueError('Publish a clean source checkout before preparation or execution')
    git('ls-files','--error-unmatch',*dependencies())
    return {'source_commit':git('rev-parse','HEAD'), 'source_files_sha256':{p:sha256_file(p) for p in dependencies()}}


def library_sources():
    from transformers.generation.stopping_criteria import StoppingCriteriaList
    from transformers import GenerationConfig
    return {**e016.library_sources(), **{c.__module__:sha256_file(inspect.getfile(c))
            for c in (StoppingCriteriaList,GenerationConfig)}}


def prepare(tokenizer):
    if INPUTS.exists() or RELEASE.exists():
        raise FileExistsError('Immutable input release exists')
    source = provenance()
    _, rows = e016.load_release(tokenizer)
    cases = e016.validate_rows(rows,tokenizer)
    cfg = json.loads(CONFIG.read_text())
    evidence = {'phase':'E017_CPU_INPUTS', 'parents':64,'already_observed_development_parents':64,
        'development_ranks':[17,80], 'remaining_development_reserve':432,
        'new_pretrained_model_calls':0,'server_contacted':False,'optimizer_updates':0,
        'planned_generations':64,'maximum_generated_tokens':64*768,
        'prompt_tokens':sum(len(c['prompt_ids']) for c in cases),
        'left_padded_prompt_tokens':8*sum(max(len(c['prompt_ids']) for c in cases[i:i+8]) for i in range(0,64,8)),
        'maximum_prompt_tokens':max(len(c['prompt_ids']) for c in cases),
        'parent_e016_release_sha256':sha256_file(e016.RELEASE), 'official_test_read':False}
    INPUTS.mkdir()
    # Copy the complete observed input bytes; no new source-data selection.
    (INPUTS/'rows.jsonl').write_bytes((e016.INPUTS/'rows.jsonl').read_bytes())
    dump(INPUTS/'cases.json',cases)
    dump(INPUTS/'cpu_evidence.json',evidence)
    dump(INPUTS/'manifest.json',{**source,'phase':'E017_INPUTS','config_sha256':sha256_file(CONFIG),
        'parent_e016_release_sha256':sha256_file(e016.RELEASE),'library_sources_sha256':library_sources(),
        'files_sha256':{name:sha256_file(INPUTS/name) for name in ('rows.jsonl','cases.json','cpu_evidence.json')}})
    dump(RELEASE,{'phase':'E017_RELEASE','manifest_sha256':sha256_file(INPUTS/'manifest.json')})
    return evidence


def load_release(tokenizer):
    release=json.loads(RELEASE.read_text())
    if release['phase']!='E017_RELEASE' or sha256_file(INPUTS/'manifest.json')!=release['manifest_sha256']:
        raise ValueError('E017 release changed')
    manifest=json.loads((INPUTS/'manifest.json').read_text())
    if manifest['config_sha256']!=sha256_file(CONFIG) or set(manifest['source_files_sha256'])!=set(dependencies()):
        raise ValueError('Config or runtime dependency set changed')
    for p,h in manifest['source_files_sha256'].items():
        historical=subprocess.check_output(['git','show',manifest['source_commit']+':'+p])
        if sha256_file(p)!=h or hashlib.sha256(historical).hexdigest()!=h:
            raise ValueError('Frozen runtime source changed: '+p)
    if manifest['library_sources_sha256']!=library_sources():
        raise ValueError('Pinned installed generation/model source changed')
    if set(manifest['files_sha256'])!={'rows.jsonl','cases.json','cpu_evidence.json'}:
        raise ValueError('Input inventory differs')
    for name,h in manifest['files_sha256'].items():
        if sha256_file(INPUTS/name)!=h:
            raise ValueError('Input bytes changed')
    _,original=e016.load_release(tokenizer)
    rows=read_jsonl(INPUTS/'rows.jsonl')
    if (manifest['parent_e016_release_sha256']!=sha256_file(e016.RELEASE) or rows!=original
            or (INPUTS/'rows.jsonl').read_bytes()!=(e016.INPUTS/'rows.jsonl').read_bytes()
            or e016.validate_rows(rows,tokenizer)!=json.loads((INPUTS/'cases.json').read_text())):
        raise ValueError('Observed parents or prompt token streams changed')
    git('ls-files','--error-unmatch',str(RELEASE),*[str(INPUTS/n) for n in (*manifest['files_sha256'],'manifest.json')])
    return json.loads(CONFIG.read_text()),rows


def rental_window(start,now=None):
    start=datetime.fromisoformat(start.replace('Z','+00:00'))
    if start.tzinfo is None:
        raise ValueError('Timezone-aware power-on time required')
    age=((now or datetime.now(timezone.utc))-start).total_seconds()
    if not math.isfinite(age) or not 0<=age<=345:
        raise ValueError('Insufficient whole-rental time; stop without model launch')
    return {'power_on_at_utc':start.isoformat(),'elapsed_seconds':age,'whole_window_cap_seconds':900,
        'remaining_seconds':900-age,'required_at_admission_seconds':555,
        'gpu_rate_cny_per_hour':8,'planned_rental_ceiling_cny':2}


def worker(args,tokenizer):
    cfg,rows=load_release(tokenizer);out=Path('runs')/cfg['run_id']
    if os.environ.get('CS294_BOUNDED_RUN_ID')!=cfg['run_id'] or not out.is_dir() or (out/'run_manifest.json').exists():
        raise ValueError('Mandatory unique bounded wrapper required')
    source=provenance();preflight=json.loads(Path(args.preflight).read_text())
    if (preflight['phase']!='E017' or preflight['source_commit']!=source['source_commit']
            or preflight['release_sha256']!=sha256_file(RELEASE)
            or preflight['accounting']['ledger_sha256']!=cfg['expected_ledger_sha256']
            or not preflight['server']['model']['all_files_verified']
            or preflight['snapshot_path']!=str(Path(args.tokenizer_dir).resolve())):
        raise ValueError('Matching source/base/ledger preflight required')
    rental_window(preflight['rental']['power_on_at_utc'])
    import torch
    from transformers import AutoModelForCausalLM
    torch.manual_seed(17);random.seed(17);torch.set_num_threads(8)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    tokenizer.pad_token=tokenizer.eos_token
    manifest={**source,'phase':'E017','status':'running','config':cfg,
        'release_sha256':sha256_file(RELEASE),'preflight_sha256':sha256_file(args.preflight),
        'server':preflight['server'],'tokenizer':preflight['tokenizer'],
        'started_at_utc':datetime.now(timezone.utc).isoformat(),'optimizer_updates':0,'checkpoint_write':False,
        'parameter_dtype':'float32','autocast_dtype':'bfloat16','attention':'sdpa','tf32':False,
        'official_test_evaluation':False,'row_compaction':False,'boundary_is_native_eos':False}
    dump(out/'run_manifest.json',manifest)
    phases={};start=time.monotonic()
    def stop(*_):raise TimeoutError('E017 finite watchdog; no retry')
    signal.signal(signal.SIGTERM,stop)
    try:
        tick=time.monotonic()
        model=AutoModelForCausalLM.from_pretrained(args.tokenizer_dir,dtype=torch.float32,
                  attn_implementation='sdpa',local_files_only=True).cuda()
        if any(p.dtype!=torch.float32 for p in model.parameters()):
            raise ValueError('Parameter dtype differs')
        model.requires_grad_(False);torch.cuda.synchronize();phases['base_load']=time.monotonic()-tick
        settings=effective_generation_config(model.generation_config,tokenizer,cfg)
        check_generation_settings(settings,cfg);dump(out/'base_generation_config.json',settings)
        torch.cuda.reset_peak_memory_stats();tick=time.monotonic()
        predictions=generate(model,tokenizer,rows,cfg,out/'base.jsonl')
        phases['base_generation']=time.monotonic()-tick
        # Independent prefix oracle validates the actual streams inside the cap.
        tick=time.monotonic();checked=audit_predictions(out/'base.jsonl',rows,tokenizer,cfg)
        if checked!=predictions:raise ValueError('Serialized records differ')
        phases['raw_record_audit']=time.monotonic()-tick
        metrics=decisions(checked,cfg);dump(out/'metrics.json',metrics)
        dump(out/'base_profile.json',{'n':64,'generation_seconds':phases['base_generation'],
            'output_tokens':metrics['retained_generated_tokens'],'padded_output_tokens':metrics['padded_batch_output_tokens'],
            'peak_allocated_mib':torch.cuda.max_memory_allocated()/1024**2,
            'peak_reserved_mib':torch.cuda.max_memory_reserved()/1024**2})
        manifest['status']='completed'
    except BaseException as exc:
        manifest.update(status='failed',exception_type=type(exc).__name__);raise
    finally:
        dump(out/'phase_timings.json',{'completed_phases_seconds':phases,'wall_seconds':time.monotonic()-start})
        manifest['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        dump(out/'run_manifest.tmp',manifest);(out/'run_manifest.tmp').replace(out/'run_manifest.json')


def audit_run(tokenizer,run,out):
    cfg,rows=load_release(tokenizer)
    m=json.loads((run/'run_manifest.json').read_text())
    if m['status']!='completed' or m['config']!=cfg or m['release_sha256']!=sha256_file(RELEASE):
        raise ValueError('Incomplete or changed run; preserve failures')
    expected={'phase':'E017','optimizer_updates':0,'checkpoint_write':False,
              'parameter_dtype':'float32','autocast_dtype':'bfloat16','attention':'sdpa','tf32':False,
              'official_test_evaluation':False,'row_compaction':False,'boundary_is_native_eos':False}
    if any(m.get(k)!=v for k,v in expected.items()):
        raise ValueError('Execution manifest contract differs')
    inputs=json.loads((INPUTS/'manifest.json').read_text())
    if m['source_files_sha256']!=inputs['source_files_sha256']:
        raise ValueError('Run source inventory differs')
    for p,h in m['source_files_sha256'].items():
        if hashlib.sha256(subprocess.check_output(['git','show',m['source_commit']+':'+p])).hexdigest()!=h:
            raise ValueError('Execution commit differs')
    predictions=audit_predictions(run/'base.jsonl',rows,tokenizer,cfg)
    metrics=decisions(predictions,cfg)
    if metrics!=json.loads((run/'metrics.json').read_text()):raise ValueError('Metrics or gate differs')
    check_generation_settings(json.loads((run/'base_generation_config.json').read_text()),cfg)
    profile=json.loads((run/'base_profile.json').read_text())
    timings=json.loads((run/'phase_timings.json').read_text())['completed_phases_seconds']
    if (profile['n']!=64 or profile['output_tokens']!=metrics['retained_generated_tokens']
            or profile['padded_output_tokens']!=metrics['padded_batch_output_tokens']
            or profile['generation_seconds']!=timings['base_generation']):
        raise ValueError('Profile counts/time differ')
    for k in ('generation_seconds','peak_allocated_mib','peak_reserved_mib'):
        if type(profile[k]) not in (int,float) or not math.isfinite(profile[k]) or profile[k]<=0:
            raise ValueError('Invalid measured profile')
    receipt=json.loads((run/'resource_receipt.json').read_text())
    if (receipt['run_id']!=cfg['run_id'] or receipt['status']!='completed' or receipt['exit_code']!=0
            or type(receipt['charged_seconds']) is not int or not 0<receipt['charged_seconds']<=255):
        raise ValueError('Resource receipt differs')
    result={'status':'passed_independent_raw_prefix_checks','raw_streams_checked':64,
            'new_pretrained_model_calls':0,'logits_recomputed':False,'proofs_verified':False,
            'result':metrics,'resource_receipt_sha256':sha256_file(run/'resource_receipt.json')}
    dump(out,result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',nargs='?',default='inspect',choices=('prepare','inspect','launch','worker','audit'))
    p.add_argument('--tokenizer-dir',required=True,type=Path)
    p.add_argument('--ledger',default='.local/resource_ledger.json')
    p.add_argument('--preflight');p.add_argument('--out',type=Path)
    p.add_argument('--power-on-at-utc');p.add_argument('--power-on-time-source',choices=('provider_timestamp','owner_start_notification'))
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    tokenizer,token_record=verified_tokenizer(a.tokenizer_dir)
    if a.action=='prepare':print(json.dumps(prepare(tokenizer),indent=2));return 0
    if a.action=='worker':worker(a,tokenizer);return 0
    cfg,_=load_release(tokenizer)
    if a.action=='audit':print(json.dumps(audit_run(tokenizer,Path('runs')/cfg['run_id'],a.out),indent=2));return 0
    source=provenance();resource=json.loads(Path('configs/resource_budget.json').read_text())
    accounting=check_ledger(cfg,a.ledger,resource)
    report={'phase':'E017','source_commit':source['source_commit'],'status':'not_run','accounting':accounting,
        'release_sha256':sha256_file(RELEASE),'tokenizer':token_record,'generations':64,'optimizer_updates':0,'new_pretrained_model_calls':0}
    if a.action=='inspect' or not a.execute:print(json.dumps(report,indent=2));return 0
    if not a.power_on_at_utc or not a.power_on_time_source:raise ValueError('Explicit power-on time/evidence required')
    report['rental']=rental_window(a.power_on_at_utc);report['rental']['time_source']=a.power_on_time_source
    report['server']=server_preflight(cfg,a.tokenizer_dir)
    if report['server']['gpu'].split(',')[2].strip()!=cfg['driver_version']:raise ValueError('Pinned driver differs')
    report['snapshot_path']=str(a.tokenizer_dir.resolve());report['rental'].update(rental_window(a.power_on_at_utc))
    preflight=Path('.local')/('e017_preflight_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')
    dump(preflight,report);check_ledger(cfg,a.ledger,resource)
    return subprocess.call([sys.executable,'-m','scripts.run_bounded','--run-id',cfg['run_id'],
        '--max-seconds',str(cfg['max_seconds']),'--ledger',a.ledger,'--expected-ledger-sha256',cfg['expected_ledger_sha256'],
        '--require-full-cap','--',sys.executable,'-m','analyses.e017','worker','--tokenizer-dir',str(a.tokenizer_dir),'--preflight',str(preflight)])


if __name__=='__main__':sys.exit(main())
