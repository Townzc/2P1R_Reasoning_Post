import json,sys,tarfile,re,pickle,collections
T=json.load(open(sys.argv[1])); vocab=T['model']['vocab']; id2tok={v:k for k,v in vocab.items()}
for a in T['added_tokens']: id2tok[a['id']]=a['content']
special={a['id'] for a in T['added_tokens'] if a.get('special')}
bs=list(range(33,127))+list(range(161,173))+list(range(174,256));cs=bs[:];n=0
for b in range(256):
    if b not in bs: bs.append(b);cs.append(256+n);n+=1
dec={chr(c):b for b,c in zip(bs,cs)}
def decode(ids):
    out=bytearray();parts=[]
    for i in ids:
        t=id2tok[i]
        if i in special: parts.append(out.decode('utf-8','replace'));out=bytearray();parts.append(t)
        else: out.extend(dec[ch] for ch in t)
    parts.append(out.decode('utf-8','replace'));return ''.join(parts)
EOS=(151645,151643)
def esc(t,i):
    k=0;j=i-1
    while j>=0 and t[j]=='\\': k+=1;j-=1
    return k%2==1
def seg(t):
    d=1
    for i,c in enumerate(t):
        if not esc(t,i): d+=(c=='{')-(c=='}')
        if d==0: return '\\boxed{'+t[:i+1],True
    return '\\boxed{'+t,False
res=collections.defaultdict(dict)
tf=tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz')
for m in tf:
    n=m.name
    if not m.isfile(): continue
    p=n.split('/')
    if n.startswith('collect/cells/') and '/raw/' in n:
        cell=p[2]
        for r in json.load(tf.extractfile(m)):
            a=r['answers'][0];ids=a['token_ids']
            stop=next(((i,'native_eos' if t in EOS else 'invalid_special_token') for i,t in enumerate(ids) if t in EOS or t in special),None)
            vis=ids[:stop[0]] if stop else ids;ns=stop[1] if stop else ('length_cap' if len(ids)==64 else 'BAD')
            text=decode(vis);s,closed=seg(text)
            res[cell].setdefault('mine',{})[r['id']]=(ns,closed,s,a['finish_reason'])
    elif n.startswith('audit/') and n.endswith('SCORING_ROWS.json'):
        res[p[1]]['rows']={r['id']:r for r in json.load(tf.extractfile(m))}
    elif n.startswith('score/') and n.endswith('ALL_SCORED_ROWS.json'):
        res[p[1]]['score']={r['id']:r['score']['correct'] for r in json.load(tf.extractfile(m))}
    elif n.startswith('analysis/') and n.endswith('_FORCED_LABELS.json'):
        res[p[1].replace('_FORCED_LABELS.json','')]['joined']=json.load(tf.extractfile(m))
    elif n=='analysis/RESULTS.json':
        res['_']['results']=json.load(tf.extractfile(m))
pickle.dump(dict(res),open(sys.argv[2],'wb'))
for c,v in res.items():
    if c=='_':continue
    print(c,{k:len(x) for k,x in v.items()})
