import sys; DATA=sys.argv[1]  # directory holding <task>/K8.jsonl of the frozen C6 data
import json, re, hashlib, random, collections, itertools, difflib
import numpy as np
def toks(s): return re.findall(r"[A-Za-z]+|\d+(?:\.\d+)?|\\[A-Za-z]+|[^\sA-Za-z\d]", s)
def ngr(t,n=4): return {tuple(t[i:i+n]) for i in range(len(t)-n+1)}
def nums(s): return re.findall(r"\d+(?:\.\d+)?", s)
out={}
for task in ['gsm8k','math']:
    rows=[json.loads(l) for l in open(f'{DATA}/{task}/K8.jsonl')]
    by=collections.defaultdict(list)
    for r in rows: by[r['parent_id']].append(r['solution'])
    assert len(by)==512 and all(len(v)==8 for v in by.values())
    T={p:[toks(s) for s in v] for p,v in by.items()}
    sim=[]; jac=[]; lenr=[]; exact=0; samenum=0; per_prob_min=[]; per_prob_max=[]
    for p,v in T.items():
        ps=[]
        for i,j in itertools.combinations(range(8),2):
            a,b=v[i],v[j]
            if by[p][i].strip()==by[p][j].strip(): exact+=1
            r=difflib.SequenceMatcher(None,a,b,autojunk=False).ratio(); ps.append(r); sim.append(r)
            A,B=ngr(a),ngr(b); jac.append(len(A&B)/max(1,len(A|B)))
            lenr.append(min(len(a),len(b))/max(len(a),len(b)))
            if nums(by[p][i])==nums(by[p][j]): samenum+=1
        per_prob_min.append(min(ps)); per_prob_max.append(max(ps))
    # baseline: solutions of different problems
    rng=random.Random(20261123); P=list(T); base=[]
    for _ in range(4000):
        p,q=rng.sample(P,2); base.append(difflib.SequenceMatcher(None,T[p][rng.randrange(8)],T[q][rng.randrange(8)],autojunk=False).ratio())
    sim=np.array(sim); jac=np.array(jac); n=len(sim)
    L=np.array([len(t) for v in T.values() for t in v])
    q=lambda x:[round(float(v),3) for v in np.quantile(x,[.1,.25,.5,.75,.9])]
    o=dict(problems=512,pairs=n,exact_duplicate_pairs=exact,
      token_similarity_quantiles_10_25_50_75_90=q(sim),token_similarity_mean=round(float(sim.mean()),3),
      pairs_similarity_ge_0p9=round(float((sim>=.9).mean()*100),2),pairs_similarity_ge_0p8=round(float((sim>=.8).mean()*100),2),pairs_similarity_lt_0p5=round(float((sim<.5).mean()*100),2),
      fourgram_jaccard_median=round(float(np.median(jac)),3),fourgram_jaccard_mean=round(float(jac.mean()),3),
      pairs_same_number_sequence_pct=round(samenum/n*100,2),
      problems_with_a_pair_ge_0p9_pct=round(float((np.array(per_prob_max)>=.9).mean()*100),2),
      baseline_different_problems_similarity_median=round(float(np.median(base)),3),
      solution_tokens_median=int(np.median(L)),length_ratio_median=round(float(np.median(lenr)),3))
    out[task]=o; print(task); [print('  ',k,v) for k,v in o.items()]
json.dump(out,open('DIVERSITY_K8.json','w'),indent=1)
