import sys; pass  # numpy 2.5.4
import json, hashlib, numpy as np
D={k:sys.argv[i+1] for i,k in enumerate(['base4B','base9B','L','P','R','S2','S4','K4s','R8'])}  # nine unpacked evidence directories, in this order
def load(d):
    rows=[json.loads(l) for l in open(d+'/evaluation/score_v1/labels.jsonl')]
    return {r['id']:r for r in rows}
M={k:load(v) for k,v in D.items()}
IDS=sorted(M['L']); assert all(sorted(m)==IDS for m in M.values()) and len(IDS)==1572
V={k:np.array([float(m[i]['correct']) for i in IDS]) for k,m in M.items()}
U={k:np.array([float(m[i]['unfinished']) for i in IDS]) for k,m in M.items()}
def boot(delta):
    rng=np.random.Generator(np.random.PCG64(20261111)); s=np.empty(10000)
    for a in range(0,10000,128):
        b=min(a+128,10000); idx=rng.integers(0,len(delta),size=(b-a,len(delta))); s[a:b]=delta[idx].mean(axis=1)*100
    lo,hi=np.quantile(s,[.025,.975],method='linear'); return float(delta.mean()*100),float(lo),float(hi)
print('numpy',np.__version__)
out={'cells':{},'contrasts':{}}
for k in D:
    c=int(V[k].sum()); fin=(U[k]==0); out['cells'][k]=dict(correct=c,acc=round(c/15.72,2),unfinished_pct=round(U[k].mean()*100,2),finished_acc=round(V[k][fin].mean()*100,2))
    print('%-7s %4d %6.2f  unfinished %5.2f%%  finished acc %6.2f'%(k,c,c/15.72,U[k].mean()*100,V[k][fin].mean()*100))
C=[('S4','P'),('S2','S4'),('S4','L'),('K4s','R8'),('K4s','L'),('K4s','R'),('R8','L'),('R8','R'),('R','L'),('P','R'),('P','L'),('S2','P'),('P','K4s')]+[(k,'base4B') for k in ['L','P','S2','S4','K4s','R8','R']]
for a,b in C:
    d,lo,hi=boot(V[a]-V[b]); n10=int(((V[a]==1)&(V[b]==0)).sum()); n01=int(((V[a]==0)&(V[b]==1)).sum())
    out['contrasts'][f'{a}-{b}']=dict(d=round(d,2),lo=round(lo,2),hi=round(hi,2),only_a=n10,only_b=n01)
    print('%-12s %+6.2f [%+6.2f, %+6.2f]  only-first %3d only-second %3d'%(f'{a}-{b}',d,lo,hi,n10,n01))
json.dump(out,open('CLAUDE_CONTRASTS_s17.json','w'),indent=1)
