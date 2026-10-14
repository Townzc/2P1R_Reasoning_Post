import json,sys,glob,os,collections
sys.path.insert(0,'/tmp/claude-0/wt_ed')
from analyses.completion_contract import first_stop, completion_score
I='/tmp/claude-0/wt_ed/reports/exploratory_20261014/admission_v1/inputs'
tj=json.load(open(I+'/instruct_model/tokenizer.json'))
inv={v:k for k,v in tj['model']['vocab'].items()}
for a in tj['added_tokens']: inv[a['id']]=a['content']
special={a['id'] for a in tj['added_tokens']}; V=len(inv)
bs=list(range(ord("!"),ord("~")+1))+list(range(ord("¡"),ord("¬")+1))+list(range(ord("®"),ord("ÿ")+1));cs=bs[:];n=0
for b in range(256):
    if b not in bs: bs.append(b);cs.append(256+n);n+=1
bdec={chr(c):b for b,c in zip(bs,cs)}
def dec(ids):
    out=bytearray()
    for i in ids:
        if i in special: continue
        out+=bytes(bdec[ch] for ch in inv[i])
    return out.decode('utf-8',errors='replace')
order=[json.loads(l)['problem_id'] for l in open(I+'/gsm8k_test1319.jsonl')]
test={json.loads(l)['problem_id']:json.loads(l) for l in open(I+'/gsm8k_test1319.jsonl')}
prompts={k:{p['problem_id']:p['input_ids'] for p in json.load(open(f'{I}/{k}_prompts.json'))} for k in ('base_4shot','instruct_0shot','wrong_teacher_t1')}
out={}
for run,eos_ids,eos in [('base_4shot',[151643],151643),('instruct_0shot',[151645,151643],151645),('wrong_teacher_t1',[151643],151643)]:
    rows={};bad=collections.Counter();starts=[];stops=collections.Counter();src={}
    for tag,d in (('prefix',f'/tmp/claude-0/aud_c/stop/x/{run}/endpoint1319'),('suffix',f'/tmp/claude-0/aud_c/fin/{run}/x/endpoint1319')):
        for raw in sorted(glob.glob(d+'/batch_*_raw.json')):
            st=int(os.path.basename(raw)[6:10]); starts.append((tag,st)); r=json.load(open(raw))
            sc=[json.loads(l) for l in open(raw.replace('_raw.json','_scored.jsonl'))]
            if r['problem_ids']!=order[st:st+16]: bad['batch_ids']+=1
            if r['input_ids']!=[prompts[run][p] for p in r['problem_ids']]: bad['prompt']+=1
            for j,(pid,toks,ev) in enumerate(zip(r['problem_ids'],r['batch_output_ids'],r['events'])):
                norm=[eos if t in eos_ids else t for t in toks]
                mine=first_stop(norm,dec,eos,512,(special-set(eos_ids))|{t for t in toks if t>=V})
                if mine!=ev: bad['event']+=1
                s=completion_score(test[pid],mine)
                if sc[j]['task_score']!=s: bad['score']+=1
                if pid in rows: bad['dup']+=1
                rows[pid]=s['task_answer_correct']; stops[mine['stop_reason']]+=1; src[pid]=tag
    cov=set(rows)==set(order)
    res=json.load(open(f'/tmp/claude-0/aud_c/fin/{run}/result.json'))
    qc=res.get('endpoint',res).get('question_correct') if isinstance(res,dict) else None
    out[run]=dict(n=len(rows),complete=cov,correct=sum(rows.values()),acc=round(100*sum(rows.values())/len(rows),2),
        stops=dict(stops),mismatch=dict(bad),prefix_rows=sum(v=='prefix' for v in src.values()),
        suffix_first=min(s for t,s in starts if t=='suffix'),
        matches_child_summary=(qc=={p:rows[p] for p in order}) if qc else 'n/a')
    json.dump(''.join('1' if rows[p] else '0' for p in order),open(f'/tmp/claude-0/aud_c/fin/{run}_bits.json','w'))
print(json.dumps(out,indent=1))
