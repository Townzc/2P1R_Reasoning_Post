import json,sys,hashlib,subprocess,collections
sys.path.insert(0,'.')
P='reports/exploratory_20261014/admission_v1'
I=P+'/inputs'
tj=json.load(open(I+'/instruct_model/tokenizer.json'))
vocab=tj['model']['vocab']; inv={v:k for k,v in vocab.items()}
for a in tj['added_tokens']: inv[a['id']]=a['content']
special={a['id'] for a in tj['added_tokens']}
bs=list(range(ord("!"),ord("~")+1))+list(range(ord("¡"),ord("¬")+1))+list(range(ord("®"),ord("ÿ")+1));cs=bs[:];n=0
for b in range(256):
    if b not in bs: bs.append(b);cs.append(256+n);n+=1
bdec={chr(c):b for b,c in zip(bs,cs)}
def dec(ids):
    out=bytearray()
    for i in ids:
        t=inv[i]
        if i in special: out+=t.encode()
        else: out+=bytes(bdec[ch] for ch in t)
    return out.decode('utf-8')
test=[json.loads(l) for l in open(I+'/gsm8k_test1319.jsonl')]
ex=json.load(open(I+'/dev_examples.json'))
pre=lambda x:f"Problem: {x}\nSolution:\n"
SYS=r'Please reason step by step, and put your final answer within \boxed{}.'
fs=''.join(pre(e['problem'])+e['reference']+'\n\n' for e in ex)
res={}
for name,exp in [('base_4shot',lambda r:fs+pre(r['prompt'])),('wrong_teacher_t1',lambda r:pre(r['prompt'])),
                 ('instruct_0shot',lambda r:f"<|im_start|>system\n{SYS}<|im_end|>\n<|im_start|>user\n{r['prompt']}<|im_end|>\n<|im_start|>assistant\n")]:
    d=json.load(open(I+f'/{name}_prompts.json'))
    ok=len(d)==1319 and all(x['problem_id']==t['problem_id'] for x,t in zip(d,test))
    bad=[t['problem_id'] for x,t in zip(d,test) if dec(x['input_ids'])!=exp(t)]
    L=[len(x['input_ids']) for x in d]
    res[name]=dict(order_ok=ok,decode_mismatch=len(bad),first_bad=bad[:2],len=[min(L),max(L)],fits=max(L)+512<=2048,
                   any_eos_in_prompt=any(i in (151643,151645) for x in d for i in x['input_ids']))
print(json.dumps(res,indent=1))
# leakage: does any test question text appear in the 4-shot demos? does any gold test answer appear in prompts? (selection only)
print('demo ids in test',set(e['id'] for e in ex)&{t['problem_id'] for t in test})
# plan checks
plan=json.load(open(I+'/wrong_teacher_t1_plan.json'))
rows=[json.loads(l) for l in open(I+'/wrong_teacher.jsonl')]
from experiments.sft_allocation_p008.schedule import schedule
ns=[r['source']['n_supervised'] for r in rows]
p2=schedule(ns,524287,256,17)
print('schedule reproduces',all(p2[k]==plan[k] for k in p2), [k for k in p2 if p2[k]!=plan.get(k)])
tot=sum(ns[i] for u in plan['updates'] for i in u); print('targets sum',tot, 'updates',len(plan['updates']))
ctrl=json.loads(subprocess.run(['git','-C','/home/claude/2P1R_Reasoning_Post','show','32c473d6:reports/p008_20261013/student_admission_v1/inputs/d1_b1_p0_breadth_t1_plan.json'],capture_output=True).stdout or b'null')
print('control plan found',ctrl is not None, 'lrs equal' if ctrl and ctrl['lrs']==plan['lrs'] else 'lrs ?')
print('row_path_ids == selection order', plan['row_path_ids']==json.load(open('/tmp/claude-0/aud_c/sel_ids.json')))
print('exposures',collections.Counter(plan['row_exposures']), 'q',plan['q'])
# responses equal original pool text
pool={}
import glob
for f in glob.glob('/home/claude/2P1R_Reasoning_Post/reports/p008_20261013/pool_d1_v1/physical_batches/*_scored.json'):
    for r in json.load(open(f)): pool[r['candidate_id']]=r
print('responses equal pool text',all(r['response']==pool[r['path_id']]['text'] and r['answer']!=pool[r['path_id']]['score']['value'] for r in rows))
print('response decode==text', sum(dec(pool[r['path_id']]['stop']['text_token_ids'])==r['response'] for r in rows), '/429')
