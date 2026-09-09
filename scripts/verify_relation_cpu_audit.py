"""Read-only C014 archive verification, independent of hidden-state generation."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time

from scipy.stats import binomtest
from scripts.audit_family_matching import verified_tokenizer
from src.relation_verifier import parse_prompt, solve, simple_paths, check_certificate, orbit_key
from src.sft_data import encode_row, prefix


def sha(data):return hashlib.sha256(data).hexdigest()


def load_archive(path):
    obj=json.loads(Path(path).read_text())
    if obj['format']!='jsonl+gzip+base64':raise ValueError('Unknown archive encoding')
    zipped=base64.b64decode(obj['data'],validate=True)
    if sha(zipped)!=obj['compressed_sha256']:raise ValueError('Compressed archive hash mismatch')
    raw=gzip.decompress(zipped)
    if sha(raw)!=obj['raw_sha256'] or len(raw)!=obj['raw_bytes']:raise ValueError('Raw archive mismatch')
    rows=[json.loads(line) for line in raw.splitlines()]
    if len(rows)!=obj['records']:raise ValueError('Record count mismatch')
    return rows


def render_from_existing_header(original,q):
    header=original.split('\nEdges:\n')[0]+'\nEdges:\n'
    lines=[f"E {e['id']} : N {e['u']} > N {e['v']} : "+' '.join(str(x) for x in e['table']) for e in q['edges']]
    return header+'\n'.join(lines)+f"\nQuery : N {q['source']} = {q['state']} > N {q['target']}\n"


def check_record(w,tokenizer,max_length,recheck_orbit=True):
    if len(w['responses'])!=4 or len(w['audit']['tokens'])!=4:
        raise ValueError('Exactly four reference/token receipts required')
    q=parse_prompt(w['prompt'])
    if solve(q)!=[w['answer']]:raise ValueError('Base answer mismatch')
    paths=simple_paths(q)
    if len(paths)!=4 or {len(p) for p in paths}!={4}:raise ValueError('Support mismatch')
    if {tuple(e['id'] for _,_,e in p) for p in paths}!={tuple(p) for p in w['task_paths']}:
        raise ValueError('Stored route inventory differs from enumerated support')
    expected=[]
    for x in range(5):
        changed=deepcopy(q);changed['state']=x;answers=solve(changed)
        if len(answers)!=1:raise ValueError('Nonunique endpoint transformation')
        expected.extend(answers)
    if expected!=w['gold_endpoint_map'] or sorted(expected)!=list(range(5)):
        raise ValueError('Hidden-label metadata disagrees with exposed solver')
    for r,receipt in zip(w['responses'],w['audit']['tokens']):
        if not check_certificate(w['prompt'],r)['valid']:raise ValueError('Invalid saved gold')
        row=encode_row({'problem_id':w['world_id'],'prompt':w['prompt'],'response':r},tokenizer,max_length)
        for field in ('n_prompt','n_supervised','n_processed'):
            if row[field]!=receipt[field]:raise ValueError('Independent token receipt mismatch')
        if sha(json.dumps(row['input_ids']).encode())!=receipt['input_with_eos_sha256']:
            raise ValueError('Full input token digest differs')
        if sum(v!=-100 for v in row['labels'][1:])!=receipt['n_supervised'] or row['labels'][-1]!=tokenizer.eos_token_id:
            raise ValueError('Response mask/EOS mismatch')
    for name,receipt in w['audit']['views'].items():
        v=deepcopy(q)
        if name in ('useful_delete','irrelevant_delete'):
            remove=set(w['intervention'][name]);v['edges']=[e for e in v['edges'] if e['id'] not in remove]
            if len(q['edges'])-len(v['edges'])!=3:raise ValueError('Invalid deletion count')
        elif name=='source_change':v['state']=(v['state']+1)%5
        elif name=='target_change':
            for e in v['edges']:
                if e['v']==v['target']:e['table']=tuple((b+1)%5 for b in e['table'])
                elif e['u']==v['target']:e['table']=tuple(e['table'][(a-1)%5] for a in range(5))
        elif name!='clean':raise ValueError('Unknown view')
        text=render_from_existing_header(w['prompt'],v)
        if sha(text.encode())!=receipt['prompt_sha256']:raise ValueError('View prompt hash mismatch')
        if len(tokenizer(prefix(text),add_special_tokens=False)['input_ids'])!=receipt['n_prompt']:
            raise ValueError('Full deletion-view prompt tokens differ')
        if solve(parse_prompt(text))!=[receipt['answer']]:raise ValueError('View answer mismatch')
        ps=simple_paths(parse_prompt(text))
        if len(ps)!=(1 if name=='useful_delete' else 4) or {len(p) for p in ps}!={4}:
            raise ValueError('View support differs')
    if recheck_orbit and orbit_key(q)!=w['audit']['orbit']:raise ValueError('Canonical grouping differs')
    if w['audit']['failures']:raise ValueError('Saved construction failures')
    return [(x['n_supervised'],x['n_processed']) for x in w['audit']['tokens']]


def verify(directory,tokenizer_dir):
    started=time.monotonic();directory=Path(directory)
    summary=json.loads((directory/'summary.json').read_text())
    for name,hash_ in summary['files_sha256'].items():
        if Path(name).name!=name or sha((directory/name).read_bytes())!=hash_:
            raise ValueError('Artifact hash differs')
    for path,hash_ in summary['source_files_sha256'].items():
        raw=subprocess.check_output(['git','show',f"{summary['source_commit']}:{path}"])
        if sha(raw)!=hash_:raise ValueError('Published historical source differs')
    tokenizer,record=verified_tokenizer(Path(tokenizer_dir))
    if record!=summary['tokenizer']:raise ValueError('Pinned tokenizer differs')
    lengths={};orbits={};splits=Counter();labels=Counter();failures=[];source_pairs=set()
    expected_fit_ids=set();expected_audit_answers={}
    expected_ids={(s,i) for s in range(401,501) for i in range(100)}
    for archive in summary['archives']:
        for w in load_archive(directory/archive['file']):
            pair=(w['seed'],w['index'])
            if pair in source_pairs or pair not in expected_ids:raise ValueError('Unexpected/repeated semantic seed-index')
            source_pairs.add(pair)
            expected_split='probe_fit' if w['seed']<481 else 'probe_audit'
            if w['split']!=expected_split:raise ValueError('Split changed after generation')
            if expected_split=='probe_fit':expected_fit_ids.add(w['world_id'])
            else:expected_audit_answers[w['world_id']]={n:r['answer'] for n,r in w['audit']['views'].items()}
            try:lengths[w['world_id']]=check_record(w,tokenizer,1536)
            except ValueError as exc:failures.append({'world_id':w['world_id'],'error':str(exc)})
            c=w['audit']['orbit']['canonical_hex']
            if c in orbits:raise ValueError('Duplicate conservative orbit')
            orbits[c]=w['world_id'];splits[w['split']]+=1;labels[str(w['answer'])]+=1
        print(json.dumps({'stage':'independent_verification','worlds':sum(splits.values()),'failures':len(failures)}),flush=True)
    if source_pairs!=expected_ids:raise ValueError('Incomplete frozen population')
    schedule=json.loads((directory/'schedule.json').read_text());exposures={a:Counter() for a in ('multi','repeat')}
    totals={a:Counter() for a in exposures}
    for update in schedule['updates']:
        for arm in exposures:
            if sorted(update[arm])!=list(range(4)):raise ValueError('Unbalanced route slots')
            if not failures:
                rows=[lengths[w][r] for w,r in zip(update['world_ids'],update[arm])]
                totals[arm]['supervised']+=sum(x[0] for x in rows)
                totals[arm]['processed']+=sum(x[1] for x in rows)
                totals[arm]['padding']+=sum(2*max(rows[j][1],rows[j+1][1])-rows[j][1]-rows[j+1][1] for j in (0,2))
            for w,r in zip(update['world_ids'],update[arm]):exposures[arm][(w,r)]+=1
        if not failures:
            m=[lengths[w][r] for w,r in zip(update['world_ids'],update['multi'])]
            r=[lengths[w][r] for w,r in zip(update['world_ids'],update['repeat'])]
            if m!=r:raise ValueError('Per-example token mismatch')
    fit_ids=set(schedule['assignment'])
    if fit_ids!=expected_fit_ids or len(fit_ids)!=8000:raise ValueError('Bad accounting pool')
    for w in fit_ids:
        if [exposures['multi'][(w,r)] for r in range(4)]!=[1]*4:raise ValueError('Multi dose differs')
        if sorted(exposures['repeat'][(w,r)] for r in range(4))!=[0,0,0,4]:raise ValueError('Repeat dose differs')
    claims=json.loads((directory/'exposure_audit.json').read_text())
    if not failures:
        for arm,vals in totals.items():
            if any(claims['arms'][arm][k]!=v for k,v in vals.items()):raise ValueError('Exposure totals differ')
    preds=load_archive(directory/'probe_predictions.json');stats=json.loads((directory/'probes.json').read_text())
    if len(preds)!=2000 or {r['world_id'] for r in preds}!=set(expected_audit_answers):
        raise ValueError('Probe audit population differs')
    for r in preds:
        if r['split']!='probe_audit' or {n:v['answer'] for n,v in r['views'].items()}!=expected_audit_answers[r['world_id']]:
            raise ValueError('Probe prediction labels differ from independently solved views')
    config=summary['config'];all_probe_flags=[]
    for view in config['probe_views']:
        for name in config['probe_names']:
            correct=sum(r['views'][view]['predictions'][name]==r['views'][view]['answer'] for r in preds)
            stat=stats[view][name]
            p=binomtest(correct,len(preds),.2,alternative='greater').pvalue
            if correct!=stat['correct'] or stat['n']!=len(preds) or abs(p-stat['one_sided_p_vs_0_2'])>1e-12:
                raise ValueError('Probe statistics differ from retained predictions')
            if p*40<=.01:all_probe_flags.append(f'{view}/{name}')
    if all_probe_flags!=summary['probe_flags']:raise ValueError('Probe gate mismatch')
    if dict(labels)!=summary['label_counts']:raise ValueError('Label histogram differs')
    return {'verified':not failures,'worlds':len(source_pairs),'split_counts':dict(splits),
            'full_clean_references_retokenized':4*len(source_pairs),'view_prompts_retokenized':5*len(source_pairs),
            'unique_conservative_world_orbits':len(orbits),'schedule_totals':totals,
            'probe_predictions_checked':len(preds)*len(config['probe_names'])*len(config['probe_views']),
            'probe_flags':all_probe_flags,'failures':failures,'wall_seconds':time.monotonic()-started,
            'source_commit':summary['source_commit'],'manifest_sha256':sha((directory/'summary.json').read_bytes()),
            'scope':'Independent exposed-table solving and separate encode_row retokenization; shared verifier module, no model inference.',
            'gpu_seconds_added':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--tokenizer-dir',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise FileExistsError('Immutable verification output exists')
    result=verify(args.directory,args.tokenizer_dir)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verified':result['verified'],'worlds':result['worlds'],'wall_seconds':result['wall_seconds']}))
