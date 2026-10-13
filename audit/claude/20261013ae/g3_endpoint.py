"""Claude independent G3: endpoint re-decode, own stop/boundary, own answer parser vs frozen judgments.
Run on the owner's device against the Codex worktree copy of reports/p008_20261013/base_v1 (file hashes
checked equal to commit efeb6380). decode()/id2tok/special come from Claude's own byte-level BPE decoder
(~/aud/rescore.py, tokenizer.json tables only); no HF tokenizer, no Codex parser imported."""
import json, glob, os, re, sys, collections, hashlib
from fractions import Fraction
src=open(os.path.expanduser('~/aud/teacher_rescore.py')).read()
exec(src.split("def run(folders):")[0])   # decode(), id2tok, special, U, W
EOT=151643
D=sys.argv[1]; OUT=sys.argv[2]
ev=[json.loads(l) for l in open(D+'/gsm8k_test1319.jsonl') if l.strip()] if os.path.exists(D+'/gsm8k_test1319.jsonl') else \
   [json.loads(l) for l in open(W+'/reports/p008_20261013/student_admission_v1/inputs/gsm8k_test1319.jsonl') if l.strip()]
G={r['problem_id']:r for r in ev}; order=[r['problem_id'] for r in ev]
def raw_decode(ids):  # no special stop; caller guarantees none present
    out=bytearray()
    for i in ids: out+=bytes(U[ch] for ch in id2tok[i])
    return out.decode('utf-8',errors='replace')
def boundary(text):
    # independent line scan: a line whose first non-[ \t] chars are Problem/Question/Q (+[ \t]*:) or [Problem]/[Question]
    pos=0
    for line in text.split('\n'):
        s=line.lstrip(' \t'); off=pos+len(line)-len(s); low=s.lower()
        hit=None
        for w in ('[problem]','[question]'):
            if low.startswith(w): hit=s[:len(w)]
        if hit is None:
            for w in ('problem','question','q'):
                if low.startswith(w):
                    rest=s[len(w):]; r2=rest.lstrip(' \t')
                    if r2.startswith(':'): hit=s[:len(w)+len(rest)-len(r2)+1]; break
        if hit is not None: return off,hit
        pos+=len(line)+1
    return None
def my_num(s):
    s=s.strip()
    s=re.sub(r'\\(?:text|mathrm|textbf)\{([^{}]*)\}',r' \1 ',s)
    s=s.replace('\\$','').replace('$','').replace('\\,','').replace('\\!','').replace('\\%','').replace('%','')
    s=s.strip().rstrip('.!').strip()
    m=re.fullmatch(r'\\[dt]?frac\{(-?\d+)\}\{(-?\d+)\}',s)
    if m: return Fraction(int(m[1]),int(m[2]))
    nums=re.findall(r'(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?:/\d+)?',s)
    if len(nums)!=1: return None
    t=nums[0].replace(',','')
    try: return Fraction(t)
    except Exception: return None
def my_claims(seg):
    c=[]
    i=0
    while True:
        j=min([k for k in (seg.find('\\boxed{',i),seg.find('\\fbox{',i)) if k>=0],default=-1)
        if j<0: break
        k=seg.find('{',j)+1; d=1
        while k<len(seg) and d: d+={'{':1,'}':-1}.get(seg[k],0); k+=1
        c.append(('box',j,my_num(seg[seg.find('{',j)+1:k-1]) if d==0 else None)); i=k
    for m in re.finditer(r'####([^\n]*)',seg): c.append(('hash',m.start(),my_num(m[1])))
    for m in re.finditer(r'(?im)^[ \t]*(?:so the answer is|the answer is|answer\s*:)[: \t]*([^\n]*)',seg):
        if '\\boxed' in m[1] or '\\fbox' in m[1]: continue
        c.append(('stmt',m.start(),my_num(m[1])))
    return sorted(c,key=lambda x:x[1])
res={}; stats=collections.Counter(); evdis=[]; rowdis=[]; padded=0; gen_tok=0; seen=[]
raws=sorted(glob.glob(D+'/endpoint1319/batch_*_raw.json'))
for f in raws:
    x=json.load(open(f)); sc=[json.loads(l) for l in open(f.replace('_raw.json','_scored.jsonl'))]
    pids=x['problem_ids']; assert len(pids)==len(sc)==len(x['events'])==len(x['batch_output_ids'])
    steps=len(x['batch_output_ids'][0]); padded+=len(pids)*(x['prompt_width']+steps)
    for pid,inp,ids,e,s in zip(pids,x['input_ids'],x['batch_output_ids'],x['events'],sc):
        seen.append(pid); r=G[pid]
        assert len(inp)<=x['prompt_width']
        if decode(inp)!=f"Problem: {r['prompt']}\nSolution:\n": stats['prompt_text_mismatch']+=1
        if s['generated_ids']!=ids[:len(s['generated_ids'])] or s['problem_id']!=pid: stats['row_mismatch']+=1
        term=next((i for i,t in enumerate(ids) if t in special),None)
        vis=ids[:term] if term is not None else ids
        whole=raw_decode(vis); b=boundary(whole)
        if b:
            k=next(k for k in range(1,len(vis)+1) if boundary(raw_decode(vis[:k])))
            t=raw_decode(vis[:k]); bo,trig=boundary(t)
            mine={'stop_reason':'new_problem_boundary','retained_tokens':k,'actual_eos_at_stop':False,'answer_segment':t[:bo],'boundary_offset':bo,'trigger_text':trig}
        elif term is not None:
            rs='native_eos' if ids[term]==EOT else 'invalid_special_token'
            mine={'stop_reason':rs,'retained_tokens':term+1,'actual_eos_at_stop':rs=='native_eos','answer_segment':whole,'boundary_offset':None,'trigger_text':None}
        else:
            assert len(ids)==512
            mine={'stop_reason':'length_cap','retained_tokens':512,'actual_eos_at_stop':False,'answer_segment':whole,'boundary_offset':None,'trigger_text':None}
        if mine!=e or mine!=s['stop']: evdis.append((pid,{k:(mine[k],e.get(k)) for k in mine if mine[k]!=e.get(k)}))
        gen_tok+=mine['retained_tokens']
        if s['generated_tokens']!=mine['retained_tokens']: stats['gen_tok_mismatch']+=1
        if s['post_stop_padding_tokens']!=steps-mine['retained_tokens']: stats['padding_mismatch']+=1
        gold=Fraction(r['answer'].replace(',',''))
        if Fraction(r['response'].split('####')[-1].strip().replace(',',''))!=gold: stats['gold_inconsistent']+=1
        cl=my_claims(mine['answer_segment']); vals={v for _,_,v in cl}
        st='missing' if not cl else 'unresolved' if None in vals else 'conflict' if len(vals)>1 else 'parsed'
        completed=mine['stop_reason'] in ('native_eos','new_problem_boundary')
        my_ok= completed and st=='parsed' and next(iter(vals))==gold
        last=[v for _,_,v in cl if v is not None]
        lastclaim_ok= completed and bool(last) and last[-1]==gold
        fz=s['task_score']; frozen_ok=fz['task_answer_correct']
        stats['my_correct']+=my_ok; stats['frozen_correct']+=frozen_ok; stats['lastclaim_correct']+=lastclaim_ok
        stats['frozen_parsed']+= fz['marked']['status']=='parsed'; stats['my_parsed']+= st=='parsed'
        stats['stop_'+mine['stop_reason']]+=1
        if mine['stop_reason']=='length_cap': stats['cap_frozen_correct']+=frozen_ok; stats['cap_marked_correct_anyway']+=fz['marked']['answer_correct']
        if my_ok!=frozen_ok: rowdis.append((pid,my_ok,frozen_ok,st,fz['marked']['status'],[(k,str(v)) for k,_,v in cl],[(c['kind'],c['payload']) for c in fz['marked']['claims']],mine['answer_segment'][-220:]))
        res[pid]={'mine':my_ok,'frozen':frozen_ok,'last':lastclaim_ok}
summ=json.load(open(D+'/endpoint1319/summary.json'))
qc=summ['question_correct']
print('n',len(seen),'order_ok',seen==order,'raw_files',len(raws))
print(dict(stats)); print('event_dis',len(evdis),evdis[:3])
print('gen_tok',gen_tok,'summary',summ['generated_tokens'],'padded',padded,'summary',summ['padded_tokens'])
print('summary question_correct agrees with rows', all(qc[p]==res[p]['frozen'] for p in res), sum(qc.values()))
print('row disagreements', len(rowdis))
for d in rowdis: print(json.dumps(d,ensure_ascii=False)[:900])
json.dump({'stats':stats,'res':res,'rowdis':rowdis,'evdis':evdis},open(OUT,'w'),ensure_ascii=False,default=str)
