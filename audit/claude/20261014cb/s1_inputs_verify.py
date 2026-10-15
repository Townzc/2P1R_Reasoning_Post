import json,hashlib,sys,collections
sys.path.insert(0,'/tmp/claude-0/p9tools'); sys.path.insert(0,'/tmp/claude-0/s1i')
from qtok import build
from experiments.sft_allocation_midpoint.common import digest
enc,dec,_=build('/tmp/claude-0/p9/qwen_tok.json')
A='/tmp/claude-0/s1i/ar/'; I='/tmp/claude-0/s0a2/inputs/'; E='/tmp/claude-0/p1a/ev/original/'
train=[json.loads(l) for l in open(I+'math_train7500.jsonl')]
rows={r['id']:r for r in json.load(open(E+'ROWS.json'))}
sc={r['id']:r for r in json.load(open(E+'ALL_SCORED_ROWS.json'))}
first={}
for t in train: first.setdefault(t['question_sha256'],t['problem_id'])
byp={t['problem_id']:t for t in train}
elig=[]; reasons=collections.Counter()
for q,pid in first.items():
    cid=pid+'::attempt01'
    if cid not in rows:
        reasons['not_scored(ctx or unsupported)']+=1; continue
    r=rows[cid]; s=sc[cid]['score']
    if r['stop_reason']=='native_eos' and s['correct'] and s['parsed'] and s['teacher_label_eligible']:
        elig.append(pid)
    else: reasons['attempt1_not_ok']+=1
print('unique questions',len(first),'eligible',len(elig),dict(reasons))
inv=json.load(open(A+'ELIGIBLE_INVENTORY.json'))
print('inventory pids == mine (order)',[x['problem_id'] for x in inv['rows']]==elig)
bad=collections.Counter(); allenc={e['path_id']:e for e in json.load(open(A+'ALL_ENCODED.json'))}; lens={}; maxlen=0
for x in inv['rows']:
    pid=x['problem_id']; cid=pid+'::attempt01'
    if x['prompt']!=byp[pid]['problem']: bad['prompt']+=1
    if x['response']!=rows[cid]['answer_segment']: bad['response']+=1
    pre=f"Problem: {x['prompt']}\nSolution:\n"; pi=enc(pre); full=enc(pre+x['response'])
    if full[:len(pi)]!=pi: bad['boundary']+=1
    ids=full+[151643]; e=allenc[x['path_id']]
    if e['input_ids']!=ids: bad['ids']+=1
    if e['labels']!=[-100]*len(pi)+full[len(pi):]+[151643]: bad['labels']+=1
    if e['n_prompt']!=len(pi) or e['n_supervised']!=len(ids)-len(pi) or e['n_processed']!=len(ids): bad['counts']+=1
    if 151643 in full: bad['embedded_eos']+=1
    maxlen=max(maxlen,len(ids)); lens[x['path_id']]=len(ids)-len(pi)
print('tokenization issues',dict(bad),'max len',maxlen)
lv=json.load(open('/tmp/claude-0/s1i/experiments/../reports/p008_20261013/LR_VECTORS.json')) if False else None
for seed,sizes in ((17,(100,400,1600,3200)),(29,(400,3200))):
    order=sorted(elig,key=lambda p:hashlib.sha256(f'p009-stage1-question-order-v1:{seed}:{p}'.encode()).hexdigest())
    ro=json.load(open(A+f'ROSTER_s{seed}.json')); print('seed',seed,'order ok',ro['full_order']==order)
    prev=None
    for n in sizes:
        st=f's1_s{seed}_n{n}'; rr=json.load(open(A+st+'_rows.json')); ee=json.load(open(A+st+'_encoded.json')); pl=json.load(open(A+st+'_plan.json')); cf=json.load(open(A+st+'_config.json'))
        okp=[r['problem_id'] for r in rr]==order[:n]
        oke=[e['input_ids'] for e in ee]==[allenc[r['path_id']]['input_ids'] for r in rr]
        U=pl['updates']; ex=collections.Counter(i for u in U for i in u); tot=sum(ee[i]['n_supervised'] for u in U for i in u)
        s=sum(lens[r['path_id']] for r in rr)
        nest = prev is None or rr[:len(prev)]==prev
        print(f'  n{n}: prefix {okp} enc {oke} nested {nest} sum {s} updates {len(U)} empty {sum(not u for u in U)} targets {tot} exp {sorted(set(ex.values()))} q {pl["q"]} unexposed {n-len(ex)} rowexp {[ex[i] for i in range(n)]==pl["row_exposures"]} cfg {cf["encoded_rows_sha256"]==digest(ee) and cf["plan_sha256"]==digest(pl) and cf["training_rows_sha256"]==digest(rr)} lr {pl["lr_vector_sha256"][:8]} {cf["seed"]==seed and cf["setting"]=="S1" and cf["updates"]==1024 and cf["targets"]==2097148}')
        prev=rr
ep=json.load(open(A+'S1_ENDPOINT.json')); qz=json.load(open(I+'qwen_math_zero.json'))
print('endpoint',len(ep),[e['input_ids'] for e in ep]==[p['input_ids'] for p in qz['prompts']],[e['problem_id'] for e in ep]==[p['problem_id'] for p in qz['prompts']],
      all(e['source_row_sha256']==digest(dict(problem_id=e['problem_id'],input_ids=e['input_ids'])) for e in ep), all(e['candidate_id']=='S1::'+e['problem_id'] for e in ep))
