"""Claude independent recompute of registered P008 contrasts from own G3 frozen vectors."""
import json, numpy as np
V=json.load(open('vectors19.json')); names=sorted(V); X=np.array([[int(c) for c in V[n]] for n in names],dtype=np.uint8)
idx={n:i for i,n in enumerate(names)}
def cell(d,b,p,pol,t=None): t=b if t is None else t; v=np.zeros(len(names)); v[idx[f'd{d}_b{b}_p{p}_{pol}_t{t}']]=1; return v
def D(d,b,p): return cell(d,b,p,'depth')-cell(d,b,p,'breadth')
C=[]
for d in (1,2):
    for b in (1,8):
        for p in (0,4): C.append((f'D{d}_Delta_p{p}_B{b}',D(d,b,p)))
    for p in (0,4): C.append((f'D{d}_C_p{p}',D(d,8,p)-D(d,1,p)))
    for b in (1,8): C.append((f'D{d}_I_B{b}',D(d,b,4)-D(d,b,0)))
    C.append((f'D{d}_I_high_minus_low',D(d,8,4)-D(d,8,0)-D(d,1,4)+D(d,1,0)))
for pol in ('breadth','depth'):
    C.append((f'D1_p0_{pol}_B8_minus_B1_at_T1',cell(1,8,0,pol,1)-cell(1,1,0,pol,1)))
    C.append((f'D1_p0_{pol}_T8_minus_T1_at_B8',cell(1,8,0,pol,8)-cell(1,8,0,pol,1)))
for i in range(9): C.append(('draw_mean_'+C[i][0].split('_',1)[1],(C[i][1]+C[i+9][1])/2))
W=np.array([c for _,c in C]); n=X.shape[1]
point=W@X.mean(1)*100
q=W@X.astype(float)*100
se=q.std(axis=1,ddof=0)/np.sqrt(n)
rng=np.random.default_rng(20261013); boot=np.empty((10000,len(C)))
for s in range(0,10000,100):
    S=rng.integers(0,n,size=(100,n)); boot[s:s+100]=(X[:,S].mean(axis=2).T)@W.T*100
lo,hi=np.quantile(boot,[.025,.975],axis=0,method='linear')
rng2=np.random.default_rng(7); b2=np.empty((4000,len(C)))
for s in range(0,4000,100):
    S=rng2.integers(0,n,size=(100,n)); b2[s:s+100]=(X[:,S].mean(axis=2).T)@W.T*100
lo2,hi2=np.quantile(b2,[.025,.975],axis=0)
json.dump([dict(name=nm,point=float(point[i]),lo=float(lo[i]),hi=float(hi[i]),lo_seed7=float(lo2[i]),hi_seed7=float(hi2[i]),se=float(se[i])) for i,(nm,_) in enumerate(C)],open('reg_mine.json','w'))
for i,(nm,_) in enumerate(C): print(f'{nm:42s} {point[i]:7.3f} [{lo[i]:7.3f},{hi[i]:7.3f}]  seed7[{lo2[i]:6.2f},{hi2[i]:6.2f}]  ±1.96se {1.96*se[i]:5.2f}')
