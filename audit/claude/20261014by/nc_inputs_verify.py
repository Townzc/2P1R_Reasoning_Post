import json,hashlib,sys,collections
sys.path.insert(0,'/tmp/claude-0/p9tools')
from qtok import build
enc,dec,_=build('/tmp/claude-0/p9/qwen_tok.json')
A='/tmp/claude-0/nci/ar/'
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def dg(v): return hashlib.sha256(canon(v)).hexdigest()
inv=[json.loads(l) for l in open(A+'ORIGINAL_D1_INPUT.jsonl')]
pids=[r['problem_id'] for r in inv]; print('inventory',len(inv),'unique problems',len(set(pids)))
order=sorted(set(pids),key=lambda p:hashlib.sha256(f'p009-stage1-question-order-v1:17:{p}'.encode()).hexdigest())
roster=json.load(open(A+'ROSTER.json'))
print('full order matches',roster['full_order']==order, len(roster['full_order']))
byp={r['problem_id']:r for r in inv}
allenc=json.load(open(A+'ALL_ENCODED.json'))
# own tokenization of all 3436
bad=collections.Counter(); lens={}
encby={e['path_id']:e for e in allenc}
for r in inv:
    pre=f"Problem: {r['prompt']}\nSolution:\n"
    pi=enc(pre); full=enc(pre+r['response'])
    e=encby[r['path_id']]
    if full[:len(pi)]!=pi: bad['prompt_boundary']+=1
    ids=full+[151643]
    if e['input_ids']!=ids: bad['ids']+=1
    lab=[-100]*len(pi)+full[len(pi):]+[151643]
    if e['labels']!=lab: bad['labels']+=1
    if e['n_prompt']!=len(pi) or e['n_processed']!=len(ids) or e['n_supervised']!=len(ids)-len(pi): bad['counts']+=1
    if e['response_hash']!=hashlib.sha256(r['response'].encode()).hexdigest(): bad['hash']+=1
    if 151643 in full: bad['embedded_eos']+=1
    if len(ids)>2048: bad['len']+=1
    lens[r['path_id']]=len(ids)-len(pi)
print('own tokenization mismatches',dict(bad))
for n in (400,3200):
    rows=json.load(open(A+f'nc17_n{n}_rows.json')); encd=json.load(open(A+f'nc17_n{n}_encoded.json'))
    plan=json.load(open(A+f'nc17_n{n}_plan.json')); cfg=json.load(open(A+f'nc17_n{n}_config.json'))
    want=[byp[p] for p in order[:n]]
    print(n,'rows == hash-order prefix',rows==want,'encoded == own',[e['input_ids'] for e in encd]==[encby[r['path_id']]['input_ids'] for r in want])
    s=sum(lens[r['path_id']] for r in want); print('  whole-answer target sum',s)
    U=plan['updates']; ex=collections.Counter(i for u in U for i in u)
    tot=sum(encd[i]['n_supervised'] for u in U for i in u)
    print('  updates',len(U),'empty',sum(not u for u in U),'targets',tot,'exposures set',sorted(set(ex.values())),'q',plan['q'],'zero exposed',n-len(ex),
          'row_exposures ok',[ex[i] for i in range(n)]==plan['row_exposures'],'presentations',sum(ex.values()))
    lv=json.load(open('/tmp/claude-0/nci/reports/p008_20261013/LR_VECTORS.json'))
    v=lv.get('1024') if isinstance(lv,dict) else None
    print('  lrs == LR_VECTORS[1024]',plan['lrs']==v if v else list(lv)[:5], 'lr sha',hashlib.sha256(canon(plan['lrs'])).hexdigest()[:16],plan['lr_vector_sha256'][:16])
    print('  cfg digests',cfg['encoded_rows_sha256']==dg(encd),cfg['plan_sha256']==dg(plan),cfg['training_rows_sha256']==dg(rows), plan['encoded_rows_sha256']==dg(encd))
    if n==3200: r400=json.load(open(A+'nc17_n400_rows.json')); print('  nested',rows[:400]==r400)
# endpoint
ep=json.load(open(A+'NC_ENDPOINT.json')); par=json.load(open('/tmp/claude-0/s0a2/inputs/qwen_gsm_zero_parity.json'))
print('endpoint n',len(ep),'ids == Stage0 parity inputs',[e['input_ids'] for e in ep]==[p['input_ids'] for p in par['prompts']],
      'pids',[e['problem_id'] for e in ep]==[p['problem_id'] for p in par['prompts']],
      'source sha ok',all(e['source_row_sha256']==dg(dict(problem_id=e['problem_id'],input_ids=e['input_ids'])) for e in ep),
      'max prompt',max(len(e['input_ids']) for e in ep))
gsm=[json.loads(l) for l in open('/tmp/claude-0/s0a2/inputs/gsm8k_test1319.jsonl')]
own=[enc(f"Problem: {g.get('question') or g.get('prompt')}\nSolution:\n") for g in gsm]
print('endpoint == own encode of GSM test prefix', own==[e['input_ids'] for e in ep])
