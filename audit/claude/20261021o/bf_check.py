import json,sys,collections,hashlib
X=sys.argv[1]
R={}
for b in range(5):
    raw=json.load(open(f'{X}/generation/batches/{b:03d}/RAW.json'))
    rows=raw if isinstance(raw,list) else raw.get('rows') or raw.get('outputs') or raw
    if b==0: print(type(raw), list(raw)[:8] if isinstance(raw,dict) else json.dumps(rows[0])[:400])
    if isinstance(rows,dict): rows=list(rows.values())[0] if len(rows)==1 else rows
    n=len(rows); unm=[];fin=collections.Counter();lens=[];cap=0;mid_special=0
    for i,r in enumerate(rows):
        ids=r['token_ids']; fin[r.get('finish_reason')]+=1; lens.append(len(ids))
        u=sorted({t for t in ids if t>=151665})
        if u: unm.append((i,r.get('candidate_id') or r.get('id'),len(ids),r.get('finish_reason'),u,[k for k,t in enumerate(ids) if t>=151665],[k for k,t in enumerate(ids) if t in (151645,151643)]))
        if any(151643<=t<151665 and t not in (151645,151643) for t in ids): mid_special+=1
    R[b]=dict(n=n,finish=dict(fin),cap1024=sum(l==1024 for l in lens),unmapped=unm,other_special_rows=mid_special,ack=__import__('os').path.exists(f'{X}/generation/batches/{b:03d}/ACK.json'))
print(json.dumps(R,indent=1,default=str))
print(open(f'{X}/generation/FAILED.json').read()); print(open(f'{X}/FAILURE.json').read()[:800])
