import json,gzip,glob,hashlib,os,sys,re
P='/tmp/claude-0/p1f/reports/p009_20261014/p1_first100_actual_v1'
sys.path.insert(0,P+'/source')
from experiments.learning_regime_p009.math_scoring_journal import pairs_for, digest, first100_forecast
from experiments.learning_regime_p009.math_scoring_pool import pair_digest
from experiments.learning_regime_p009.math_scoring import last_box
rows=json.load(gzip.open(P+'/ROWS.json.gz'))
basis=json.load(open(P+'/original/journal/BASIS.json'))
print('rows',len(rows),'basis rows sha ok',basis['ordered_rows_sha256']==digest(rows))
import collections
print(collections.Counter(r['dataset'] for r in rows))
# own last-box extractor (brace matching)
def mybox(s):
    out=None
    for m in re.finditer(r'\\(?:boxed|fbox)\s*\{',s):
        i=m.end(); d=1; j=i
        while j<len(s) and d:
            if s[j]=='{': d+=1
            elif s[j]=='}': d-=1
            j+=1
        if d==0: out=s[i:j-1].strip()
    return out
mism=sum((mybox(r['answer_segment']) or None)!=(last_box(r['answer_segment'])['answer'] or None) for r in rows)
print('own box extractor disagreements',mism)
pairs=pairs_for(rows)
print('distinct pairs total',len(pairs))
res=json.load(open(P+'/original/journal/chunks/00000/RESULT.json'))
print('result keys',list(res)[:10], 'rows',len(res['rows']))
obs={r['pair_id']:r['symbolic_attempt'] for r in res['rows'] if r['pair_id'] is not None}
files={os.path.basename(f)[:-5]:json.load(open(f)) for f in glob.glob(P+'/original/journal/pairs/*.json')}
print('observed',len(obs),'pair files',len(files),'same set',set(obs)==set(files))
bad=[k for k,v in files.items() if pair_digest(tuple(v['pair']))!=k or v['observation']!=obs.get(k)]
print('pair-file mismatches',len(bad))
first_ids=[r['id'] for r in res['rows']]==[r['id'] for r in rows[:100]]
print('first100 ordered ids',first_ids)
# pairs from first100 rows
p100=pairs_for(rows[:100]); print('pairs in first100 rows',len(p100),'== obs',set(p100)==set(obs))
el=[v['elapsed_seconds'] for v in obs.values()]
st=collections.Counter(v['symbolic']['status'] for v in obs.values())
print('max',max(el),'sum',sum(el),'status',dict(st))
rem=len(set(pairs)-set(obs)); print('remaining',rem)
t=json.load(open(P+'/original/journal/chunks/00000/TIMING.json'))
sc=t['elapsed_through_completed_proof_seconds']+1.2*(max(el)*rem+300); print('scenario',sc)
f=first100_forecast(basis,res,t,rows); prop=json.load(open(P+'/original/FIRST100_PROPOSAL.json'))
print('forecast fn == proposal', {k:(f[k],prop.get(k)) for k in f if f[k]!=prop.get(k)})
# stop reasons and pair eligibility
print('rows w/o pair:',collections.Counter(r['stop_reason'] for r in rows if not ((r['stop_reason'] in('native_eos','new_problem_boundary')) and last_box(r['answer_segment'])['answer'])))
# pairs per dataset share
