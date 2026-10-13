"""Reproduce round7 contrasts from immutable compact scores; no model calls."""
from pathlib import Path
import json
import numpy as np

path=Path(__file__).resolve().parent.parent/'token_seed17_two_prices_v1/paired_question_scores.json'
rows=json.loads(path.read_text())
assert len(rows)==1319 and [r['problem_id'] for r in rows]==sorted({r['problem_id'] for r in rows})
columns=['breadth_p0','depth_p0','breadth_p4','depth_p4']
a=np.array([[int(r[k]) for k in columns] for r in rows])
assert a.sum(axis=0).tolist()==[963,950,927,952]
d=np.stack([a[:,1]-a[:,0],a[:,3]-a[:,2],a[:,3]-a[:,2]-a[:,1]+a[:,0],a[:,2]-a[:,0],a[:,3]-a[:,1]],axis=1)
rng=np.random.default_rng(20261013)
bootstrap=np.array([d[rng.integers(0,1319,size=1319)].mean(axis=0)*100 for _ in range(10000)])
names=['p0_depth_minus_breadth','p4_depth_minus_breadth','price_interaction_p4_minus_p0','supplementary_breadth_p4_minus_p0','supplementary_depth_p4_minus_p0']
print(json.dumps({name:dict(difference_pp=float(d[:,i].mean()*100),conditional_question_bootstrap_95_pp=np.quantile(bootstrap[:,i],[.025,.975]).tolist(),posthoc_supplementary=i>=3) for i,name in enumerate(names)},indent=2))
