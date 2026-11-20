import json, hashlib, sys, collections
import numpy as np
P=sys.argv[1]
man=json.load(open(f"{P}/manifest.json"))
for f,m in man['files'].items():
    b=open(f"{P}/{f}",'rb').read()
    print('sha',f, hashlib.sha256(b).hexdigest()==m['sha256'], len(b)==m['bytes'])
rows=[json.loads(l) for l in open(f"{P}/question_outcomes.jsonl")]
print('rows',len(rows))
by=collections.defaultdict(dict); dup=0
for r in rows:
    if r['question_id'] in by[r['run_id']]: dup+=1
    by[r['run_id']][r['question_id']]=r
print('dups',dup, {k:len(v) for k,v in by.items()})
qsets={k:frozenset(v) for k,v in by.items()}
print('same question set across runs', len(set(qsets.values()))==1)
for k in sorted(by):
    v=by[k].values()
    c=sum(r['correct'] for r in v); parsed=sum(r['parse_status']=='parsed' for r in v)
    bad=[r for r in v if r['correct'] and r['parse_status']!='parsed']
    stops=collections.Counter(r['stop_reason'] for r in v)
    steps=collections.Counter(r['checkpoint_step'] for r in v)
    unk=sum(r['correct'] is None for r in v)
    print(f"{k:14s} correct={c}/{len(by[k])} acc={c/len(by[k]):.4f} parsed={parsed} correct_but_unparsed={len(bad)} unknown={unk} steps={dict(steps)} stops={dict(stops)} meantok={np.mean([r['generated_tokens'] for r in v]):.1f}")
Q=sorted(qsets['base'])
def vec(run): return np.array([by[run][q]['correct'] for q in Q],dtype=float)
rng=np.random.default_rng(20261013)
B=10000; n=len(Q)
idx=rng.integers(0,n,size=(B,n))
for a,b in [('solutions','repeat'),('breadth','solutions'),('mixed','solutions'),('breadth','repeat'),('solutions','base')]:
    seeds=[17,23] if b!='base' else [17,23]
    ds=[]
    for s in seeds:
        va=vec(f"{a}_{s}"); vb=vec(f"{b}_{s}") if b!='base' else vec('base')
        ds.append(va-vb)
    d=np.mean(ds,axis=0)
    boot=d[idx].mean(axis=1)*100
    per=[(x.mean()*100, int((x>0).sum()), int((x<0).sum())) for x in ds]
    print(f"{a}-{b}: mean={d.mean()*100:.3f}pp CI=[{np.percentile(boot,2.5):.2f},{np.percentile(boot,97.5):.2f}] per-seed(diff,gained,lost)={[(round(p[0],3),p[1],p[2]) for p in per]}")
# seed agreement
for a in ['repeat','solutions','mixed','breadth']:
    x,y=vec(f"{a}_17"),vec(f"{a}_23")
    print(a,'seed17 vs 23: both',int(((x==1)&(y==1)).sum()),'only17',int(((x==1)&(y==0)).sum()),'only23',int(((x==0)&(y==1)).sum()))
