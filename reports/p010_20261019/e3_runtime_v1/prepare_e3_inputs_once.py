"""Copy the already frozen E3 roster and saved T0.8 verdicts; no token/scorer execution."""
from pathlib import Path
from collections import Counter
from experiments.p010.common import read,dump,sha,digest,manifest,utc
from experiments.p010.teacher_contract import sampling
r=Path('.local/p010_20261019/r1');old=r/'inputs';original=r/'teacher_t72_export_r1/evidence'
roster=read(old/'MATH_ROSTERS.json');pids=roster['e3_hash200']
assert len(pids)==len(set(pids))==200 and set(pids)<=set(roster['s1']['400'])
source={x['problem_id']:x for x in read(old/'MATH_SOURCE.json')}
queue={x['candidate_id']:x for x in read(old/'t72_fixed_requests.json')}
saved=read(original/'RECORD_INDEX.json');review=read(r/'T72_DATA_A1_ACCEPTED.json')
assert review['decision'] in ('PASS','PASS-WITH-NOTES') and sha(review['local_report_file'])==review['report_sha256']
assert read(r/'teacher_t72_export_r1/COMPLETED.json')['provider_stopped'] is True
groups={};inherited=[];prompts=[]
for pid in pids:
    req=queue[pid+'::attempt01'];prompts.append(dict(problem_id=pid,problem=source[pid]['problem'],prompt_token_ids=req['prompt_token_ids']))
    assert len(req['prompt_token_ids'])+1024<=2048
    for attempt in range(1,9):
        cid=f'{pid}::attempt{attempt:02d}';s=saved[cid]
        assert s['candidate_id']==cid and s['problem_id']==pid and s['attempt']==attempt
        inherited.append(dict(original_candidate_id=cid,original_record=s,original_record_sha256=digest(s)))
for label,temp in [('t06',.6),('t10',1.)]:
    rows=[]
    for pid in pids:
        for attempt in range(1,9):
            cid=f'{pid}::attempt{attempt:02d}';q=queue[cid];params=sampling(q);params['temperature']=temp
            assert q['prompt_token_ids']==queue[pid+'::attempt01']['prompt_token_ids']
            rows.append(dict(candidate_id='p010_e3/'+label+'/'+cid,original_seed_candidate_id=cid,
                problem_id=pid,attempt=attempt,temperature=temp,model='t72',seed=q['seed'],
                prompt_token_ids=q['prompt_token_ids'],sampling=params,source_row_sha256=digest(q)))
    assert len(rows)==1600 and len({x['candidate_id'] for x in rows})==1600
    assert set(Counter(x['problem_id'] for x in rows).values())=={8}
    groups[label]=rows
assert not {x['candidate_id'] for x in groups['t06']} & {x['candidate_id'] for x in groups['t10']}
out=r/'e3_inputs_r1';out.mkdir(exist_ok=False)
dump(out/'STARTED.json',dict(utc=utc(),new_models=0,new_symbolic_scores=0,new_token_encodings=0,new_raw_decodes=0))
for label,rows in groups.items():dump(out/(label+'_requests.json'),rows)
dump(out/'PROMPT_TEXTS.json',prompts)
dump(out/'ROSTER.json',dict(problem_ids=pids,new_temperatures=[.6,1.],new_attempts_per_problem=8,
    reused_temperature=.8,reused_attempts=list(range(1,9)),original16_preserved_outside_matched_comparison=True,
    original_frozen_roster_sha256=sha(old/'MATH_ROSTERS.json'),
    seed_relation='Same original per-question/per-attempt frozen seed across all three temperatures; new request identities include temperature.',
    no_correctness_based_reselection=True))
dump(out/'ORIGINAL_T08_ROWS.json',inherited)
dump(out/'GOLD_SOURCE.json',[source[p] for p in pids])
worker=['t06_requests.json','t10_requests.json','PROMPT_TEXTS.json','ROSTER.json']
basis=dict(utc=utc(),source_files={'prepare_e3_inputs_once.py':sha(__file__)},
    original_inputs={k:sha(old/k) for k in ['MATH_ROSTERS.json','MATH_SOURCE.json','t72_fixed_requests.json']},
    original_t72_record_index_sha256=sha(original/'RECORD_INDEX.json'),
    original_t72_export_completion_sha256=sha(r/'teacher_t72_export_r1/COMPLETED.json'),
    original_actual_A1={k:v for k,v in review.items() if k!='local_report_file'},
    exact_problem_ids=pids,new_request_counts={k:len(v) for k,v in groups.items()},saved_rows_reused=len(inherited),
    worker_files={n:dict(bytes=(out/n).stat().st_size,sha256=sha(out/n)) for n in worker},
    local_only_files=['ORIGINAL_T08_ROWS.json','GOLD_SOURCE.json'],no_new_encoding_or_decode_or_scoring=True,
    no_upload_or_model_call=True,actual_runtime_A2_pending=True)
dump(out/'BASIS.json',basis);dump(out/'MANIFEST.json',manifest(out));dump(out/'COMPLETED.json',dict(utc=utc(),basis_sha256=sha(out/'BASIS.json'),worker_files=basis['worker_files'],new_outputs_prepared=3200,reused_saved_rows=1600,actual_models=0))
print(dict(prepared=str(out),new_outputs=3200,reused=1600,no_new_scoring=True))
