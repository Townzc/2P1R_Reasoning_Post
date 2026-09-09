"""C014 immutable CPU audit. Refuses dirty/unpublished source or existing output."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import signal
import subprocess
import time

import numpy as np
from scripts.audit_family_matching import verified_tokenizer
from src.relation_transport import make_world, views, render_prompt, allocation_schedule
from src.relation_audit import audit_world, audit_schedule
from src.relation_probes import features, fit_probes, predict, probe_statistics, NAMES, VIEW_NAMES

SOURCES = [
    'src/relation_transport.py', 'src/relation_verifier.py', 'src/relation_probes.py',
    'src/relation_audit.py', 'src/sft_data.py', 'scripts/run_relation_cpu_audit.py',
    'scripts/verify_relation_cpu_audit.py', 'scripts/audit_family_matching.py',
    'tests/test_relation_transport.py', 'tests/test_relation_cpu_audit.py',
    'configs/diagnostics/relation_transport_c014.json', 'configs/models.lock.json',
    'docs/experiments/C014_relation_transport_cpu_audit.md',
]


def digest(data): return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def write_archive(path, rows):
    if path.exists(): raise FileExistsError('Immutable archive exists')
    raw = b''.join((json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode() for r in rows)
    zipped = gzip.compress(raw,mtime=0)
    dump(path,{'format':'jsonl+gzip+base64','records':len(rows),'raw_bytes':len(raw),
               'raw_sha256':digest(raw),'compressed_sha256':digest(zipped),
               'data':base64.b64encode(zipped).decode()})
    return {'file':path.name,'records':len(rows),'raw_bytes':len(raw),'compressed_bytes':len(zipped),
            'raw_sha256':digest(raw),'file_sha256':digest(path.read_bytes())}


def provenance(repo):
    git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
    if git('status','--porcelain','--untracked-files=no'):
        raise ValueError('Publish clean tracked source before the audit')
    git('ls-files','--error-unmatch',*SOURCES)
    commit=git('rev-parse','HEAD')
    if commit != git('rev-parse','origin/main'):
        raise ValueError('Source must equal fetched published origin/main')
    return {'source_commit':commit,'source_worktree_dirty':False,
            'source_files_sha256':{p:digest((repo/p).read_bytes()) for p in SOURCES}}


def run(out, tokenizer_dir):
    out=Path(out); repo=Path.cwd()
    if out.exists(): raise FileExistsError('Immutable output exists; use a new registered attempt')
    config=json.loads(Path('configs/diagnostics/relation_transport_c014.json').read_text())
    if out.name!=config['attempt_id']:raise ValueError('Output name must match the registered attempt')
    if list(NAMES)!=config['probe_names'] or list(VIEW_NAMES)!=config['probe_views']:
        raise ValueError('Probe registration differs from implementation')
    source=provenance(repo)
    tokenizer,tokenizer_record=verified_tokenizer(Path(tokenizer_dir))
    started=time.monotonic(); out.mkdir(parents=True,exist_ok=False)
    initial={'phase':'C014','status':'running','started_at_utc':datetime.now(timezone.utc).isoformat(),
             **source,'config':config,'tokenizer':tokenizer_record,'gpu_seconds_added':0,
             'environment':{'python':platform.python_version(),
                            **{p:importlib.metadata.version(p) for p in ('numpy','scipy','transformers','tokenizers')}}}
    dump(out/'initial.json',initial)
    def deadline(*_):raise TimeoutError('Frozen CPU wall deadline reached')
    previous=signal.signal(signal.SIGALRM,deadline);signal.alarm(config['cpu_wall_deadline_seconds'])
    worlds=[]; pending=[]; archives=[]; checks=Counter(); labels=Counter(); failures=[]
    orbits={}; duplicates=[]; position_counts={name:Counter() for name in ('useful_delete','irrelevant_delete')}
    try:
        for seed in range(config['semantic_seed_start'],config['semantic_seed_stop_exclusive']):
            split='probe_fit' if seed<config['fit_seed_stop_exclusive'] else 'probe_audit'
            for index in range(config['instances_per_seed']):
                w=make_world(seed,index,split=split)
                # Retain a triggering world even if its validation raises.
                worlds.append(w);pending.append(w)
                w['audit']=audit_world(w,tokenizer,config['max_serialized_sequence_tokens'],metamorphic=index==0)
                checks.update(w['audit']['checks']);labels[str(w['answer'])]+=1
                failures.extend({'world_id':w['world_id'],'check':f} for f in w['audit']['failures'])
                orbit=w['audit']['orbit']; key=orbit['key']
                if key in orbits:
                    old=orbits[key]
                    if old['canonical_hex']!=orbit['canonical_hex']:raise ValueError('Canonical hash collision')
                    duplicates.append({'first':old['world_id'],'second':w['world_id'],
                                       'cross_split':old['split']!=split})
                else:orbits[key]={**orbit,'world_id':w['world_id'],'split':split}
                for name,positions in w['audit']['deletion_positions'].items():position_counts[name].update(map(str,positions))
                if len(pending)==config['shard_records']:
                    archives.append(write_archive(out/f'records_{len(archives):03d}.json',pending));pending=[]
            print(json.dumps({'stage':'construction','worlds':len(worlds),'failed_checks':len(failures),
                              'elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
        if pending:archives.append(write_archive(out/f'records_{len(archives):03d}.json',pending));pending=[]
        fit=[w for w in worlds if w['split']=='probe_fit'];audit=[w for w in worlds if w['split']=='probe_audit']
        schedule=allocation_schedule([w['world_id'] for w in fit],config['assignment_seed'])
        schedule_report=audit_schedule(fit,schedule)
        dump(out/'schedule.json',schedule);dump(out/'exposure_audit.json',schedule_report)
        print(json.dumps({'stage':'probe_fit','worlds':len(fit),'elapsed_seconds':round(time.monotonic()-started,2)}),flush=True)
        fitted=fit_probes([features(w['prompt']) for w in fit],[w['answer'] for w in fit],config['probe_ridge_alpha'])
        prediction_rows=[{'world_id':w['world_id'],'split':w['split'],'views':{}} for w in audit]
        probe_reports={}
        for name in VIEW_NAMES:
            view=[views(w)[name] for w in audit]
            predictions=predict(fitted,[features(render_prompt(q)) for q,_ in view])
            probe_reports[name]=probe_statistics(predictions,[y for _,y in view],
                                                  config['probe_family_tests'],config['probe_family_alpha'])
            for r,(_,y),pred in zip(prediction_rows,view,predictions):
                r['views'][name]={'answer':y,'predictions':dict(zip(NAMES,map(int,pred)))}
            print(json.dumps({'stage':'probe_audit','view':name,
                              'max_accuracy':max(x['accuracy'] for x in probe_reports[name].values())}),flush=True)
        prediction_archive=write_archive(out/'probe_predictions.json',prediction_rows)
        dump(out/'probes.json',probe_reports)
        leakage_flags=[f'{view}/{name}' for view,rows in probe_reports.items() for name,r in rows.items() if r['flagged']]
        counterfactual={}
        for name in NAMES:
            rows=[r['views'] for r in prediction_rows]
            counterfactual[name]={
                'target_edit_prediction_changed':sum(r['clean']['predictions'][name]!=r['target_change']['predictions'][name] for r in rows),
                'target_edit_both_correct':sum(r['clean']['predictions'][name]==r['clean']['answer'] and
                                                r['target_change']['predictions'][name]==r['target_change']['answer'] for r in rows),
                'n_parents':len(rows)}
        passed=not failures and not duplicates and not schedule_report['failures'] and not leakage_flags
        tokens=Counter(str(w['audit']['tokens'][0]['n_supervised']) for w in worlds)
        summary={**initial,'status':'passed_cpu_gates' if passed else 'failed_cpu_gates',
                 'finished_at_utc':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-started,
                 'worlds':len(worlds),'fit_worlds':len(fit),'audit_worlds':len(audit),'retained_fraction':1.,
                 'label_counts':dict(labels),'checks':dict(checks),'failures':failures,'duplicate_orbits':duplicates,
                 'unique_conservative_world_orbits':len(orbits),'bare_topology_classes':1,
                 'target_token_histogram':dict(tokens),'max_processed_tokens':max(w['audit']['tokens'][0]['n_processed'] for w in worlds),
                 'deletion_position_counts':position_counts,'schedule_failures':schedule_report['failures'],
                 'probe_flags':leakage_flags,'counterfactual_probe_diagnostics':counterfactual,
                 'archives':archives,'probe_prediction_archive':prediction_archive,
                 'limits':['CPU sandbox only; no scientific training pool, model result or holdout evaluation.',
                           'Passing eight probes is not a proof of absent shortcuts; all share one fixed audit population.',
                           'Route symmetry is one algorithm/topology; exposed table/state distributions need not match.',
                           'Canonical grouping conservatively ignores coherent target-potential edits and all source states.']}
        if source['source_files_sha256']!={p:digest((repo/p).read_bytes()) for p in SOURCES}:
            raise RuntimeError('Source changed during audit')
        summary['files_sha256']={p.name:digest(p.read_bytes()) for p in out.iterdir() if p.is_file()}
        dump(out/'summary.json',summary)
        return summary
    except BaseException as exc:
        if pending:archives.append(write_archive(out/f'partial_{len(archives):03d}.json',pending))
        dump(out/'failure.json',{'status':'incomplete_failed_attempt','error_type':type(exc).__name__,
                                'error':str(exc),'worlds_retained':len(worlds),'archives':archives,
                                'wall_seconds':time.monotonic()-started,**source})
        raise
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,previous)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--tokenizer-dir',type=Path,required=True)
    args=p.parse_args();r=run(args.out,args.tokenizer_dir)
    print(json.dumps({k:r[k] for k in ('status','worlds','wall_seconds','probe_flags')}))


if __name__=='__main__':main()
