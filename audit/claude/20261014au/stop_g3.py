import json,sys,glob,os,collections,hashlib
sys.path.insert(0,'/tmp/claude-0/wt_ed')
from analyses.completion_contract import first_stop, completion_score
X='/tmp/claude-0/aud_c/stop/x'
I='/tmp/claude-0/wt_ed/reports/exploratory_20261014/admission_v1/inputs'
tj=json.load(open(I+'/instruct_model/tokenizer.json'))
inv={v:k for k,v in tj['model']['vocab'].items()}
for a in tj['added_tokens']: inv[a['id']]=a['content']
special={a['id'] for a in tj['added_tokens']}
V=len(inv)
bs=list(range(ord("!"),ord("~")+1))+list(range(ord("¡"),ord("¬")+1))+list(range(ord("®"),ord("ÿ")+1));cs=bs[:];n=0
for b in range(256):
    if b not in bs: bs.append(b);cs.append(256+n);n+=1
bdec={chr(c):b for b,c in zip(bs,cs)}
def dec(ids,skip=True):
    out=bytearray()
    for i in ids:
        if i in special:
            if not skip: out+=inv[i].encode()
            continue
        out+=bytes(bdec[ch] for ch in inv[i])
    return out.decode('utf-8',errors='replace')
test={json.loads(l)['problem_id']:json.loads(l) for l in open(I+'/gsm8k_test1319.jsonl')}
order=[json.loads(l)['problem_id'] for l in open(I+'/gsm8k_test1319.jsonl')]
res={}
for run,eos_ids,eos in [('base_4shot',[151643],151643),('instruct_0shot',[151645,151643],151645),('wrong_teacher_t1',[151643],151643)]:
    d=f'{X}/{run}/endpoint1319'; acked={os.path.basename(p)[len('endpoint1319_batch_'):-5] for p in glob.glob(f'{X}/{run}/completed/endpoint1319_batch_*.json')}
    rows={};evbad=0;scbad=0;n=0;caps=0;stops=collections.Counter()
    for raw in sorted(glob.glob(d+'/batch_*_raw.json')):
        start=os.path.basename(raw)[6:10]; r=json.load(open(raw))
        sc=[json.loads(l) for l in open(raw.replace('_raw.json','_scored.jsonl'))] if os.path.exists(raw.replace('_raw.json','_scored.jsonl')) else []
        for j,(pid,toks,ev) in enumerate(zip(r['problem_ids'],r['batch_output_ids'],r['events'])):
            norm=[eos if t in eos_ids else t for t in toks]
            mine=first_stop(norm,lambda x:dec(x,True),eos,512,(special-set(eos_ids))|{t for t in toks if t>=V})
            if mine!=ev: evbad+=1
            s=completion_score(test[pid],mine)
            if sc and sc[j]['task_score']!=s: scbad+=1
            rows[pid]=dict(correct=s['task_answer_correct'],acked=start in acked,stop=mine['stop_reason'],val=s['marked']['value'])
            stops[mine['stop_reason']]+=1; n+=1
    pref=[p for p in order if p in rows]
    assert pref==order[:len(pref)], 'not a prefix'
    res[run]=dict(rows=n,acked=sum(v['acked'] for v in rows.values()),event_mismatch=evbad,score_mismatch=scbad,stops=dict(stops),
                  correct_all=sum(v['correct'] for v in rows.values()),correct_acked=sum(v['correct'] for v in rows.values() if v['acked']))
    json.dump(rows,open(f'/tmp/claude-0/aud_c/stop_{run}.json','w'))
print(json.dumps(res,indent=1))
