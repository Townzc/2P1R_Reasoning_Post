import json,sys,gzip,hashlib,collections,glob,os
sys.path.insert(0,'/tmp/claude-0/a4/r'); sys.path.insert(0,'/tmp/claude-0/p9tools')
from analyses.completion_contract import first_stop, completion_score
from qtok import build
enc,dec,_=build('/tmp/claude-0/p9/qwen_tok.json')
tj=json.load(open('/tmp/claude-0/p9/qwen_tok.json')); V=len(tj['model']['vocab'])+len(tj['added_tokens'])
special=[a['id'] for a in tj['added_tokens'] if a.get('special')]
A='/tmp/claude-0/a4/'; N='/tmp/claude-0/pa/rep/'
test={json.loads(l)['problem_id']:json.loads(l) for l in open(A+'test1319.jsonl')}
ep=json.load(open(A+'ncin/NC_ENDPOINT.json'))
orc=json.load(gzip.open('/tmp/claude-0/pa/r/reports/p009_20261014/stage1_nc_guard_repair_complete_v1/REPLACEMENT_LOCAL_ORACLE.json.gz'))
bad=collections.Counter(); mine={}; stops=collections.Counter(); seen=[]
for off in range(0,1319,256):
    raw=json.load(open(N+f'endpoint/raw/{off:05d}.json')); part=ep[off:off+256]
    if [r['problem_id'] for r in raw]!=[p['problem_id'] for p in part]: bad['order']+=1
    for row,item in zip(part,raw):
        if item['prompt_token_ids']!=row['input_ids']: bad['prompt']+=1
        if item['candidate_id']!=row['candidate_id']: bad['cid']+=1
        ids=item['token_ids']
        if any(t>=V for t in ids): bad['oov']+=1
        ev=first_stop(ids,dec,151643,512,tuple(special))
        s=completion_score(test[row['problem_id']],ev)
        mine[row['problem_id']]=s['task_answer_correct']; stops[ev['stop_reason']]+=1; seen.append(row['problem_id'])
dd={d['problem_id']:d for d in orc['decoded']}
print('rows',len(mine),'unique',len(set(seen)),'correct',sum(mine.values()),'stops',dict(stops),'issues',dict(bad))
print('== oracle question_correct', mine==orc['question_correct'], 'oracle correct',orc['correct'])
diff=[p for p in mine if mine[p]!=orc['question_correct'][p]]; print('disagree',len(diff),diff[:5])
# compare per-row events/scores with oracle decoded
raws={off:json.load(open(N+f'endpoint/raw/{off:05d}.json')) for off in range(0,1319,256)}
em=sm=0
for off,raw in raws.items():
    for item in raw:
        ev=first_stop(item['token_ids'],dec,151643,512,tuple(special)); o=dd[item['problem_id']]
        if ev!=o['stop']: em+=1
        if completion_score(test[item['problem_id']],ev)!=o['score']: sm+=1
        if o['raw_file_sha256']!=hashlib.sha256(open(N+o['raw_file'],'rb').read()).hexdigest(): bad['rawsha']+=1
print('event mismatches',em,'score mismatches',sm,'rawsha',bad['rawsha'])
# dose
plan=json.load(open(A+'ncin/nc17_n3200_plan.json')); encd=json.load(open(A+'ncin/nc17_n3200_encoded.json'))
t=p_=0; dm=0
for step,idx in enumerate(plan['updates'],1):
    d=json.load(open(N+f'completed/update_{step:04d}.json')); a=json.load(open(N+f'intents/update_{step:04d}.json'))
    st=sum(encd[i]['n_supervised'] for i in idx); pt=sum(encd[i]['n_processed'] for i in idx); t+=st; p_+=pt
    w=dict(step=step,indices=idx,lr=plan['lrs'][step-1],supervised_tokens=st,processed_tokens=pt)
    if a!=w or any(d.get(k)!=v for k,v in w.items()) or d['cumulative_targets']!=t or d['cumulative_processed']!=p_: dm+=1
print('updates',len(plan['updates']),'dose mismatches',dm,'targets',t,'processed',p_, 'oracle processed',orc['processed_tokens_verified'])
names={os.path.basename(f)[:-5] for f in glob.glob(N+'completed/*.json')}
exp={f'update_{i:04d}' for i in range(1,1025)}|{'terminal_merge'}|{f'endpoint_{i:05d}' for i in range(0,1319,256)}
print('completed units',len(names),'non-update/endpoint/merge',len(names-exp),'missing',len(exp-names))
mp=json.load(open(N+'MERGE_PROOF.json')); pe=json.load(open(N+'TRAINING_PROCESS_EXITED.json'))
print('merge',mp.get('merge_dtype'),mp.get('saved_dtype'),mp.get('optimizer_updates_after_terminal_save'),'exit',pe.get('exitcode'),pe.get('joined_before_endpoint'))
o400=json.load(gzip.open('/tmp/claude-0/a4/r/reports/p009_20261014/stage1_nc_preemption_disposition_v1/nc_s17_n400/LOCAL_ORACLE_AUDIT.json.gz'))['question_correct']
ids=[p['problem_id'] for p in ep]
lo=sum(o400[i] for i in ids); hi=sum(mine[i] for i in ids); d=hi-lo
print('PAIR n400',lo,'n3200',hi,'delta',d,'pp',round(100*d/1319,3),'discordant',sum(o400[i]!=mine[i] for i in ids),'stop?',100*d>=5*1319)
print('only n3200 right',sum(mine[i] and not o400[i] for i in ids),'only n400 right',sum(o400[i] and not mine[i] for i in ids))
import random
random.seed(20261014); diffs=[]
for _ in range(10000):
    s=[random.choice(ids) for _ in ids]; diffs.append(100*sum(mine[i]-o400[i] for i in s)/1319)
diffs.sort(); print('my bootstrap 95% CI (python random, not registered generator)',round(diffs[249],2),round(diffs[9749],2))
