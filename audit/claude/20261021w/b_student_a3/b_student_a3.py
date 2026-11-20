import json,sys,collections,re,glob,os
S,tokp,out=sys.argv[1:4]
T=json.load(open(tokp));id2={v:k for k,v in T['model']['vocab'].items()}
for a in T['added_tokens']: id2[a['id']]=a['content']
sp={a['id'] for a in T['added_tokens']}
bs=list(range(33,127))+list(range(161,173))+list(range(174,256));cs=bs[:];n=0
for b in range(256):
    if b not in bs: bs.append(b);cs.append(256+n);n+=1
dec={chr(c):b for b,c in zip(bs,cs)}
def decode(ids):
    o=bytearray();parts=[]
    for i in ids:
        t=id2[i]
        if i in sp: parts.append(o.decode('utf-8','replace'));o=bytearray();parts.append(t)
        else:o.extend(dec[ch] for ch in t)
    parts.append(o.decode('utf-8','replace'));return ''.join(parts)
def last_box(t):
    i=t.rfind('\\boxed{')
    if i<0:
        j=t.rfind('\\boxed ');return None if j<0 else t[j+7:].split('$')[0].strip()
    k=i+7;d=1;s=k
    while k<len(t) and d: d+=(t[k]=='{')-(t[k]=='}');k+=1
    return t[s:k-1] if d==0 else None
def norm(s):
    s=re.sub(r'\\left|\\right|\\!|\\,|\;|\\:|\s','',s);s=s.replace('dfrac','frac').replace('tfrac','frac').replace('^\\circ','').replace('^{\\circ}','').replace('$','')
    s=re.sub(r'\\text\{(.*?)\}',r'\1',s);return s.rstrip('.')
res={}
for job in ('B_B1_s17_r1','B_B3_s17_r1'):
    J=f'{S}/{job}';decd=json.load(open(J+'/audit/DECODED.json'));rows=json.load(open(J+'/audit/SCORING_ROWS.json'))
    sc=json.load(open(J+'/score/owned_score/payload/ALL_SCORED_ROWS.json'))
    raws={}
    for f in glob.glob(J+'/runtime/raw/*/*.json'):
        for r in json.load(open(f)): raws[(os.path.basename(os.path.dirname(f)),r['candidate_id'])]=r
    c=collections.Counter();flags=[];pairs={}
    assert len(decd)==len(rows)==len(sc)==2500 and len(raws)==2500
    for d,row,s in zip(decd,rows,sc):
        r=raws[(d['evaluation'],d['candidate_id'])];ids=r['token_ids'];st=d['stop'];sr=st['stop_reason']
        if any(t not in id2 for t in ids): c['unmapped']+=1
        if sr=='native_eos':
            e=next(i for i,t in enumerate(ids) if t in (151643,151645));exp=decode(ids[:e])
        elif sr=='length_cap':
            exp=decode(ids);c['cap_len_%d'%len(ids)]+=1
        else: exp=None;flags.append((d['candidate_id'],'stop '+sr))
        if exp is not None and exp!=st['answer_segment']: flags.append((d['evaluation'],d['candidate_id'],'decode'))
        if row['answer_segment']!=st['answer_segment'] or row['stop_reason']!=sr: flags.append((d['candidate_id'],'row'))
        if s['id']!=row['id']: flags.append((row['id'],'order'))
        cor=s['score']['correct'];c[sr]+=1
        if sr!='native_eos':
            if cor: flags.append((row['id'],'nonnative correct'))
            continue
        mine=last_box(st['answer_segment'])
        if mine is None:
            c['nobox']+=1
            if cor: flags.append((row['id'],'nobox correct'))
            continue
        if s['score'].get('extracted_answer') is not None and s['score']['extracted_answer'].strip()!=mine.strip(): flags.append((row['id'],'extract'))
        eq=norm(mine)==norm(row['gold'])
        if eq and not cor: flags.append((row['id'],'streq wrong',mine,row['gold']))
        elif cor and not eq: pairs[(mine,row['gold'])]=pairs.get((mine,row['gold']),0)+1
    byev=collections.defaultdict(list)
    for row,s in zip(rows,sc): byev[row['evaluation']].append(s['score']['correct'])
    res[job]=dict(counts=dict(c),flags=flags[:30],n_flags=len(flags),greedy=sum(byev['greedy']),
        sampled=sum(sum(byev[f'sample{i}']) for i in range(4)),symbolic_only_pairs=len(pairs),symbolic_only_rows=sum(pairs.values()),
        pairs=[list(p) for p in sorted(pairs)])
json.dump(res,open(out,'w'),indent=1,ensure_ascii=False)
for j,v in res.items(): print(j,{k:v[k] for k in v if k!='pairs'})
