import json,sys,collections,hashlib
repo,inp,b6400,tokp,out=sys.argv[1:6]
sys.path.insert(0,repo)
from src.sft_data import prefix
from experiments.learning_regime_p009.training_plan import LR_VECTOR_SHA256,UPDATES,TARGETS
from experiments.sft_allocation_midpoint.common import digest
T=json.load(open(tokp));id2={v:k for k,v in T['model']['vocab'].items()}
for a in T['added_tokens']: id2[a['id']]=a['content']
sp={a['id'] for a in T['added_tokens']}
bs=list(range(33,127))+list(range(161,173))+list(range(174,256));cs=bs[:];n=0
for b in range(256):
    if b not in bs: bs.append(b);cs.append(256+n);n+=1
dec={chr(c):b for b,c in zip(bs,cs)}
def decode(ids):
    o=bytearray();parts=[]
    for i in ids:
        t=id2[i]
        if i in sp: parts.append(o.decode('utf-8','replace'));o=bytearray();parts.append(t)
        else:o.extend(dec[ch] for ch in t)
    parts.append(o.decode('utf-8','replace'));return ''.join(parts)
sel=json.load(open(repo+'/reports/p011_20261020/b_complete6400_actual_v1/SELECTION.json'))
srows={r['candidate_id']:r for r in json.load(open(b6400+'/audit/SCORING_ROWS.json'))}
raw={r['candidate_id']:r for r in json.load(open(b6400+'/audit/RAW_ORDERED.json'))}
res={}
for run,k in (('B1','1'),('B3','8'),('B2','4')):
    d=f'{inp}/b_runtime_student_inputs_r1/{run}'
    rows=json.load(open(d+'/rows.json'));enc=json.load(open(d+'/encoded.json'));plan=json.load(open(d+'/plan.json'));cfg=json.load(open(d+'/config.json'))
    bad=collections.Counter()
    if [r['path_id'] for r in rows]!=sel['selected_ids'][k]: bad['selected_ids']+=1
    for r,e in zip(rows,enc):
        s=srows[r['path_id']]
        if r['response']!=s['answer_segment']: bad['response_text']+=1
        if any(t not in id2 for t in raw[r['path_id']]['token_ids']): bad['unmapped_in_training']+=1
        if e['path_id']!=r['path_id']: bad['order']+=1
        ids,lab=e['input_ids'],e['labels']
        if ids[-1]!=151643 or 151643 in ids[:-1]: bad['eos']+=1
        if len(ids)>2048 or len(ids)!=e['n_processed']: bad['length']+=1
        if decode(ids[:-1])!=prefix(r['prompt'])+r['response']: bad['decode']+=1
        f=e['n_prompt']
        if lab[:f]!=[-100]*f or lab[f:]!=ids[f:]: bad['labels']+=1
        if decode(ids[:f])!=prefix(r['prompt']): bad['prompt_span']+=1
        if e['response_hash']!=hashlib.sha256(r['response'].encode()).hexdigest(): bad['hash']+=1
    exp=plan['row_exposures'];sup=[e['n_supervised'] for e in enc]
    tot=sum(x*y for x,y in zip(exp,sup))
    pres=collections.Counter(i for u in plan['updates'] for i in u)
    res[run]=dict(n=len(rows),P_cov=cfg['P_cov'],cfg_n=cfg['n'],bad=dict(bad),updates=len(plan['updates']),UPDATES=UPDATES,
        supervised_targets=plan['supervised_targets'],TARGETS=TARGETS,sum_exposure_x_supervised=tot,
        exposures_match_plan=all(pres[i]==exp[i] for i in range(len(enc))),min_exp=min(exp),max_exp=max(exp),
        lr_sha_ok=plan['lr_vector_sha256']==LR_VECTOR_SHA256==cfg['lr_vector_sha256'],seed=plan['seed'],
        fallback=cfg['unverified_fallback_questions'],unmapped=cfg['unmapped_training_rows'],
        max_len=max(len(e['input_ids']) for e in enc))
json.dump(res,open(out,'w'),indent=1);print(json.dumps(res,indent=1))
