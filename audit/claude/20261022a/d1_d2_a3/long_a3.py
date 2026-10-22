import json,sys,collections,hashlib,re,glob,os
tok,rawdir,rows_p,comp_p,key,out=sys.argv[1:7]
T=json.load(open(tok)); vocab=T['model']['vocab']; id2tok={v:k for k,v in vocab.items()}
for a in T['added_tokens']: id2tok[a['id']]=a['content']
special={a['id'] for a in T['added_tokens']}
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
NAT=(151645,151643)
H=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
raw={}
for f in sorted(glob.glob(rawdir+'/eval_*.json')):
    for r in json.load(open(f)): raw[r['id']]=r
rows=json.load(open(rows_p)); comp=json.load(open(comp_p))[key]['endpoints']
def lastbox(s):
    i=s.rfind('\\boxed{')
    if i<0: return None
    j=i+7;d=1
    while j<len(s) and d:
        d+= (s[j]=='{')-(s[j]=='}'); j+=1
    return s[i+7:j-1] if d==0 else None
def norm(x):
    if x is None: return None
    x=re.sub(r'\\left|\\right|\\!|\\,|\;|\\ |\s|\$','',x).replace('dfrac','frac').replace('tfrac','frac')
    x=re.sub(r'\\text\{(.*?)\}',r'\1',x); return x.rstrip('.')
def label(rid):
    b,q,mode,seed=rid.split(':'); key=b+'_'+mode
    v=comp[key]['question_correct'][b+':'+q]; return v[0] if mode=='greedy' else v[int(seed)]
st=collections.Counter(); mism=[]; symb=[]; strfalse=[]; per=collections.defaultdict(collections.Counter); toks=collections.defaultdict(list)
for row in rows:
    r=raw[row['id']]; a=r['answers'][0]; ids=a['token_ids']
    unm=[t for t in ids if t not in id2tok]
    if ids and ids[-1] in NAT and not any(t in NAT for t in ids[:-1]): sr='native_eos'; body=ids[:-1]
    elif len(ids)==16384 and a['finish_reason']=='length' and not any(t in NAT for t in ids): sr='length_cap'; body=ids
    else: sr='other'; body=ids
    if unm: st['unmapped']+=1; body=[t for t in body if t in id2tok]
    text=decode(body)
    if H(text)!=row['raw_text_sha256']: st['text_sha_mismatch']+=1
    region=text[text.rfind('</think>')+8:] if '</think>' in text else text
    if H(region)!=row['region_sha256']: st['region_sha_mismatch']+=1
    if sr!=row['stop_reason']: mism.append((row['id'],'stop',sr,row['stop_reason']))
    b=row['id'].split(':')[0]+'_'+row['id'].split(':')[2]; per[b][sr]+=1; toks[b].append(len(ids))
    lab=label(row['id']); per[b]['correct']+=lab
    box=lastbox(region) if sr=='native_eos' else None
    eq = box is not None and norm(box)==norm(row['gold'])
    if sr!='native_eos' and lab: mism.append((row['id'],'truncated_but_true'))
    if eq and not lab: strfalse.append((row['id'],box,row['gold']))
    if lab and not eq: symb.append((row['id'],box,row['gold']))
    st['rows']+=1
res=dict(stats=st,per_endpoint={k:dict(v,n=sum(v[s] for s in ('native_eos','length_cap','other')),mean_tokens=sum(toks[k])/len(toks[k])) for k,v in per.items()},
  mismatches=mism,string_equal_but_scored_false=strfalse,true_without_string_equality=symb)
json.dump(res,open(out,'w'),indent=1,default=str)
print(dict(st)); [print(k,v) for k,v in res['per_endpoint'].items()]; print('mism',len(mism),mism[:5]); print('strfalse',len(strfalse),strfalse[:5]); print('symb',len(symb))
