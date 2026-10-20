"""New P010 rosters and E4 tokenization only. No old model/scoring replay."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil

from experiments.p010.common import dump, read, sha, manifest, digest, MODELS, PLAN_COMMIT, utc
from experiments.learning_regime_p009.training_plan import make_plan, TARGETS, UPDATES, LR_VECTOR_SHA256
from experiments.learning_regime_p009.stage1_roster import nested_encoded_sets
from scripts.prepare_p009_stage0_inputs import teacher_seed
from src.sft_data import encode_row


def prepare(out):
    r = Path('.local/p009_20261014/r1'); out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    dump(out/'STARTED.json', dict(utc=utc(), plan_commit=PLAN_COMMIT, model_calls=0))
    inputs = r/'stage0_inputs_r1'
    train = [json.loads(x) for x in (inputs/'math_train7500.jsonl').open()]
    by_pid = {x['problem_id']: x for x in train}
    s1 = r/'stage1_s1_inputs_r1'
    roster = {str(n): [x['problem_id'] for x in read(s1/f's1_s17_n{n}_rows.json')] for n in (400,3200)}
    assert roster['400'] == roster['3200'][:400]
    unsupported = {x['problem_id'] for x in read(inputs/'unsupported_math_train.json')}
    candidates = [x for x in train if x['problem_id'] not in set(roster['3200']) | unsupported]
    # E2 is fixed before any new outcomes and is excluded from E1d.
    dev = sorted(candidates, key=lambda x: (hashlib.sha256(
        ('p010-e2-dev:20261019:'+x['problem_id']).encode()).hexdigest(), x['problem_id']))[:30]
    dev_ids = {x['problem_id'] for x in dev}
    e1d = [x['problem_id'] for x in train if x['problem_id'] not in unsupported | dev_ids]
    random.Random(20261019).shuffle(e1d)
    smoke = sorted(roster['400'], key=lambda pid: hashlib.sha256(
        ('p010-t72-smoke:20261019:'+pid).encode()).hexdigest())[:20]
    requests = [json.loads(x) for x in (inputs/'math_teacher_requests8993.jsonl').open()]
    first = {x['problem_id']: x for x in requests if x['attempt'] == 1}
    existing_t15 = {x['candidate_id'] for x in requests if x['problem_id'] in set(roster['400'])}
    # Reuse exact original prompt token IDs and original per-candidate seed rule.
    generation = {}
    for model in ('t15','t7','t72'):
        rows=[]
        if model != 't15':
            for pid in roster['3200']:
                rows.append(dict(first[pid], model=model, phase='first_attempt'))
        for attempt in range(2,17):
            for pid in roster['400']:
                cid=f'{pid}::attempt{attempt:02d}'
                if model == 't15' and cid in existing_t15:
                    continue
                rows.append(dict(candidate_id=cid, problem_id=pid, attempt=attempt,
                    seed=teacher_seed(cid), prompt_token_ids=first[pid]['prompt_token_ids'],
                    model=model, phase='k_supply'))
        generation[model] = rows
        dump(out/f'{model}_fixed_requests.json', rows)
    dump(out/'MATH_ROSTERS.json', dict(s1=roster, e2_dev=[x['problem_id'] for x in dev],
        e1d_order=e1d, smoke20=smoke, e3_hash200=sorted(roster['400'], key=lambda pid:
        hashlib.sha256(('p010-e3:20261019:'+pid).encode()).hexdigest())[:200],
        e1d_order_method='Python Random(20261019).shuffle, original P009 train order; no correctness filter',
        unsupported=sorted(unsupported), source_train_sha256=sha(inputs/'math_train7500.jsonl')))
    dump(out/'MATH_SOURCE.json', train)
    dump(out/'E2_DEV.json', dev)
    dump(out/'T72_SMOKE20.json', [dict(first[pid], model='t72') for pid in smoke])
    # Preserve the physical original P2 raw files, not regenerated/decoded text.
    evidence = r/'stage0_generation_budget_r2/exports/teacher_p2_p3/evidence'
    found={}; copied={}; oldout=out/'t15_attempt01_original_raw';oldout.mkdir()
    for path in sorted((evidence/'math_procurement/raw').glob('*.json')):
        original=read(path); records=original['outputs'] if isinstance(original,dict) else original
        selected=[(i,x) for i,x in enumerate(records) if x['candidate_id'] in existing_t15]
        if selected:
            shutil.copyfile(path,oldout/path.name);assert sha(oldout/path.name)==sha(path)
            copied[path.name]={'sha256':sha(path),'bytes':path.stat().st_size}
            for i,x in selected:found[x['candidate_id']]={'file':path.name,'index':i,'record_sha256':digest(x)}
    assert set(found)==existing_t15
    dump(out/'T15_REUSE.json',dict(physical_files=copied,records=found,
        source_root='P009 teacher_p2_p3/math_procurement/raw',byte_identical=True,new_generation=False,
        attempt01_count=400,additional_original_attempts=len(found)-400,
        note='Reuse already saved attempts2-4 as well; only missing attempts through16 are generated.'))
    # P009 S2 corpus and permutation are reused; OLMo encoding is newly materialized.
    from transformers import AutoTokenizer
    tokenizer_dir = r/'source_assets_r1/olmo'
    tok=AutoTokenizer.from_pretrained(tokenizer_dir,local_files_only=True)
    corpus=read(r/'stage1_nc_inputs_r1/ORIGINAL_G1.json')
    source=r/'stage1_nc_inputs_r1/ORIGINAL_D1_INPUT.jsonl'
    rows=[json.loads(x) for x in source.open()]
    encoded=[encode_row(x,tok,2048) for x in rows]
    frozen_lengths={x['path_id']:x['n_supervised'] for x in read(r/'data_feasibility_r1/olmo_d1_lengths.json')['rows']}
    assert all(x['n_supervised']==frozen_lengths[x['path_id']] for x in encoded)
    selected=nested_encoded_sets(encoded,17,100257,negative_control=True)
    lookup={x['problem_id']:(x,e) for x,e in zip(rows,encoded)}
    summaries={}
    for n in (400,3200):
        ids=selected['selections'][str(n)]['problem_ids']; rr=[lookup[i][0] for i in ids]; ee=[lookup[i][1] for i in ids]
        plan=make_plan(ee,17,100257)
        config=dict(experiment='P010',arm='E4',model=MODELS['olmo'],n=n,seed=17,
            updates=UPDATES,targets=TARGETS,lr_vector_sha256=LR_VECTOR_SHA256,eos_token_id=100257,
            rows_sha256=digest(rr),encoded_sha256=digest(ee),plan_sha256=digest(plan),
            endpoint='GSM8K',max_new_tokens=512,g0_bypassed_by_explicit_diagnostic_scope=True)
        for suffix,data in [('rows',rr),('encoded',ee),('plan',plan),('config',config)]:dump(out/f'e4_n{n}_{suffix}.json',data)
        summaries[str(n)]=dict(config=config,once_each_targets=sum(x['n_supervised'] for x in ee),
            q=plan['q'],min_exposures=min(plan['row_exposures']),max_exposures=max(plan['row_exposures']))
    for name in ('olmo_gsm_zero.json','olmo_gsm_four.json'):
        shutil.copyfile(inputs/name,out/name)
    dump(out/'E4_SUMMARY.json',dict(summaries=summaries,corpus_sha256=sha(source),
        frozen_OLMo_lengths_sha256=sha(r/'data_feasibility_r1/olmo_d1_lengths.json'),
        original_G1=corpus,endpoint_files_reused=True,training_calls=0,
        four_shot_baseline_reuse='P009 olmo_p3 already completed 487/1319, no duplicate inference'))
    dump(out/'MANIFEST.json',manifest(out))
    print(json.dumps({'out':str(out),'E4':summaries,'new_requests':{k:len(v) for k,v in generation.items()},
        't15_reused':len(found),'new_model_calls':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);prepare(p.parse_args().out)
