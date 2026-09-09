"""Fresh CPU C010/C011/C012 outputs; never start or connect to a GPU server."""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime,timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

from scripts.audit_legal_support import load_training_problems, FAMILIES
from scripts.audit_matching_selection import characterize
from scripts.diagnose_family_lengths import diagnose
from src.path_family_matching_complete import complete_supported_key_join,canonical_json_line,record_reference

INVENTORY_SHA='ba890778096197a3f9683cf6d6b4a4675dcc930ff41c5e8ec977ab84611c8ed0'
STREAM_SHA='4302986b7f74c390ed740720715326e3e3db422649031204ab131dae55e0e58e'
CONFIG=Path('configs/diagnostics/matching_completion_v1.json')
SOURCE_NAMES=['scripts/run_matching_completion.py','scripts/diagnose_family_lengths.py',
              'scripts/audit_legal_support.py','scripts/audit_pilot_structure_bias.py','src/countdown_smoke.py',
              'scripts/audit_matching_selection.py','src/path_family_matching_complete.py',
              'src/path_family_matching.py','src/block_packing.py','src/single_family_matching.py',
              'configs/diagnostics/matching_completion_v1.json',
              'docs/experiments/C010_complete_support_join.md','docs/experiments/C011_family_length_diagnostic.md',
              'docs/experiments/C012_identity_absent_boundary_preparation.md',
              'reports/family_matching_20260909_r1/summary.json','reports/family_matching_20260909_r1/per_problem.jsonl']


def sha(data):return hashlib.sha256(data).hexdigest()

def hash_stream(stream):
    digest=hashlib.sha256();size=0
    for chunk in iter(lambda:stream.read(1024*1024),b''):
        digest.update(chunk);size+=len(chunk)
    return {'sha256':digest.hexdigest(),'bytes':size}

def dump(path,data):
    with path.open('x') as out:json.dump(data,out,sort_keys=True,indent=2,allow_nan=False);out.write('\n')


def load_inputs(inventory):
    data=inventory.read_bytes()
    if sha(data)!=INVENTORY_SHA:raise ValueError('C009 tokenized archive changed')
    stream=gzip.decompress(data)
    if sha(stream)!=STREAM_SHA:raise ValueError('C009 tokenized stream changed')
    records=[json.loads(line) for line in stream.splitlines()]
    problems={p['problem_id']:{k:p[k] for k in ('problem_id','numbers','target')} for p in load_training_problems('.')}
    if len(records)!=25846 or {r['problem_id'] for r in records}!=set(problems):raise ValueError('Incomplete original inventory')
    return records,problems


def expand_key(key,lookup):
    result={k:v for k,v in key.items() if k!='witnesses'};result['witnesses']={}
    for pid,w in key['witnesses'].items():
        witness={k:v for k,v in w.items() if k!='slots'};slots=[]
        for slot in w['slots']:
            r=lookup[slot['record_ref']]
            if any(slot[k]!=r[k] for k in ('family','structure_id','ac_class')) or r['problem_id']!=pid:
                raise ValueError('Witness reference mismatch')
            expected=w.get('n_supervised',w.get('family_lengths',{}).get(r['family']))
            if r['n_supervised']!=expected:raise ValueError('Witness token length mismatch')
            slots.append({**{k:v for k,v in slot.items() if k!='record_ref'},'record':r})
        witness['slots']=slots;result['witnesses'][pid]=witness
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['common','lengths','absent'],required=True)
    parser.add_argument('--inventory',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--private-out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists() or args.private_out.exists():raise FileExistsError('Fresh immutable output directories required')
    config=json.loads(CONFIG.read_text())
    if config!={'schema_version':1,'common_join_seconds':600,'packing_seconds':60,'single_family_seconds':120,
               'training_family':'identity_absent','training_seed':31,'selection_seed':31,'block_tiers':[32,16],
               'training_updates':1024,'per_job_seconds':1050,'ledger_used_seconds':4716}:
        raise ValueError('Unknown frozen diagnostic configuration')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','status','--porcelain','--',*SOURCE_NAMES],text=True).strip():raise ValueError('Publish sources before actual diagnostics')
    source_hashes={n:sha(Path(n).read_bytes()) for n in SOURCE_NAMES}
    args.out.mkdir(parents=True);args.private_out.mkdir(parents=True)
    started=time.monotonic();records,problems=load_inputs(args.inventory)
    lookup={record_reference(r):r for r in records if r['encodable']}
    old=[json.loads(l) for l in Path('reports/family_matching_20260909_r1/per_problem.jsonl').read_text().splitlines()]
    old_summary=json.loads(Path('reports/family_matching_20260909_r1/summary.json').read_text())
    if sha(Path('reports/family_matching_20260909_r1/per_problem.jsonl').read_bytes())!=old_summary['output_sha256']['per_problem.jsonl']:
        raise ValueError('C009 completed per-question stages changed')
    summary={'diagnostic_id':{'common':'C010','lengths':'C011','absent':'C012'}[args.phase],
             'source_commit':commit,'source_sha256':source_hashes,'config':config,
             'inventory_compressed_sha256':INVENTORY_SHA,'inventory_stream_sha256':STREAM_SHA,
             'gpu_seconds_added':0,'environment':{p:importlib.metadata.version(p) for p in ('numpy','scipy','networkx')},
             'server_connected':False,'model_or_development_outputs_read':False}
    if args.phase=='lengths':
        result=diagnose(records,problems)
        if result['counts']['common_class']!=67 or result['counts']['common_structure']!=66:
            raise ValueError('Independent common-length stages disagree with C009')
        dump(args.out/'length_diagnostic.json',result)
        # These two branches are nested internally, but neither branch is called the other's predecessor.
        reports={}
        for mode in ('common','per_family'):
            reports[mode]=characterize(problems,{mode+'_class':result['stage_ids'][mode+'_class'],mode+'_structure':result['stage_ids'][mode+'_structure']})
        dump(args.out/'selection.json',reports)
        summary.update(status='complete',counts=result['counts'])
    else:
        from src.block_packing import pack_support_groups
        if args.phase=='common':
            lengths={p['problem_id']:p['structure_lengths'] for p in old}
            eligible=[r for r in records if r['encodable'] and r['n_supervised'] in lengths[r['problem_id']]]
            if len(eligible)!=5774 or len({r['problem_id'] for r in eligible})!=66:
                raise ValueError('C010 necessary common-length filter changed')
            archive=args.private_out/'valid_keys.jsonl.gz'
            with gzip.GzipFile(filename=str(archive),mode='xb',mtime=0) as writer:
                result=complete_supported_key_join(eligible,max_seconds=config['common_join_seconds'],length_mode='common',on_key=lambda key:writer.write(canonical_json_line(key)))
            if result['complete'] and result['total_candidate_pairs']!=48429084:raise ValueError('C010 finite grid changed')
            with gzip.open(archive,'rb') as inp:stream_receipt=hash_stream(inp)
            with archive.open('rb') as inp:archive_receipt=hash_stream(inp)
            if stream_receipt['sha256']!=result['key_stream_sha256']:raise ValueError('Key stream mismatch')
            summary['private_key_archive']=archive_receipt
            summary['private_key_stream']=stream_receipt
            groups=[{'problem_ids':g['problem_ids'],'representative':g['representative_key']} for g in result['support_groups']]
            stages={name:sorted(r['problem_id'] for r in old if r[name]) for name in ('raw_disjoint','token_matched','structure_matched')}
        else:
            from src.single_family_matching import single_family_keys
            eligible=[r for r in records if r['encodable'] and r['family']==config['training_family']]
            result=single_family_keys(eligible,family=config['training_family'],max_seconds=config['single_family_seconds'])
            # Store references to the fixed archive instead of repeating full traces.
            for key in result['keys']:
                for witness in key['witnesses'].values():
                    for slot in witness['slots']:
                        slot['record_ref']=record_reference(slot.pop('record'))
            unique={}
            for key in result['keys']:
                support=tuple(key['problem_ids'])
                if support not in unique or key['structures']<unique[support]['structures']:
                    unique[support]=key
            groups=[{'problem_ids':list(s),'representative':key} for s,key in sorted(unique.items())]
            stages={'individual_family_feasible':sorted(result['per_problem_feasible_lengths'])}
        dump(args.out/'join.json',result)
        packing=pack_support_groups(groups,time_limit=config['packing_seconds'])
        packing.update(block_count=packing['primal_block_count'],selected_problem_ids=packing['used_problem_ids'],
                       optimal=packing['is_optimal'],block_upper_bound=packing['integer_upper_bound'])
        packing['input_join_complete']=result['complete']
        packing['global_optimal']=bool(result['complete'] and packing['optimal'])
        packing['optimality_scope']='complete_key_universe' if result['complete'] else 'discovered_groups_only'
        for block in packing['blocks']:
            representative=block['representative']
            selected=set(block['problem_ids'])
            representative=dict(representative,problem_ids=block['problem_ids'],
                                witnesses={p:w for p,w in representative['witnesses'].items() if p in selected})
            block['representative']=expand_key(representative,lookup)
        dump(args.out/'packing.json',packing)
        stages['shared_key_supported']=result['supported_problem_ids']
        stages['packed']=packing['selected_problem_ids']
        dump(args.out/'selection.json',characterize(problems,stages))
        summary.update(status='complete' if result['complete'] else 'incomplete_join',join_complete=result['complete'],
                       supported_problem_count=len(result['supported_problem_ids']),packing_block_count=packing['block_count'],
                       packing_proved_optimal=packing['global_optimal'],packing_upper_bound=packing['block_upper_bound'],
                       packing_upper_bound_scope=packing['optimality_scope'])
    if source_hashes!={n:sha(Path(n).read_bytes()) for n in SOURCE_NAMES}:raise ValueError('Source changed during run')
    summary.update(runtime_seconds=time.monotonic()-started,completed_at_utc=datetime.now(timezone.utc).isoformat(),
                   output_sha256={p.name:sha(p.read_bytes()) for p in args.out.iterdir() if p.is_file()})
    dump(args.out/'summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('source_sha256','config','output_sha256')},sort_keys=True),flush=True)

if __name__=='__main__':main()
