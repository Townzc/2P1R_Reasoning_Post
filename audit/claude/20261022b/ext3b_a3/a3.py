import json,sys,tarfile,hashlib,zlib,pickle,collections
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
H=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False,ensure_ascii=False).encode()).hexdigest()
H2=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def lastbox(t):
    i=t.rfind('\\boxed{')
    if i<0: return None
    j=i+7;d=1;k=j
    while k<len(t) and d: d+=(t[k]=='{')-(t[k]=='}');k+=1
    return t[j:k-1] if d==0 else None
R=collections.defaultdict(dict)
tf=tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz')
for m in tf:
    if not m.isfile(): continue
    n=m.name;cell=n.split('/')[0].replace('_attempt1','')
    if '/runtime/raw/eval_' in n:
        for r in json.load(tf.extractfile(m)):
            a=r['answers'][0];ids=a['token_ids']
            st=next(((i,'native_eos' if t in EOS else 'invalid_special_token') for i,t in enumerate(ids) if t in EOS or t in special),None)
            vis=ids[:st[0]] if st else ids;stop=st[1] if st else ('length_cap' if len(ids)==16384 else 'BAD')
            text=decode(vis);region=text[text.rfind('</think>')+8:] if '</think>' in text else text
            tail=a['backend_text'][-6000:].encode();loop=(len(zlib.compress(tail))/len(tail)<0.12) if tail else False
            R[cell].setdefault('mine',{})[r['id']]=dict(stop=stop,ntok=len(ids),h=(H(text),H2(text)),hr=(H(region),H2(region)),box=lastbox(region),loop=loop)
    elif n.endswith('/audit/SCORING_ROWS.json'):
        R[cell]['rows']={r['id']:r for r in json.load(tf.extractfile(m))}
    elif n.endswith('ALL_SCORED_ROWS.json'):
        R[cell]['score']={r['id']:r['score']['correct'] for r in json.load(tf.extractfile(m))}
    elif n=='analysis/COMPLETED.json':
        R['_']['analysis']=json.load(tf.extractfile(m))
pickle.dump(dict(R),open(sys.argv[2],'wb'))
for c,v in R.items(): print(c,{k:len(x) for k,x in v.items()})
