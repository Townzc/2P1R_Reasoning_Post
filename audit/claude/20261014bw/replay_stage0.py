import json,glob,os,sys,collections
R='/tmp/claude-0/s0a2'
sys.path.insert(0,R+'/pkg')
from analyses.completion_contract import first_stop, completion_score
sys.path.insert(0,'/tmp/claude-0/p9tools')
from qtok import build
_,qdec,qadd=build('/tmp/claude-0/p9/qwen_tok.json')
_,odec,oadd=build('/tmp/claude-0/sup/olmo/tokenizer.json',nfc=False)
def specials(path):
    tj=json.load(open(path)); return {a['id'] for a in tj['added_tokens'] if a.get('special')}, len(tj['model']['vocab'])+0
QS,_=specials('/tmp/claude-0/p9/qwen_tok.json'); OS,_=specials('/tmp/claude-0/sup/olmo/tokenizer.json')
M={'teacher':dict(eos=[151645,151643],vocab=151936,dec=qdec,sp=QS,tokdefault=151645),
   'qwen':dict(eos=[151643],vocab=151936,dec=qdec,sp=QS,tokdefault=151643),
   'olmo':dict(eos=[100257],vocab=100352,dec=odec,sp=OS,tokdefault=100257)}
DS={'math_procurement':('teacher_p2_p3','teacher',1024,True),'teacher_gsm_zero':('teacher_p2_p3','teacher',512,False),
 'teacher_math_zero':('teacher_p2_p3','teacher',1024,False),'qwen_math_zero':('qwen_p3','qwen',1024,False),
 'qwen_math_four':('qwen_p3','qwen',1024,False),'olmo_gsm_zero':('olmo_p3','olmo',512,False),'olmo_gsm_four':('olmo_p3','olmo',512,False)}
gsm={json.loads(l)['problem_id']:json.loads(l) for l in open(R+'/inputs/gsm8k_test1319.jsonl')}
def expected(name):
    run,model,cap,proc=DS[name]
    if proc:
        rows=[json.loads(l) for l in open(R+'/inputs/math_teacher_requests8993.jsonl')]
        return [(r['candidate_id'],r['problem_id'],r['seed'],r['prompt_token_ids']) for r in rows]
    d=json.load(open(R+f'/inputs/{name}.json'))
    assert d['n']==len(d['prompts']) and d['max_new_tokens']==cap and d['max_context']==2048
    return [(name+'::'+p['problem_id'],p['problem_id'],17,p['input_ids']) for p in d['prompts']]
out={}
for name,(run,model,cap,proc) in DS.items():
    m=M[model]; exp=expected(name)
    raws=[]
    for f in sorted(glob.glob(f'{R}/ex/{run}/{name}/raw/*.json')): raws+=json.load(open(f))
    bad=collections.Counter(); stops=collections.Counter(); backend=collections.Counter(); correct=0; lens=[]
    if len(raws)!=len(exp): bad['count']+=1
    seen=set(); distinct=collections.defaultdict(set)
    for (cid,pid,seed,prompt),r in zip(exp,raws):
        if r['candidate_id']!=cid or r['problem_id']!=pid: bad['identity']+=1
        if cid in seen: bad['dup']+=1
        seen.add(cid)
        if r['prompt_token_ids']!=prompt: bad['prompt']+=1
        s=r['sampling']
        want=dict(n=1,temperature=0.8 if proc else 0,top_p=0.95 if proc else 1,top_k=-1,repetition_penalty=1,max_tokens=cap,seed=seed,stop=None,stop_token_ids=m['eos'],ignore_eos=False,detokenize=True,skip_special_tokens=False,include_stop_str_in_output=True)
        if s!=want: bad['sampling']+=1
        ids=r['token_ids']
        if not ids or len(ids)>cap or any(not (0<=t<m['vocab']) for t in ids): bad['ids']+=1
        if len(prompt)+cap>2048: bad['context']+=1
        pos=[i for i,t in enumerate(ids) if t in m['eos']]
        if pos and pos!=[len(ids)-1]: bad['eos_interior']+=1
        if not pos and (len(ids)!=cap or r['finish_reason']!='length'): bad['short_no_eos']+=1
        if pos and r['finish_reason']=='length' and len(ids)!=cap: bad['length_meta']+=1
        backend[r['finish_reason']]+=1
        native=next((t for t in ids if t in m['eos']),m['tokdefault'])
        ev=first_stop(ids,lambda x:m['dec'](x),native,cap,m['sp'])
        stops[ev['stop_reason']]+=1; lens.append(len(ids))
        if proc: distinct[pid].add(tuple(ids))
        if name.endswith('gsm_zero') or name.endswith('gsm_four'):
            sc=completion_score(gsm[pid],ev); correct+=bool(sc['task_answer_correct'])
    o=dict(n=len(raws),problems=dict(bad),logical=dict(stops),backend=dict(backend),mean_len=round(sum(lens)/len(lens),1))
    if 'gsm' in name: o['correct']=correct
    if proc:
        multi=[p for p,v in distinct.items() if len(v)>0]
        reps=collections.Counter(len([c for c in exp if c[1]==p]) for p in distinct)
        dup=sum(1 for p,v in distinct.items() if len(v)<len([1 for c in exp if c[1]==p]))
        o['problems_with_repeat_identical_outputs']=dup; o['attempts_per_problem']=dict(reps)
    out[name]=o; print(name,json.dumps(o),flush=True)
json.dump(out,open(R+'/replay_out.json','w'),indent=1)
