import json,sys,collections,hashlib
tok_path,raw_path,tr_path,out=sys.argv[1:5]
T=json.load(open(tok_path))
vocab=T['model']['vocab']; id2tok={v:k for k,v in vocab.items()}
for a in T['added_tokens']: id2tok[a['id']]=a['content']
special={a['id'] for a in T['added_tokens']}
# GPT-2 byte decoder
bs=list(range(ord('!'),ord('~')+1))+list(range(ord('¡'),ord('¬')+1))+list(range(ord('®'),ord('ÿ')+1))
cs=bs[:];n=0
for b in range(256):
    if b not in bs: bs.append(b);cs.append(256+n);n+=1
dec={chr(c):b for b,c in zip(bs,cs)}
def decode(ids):
    out=bytearray();parts=[]
    for i in ids:
        t=id2tok[i]
        if i in special:
            parts.append(out.decode('utf-8',errors='replace'));out=bytearray();parts.append(t)
        else: out.extend(dec[ch] for ch in t)
    parts.append(out.decode('utf-8',errors='replace'));return ''.join(parts)
raw=json.load(open(raw_path));tr=json.load(open(tr_path))
assert len(raw)==len(tr)==6400
NAT=(151645,151643);stats=collections.Counter();mism=[]
for r,d in zip(raw,tr):
    ids=r['token_ids'];sr=d['stop']['stop_reason'];stats[sr]+=1
    unm=[i for i,t in enumerate(ids) if t not in id2tok]
    if sr=='native_eos':
        e=next(i for i,t in enumerate(ids) if t in NAT); exp=decode(ids[:e]); 
        if unm: mism.append((r['candidate_id'],'unmapped native'))
    elif sr=='length_cap':
        exp=decode([t for t in ids if t in id2tok]) if unm else decode(ids)
        if not (len(ids)==1024 and r['finish_reason']=='length' and not any(t in NAT for t in ids)): mism.append((r['candidate_id'],'cap shape'))
    elif sr=='invalid_special_token':
        p=unm[0] if unm else None; exp=decode(ids[:p]) if p is not None else None
    else: exp=None; mism.append((r['candidate_id'],'stop '+sr))
    got=d['stop']['answer_segment']
    if exp is not None and got!=exp:
        if sr=='length_cap' and unm: stats['cap_unmapped_skip']+=1
        else: mism.append((r['candidate_id'],sr,len(got),len(exp or '')))
    if d['raw_record_sha256'] is None: mism.append((r['candidate_id'],'nohash'))
    stats['unmapped_rows']+=bool(unm)
json.dump(dict(stats=stats,mismatches=mism[:50],n_mismatch=len(mism)),open(out,'w'),indent=1)
print(dict(stats),len(mism),mism[:5])
