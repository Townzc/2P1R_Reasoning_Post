import json,sys,glob,hashlib,collections,os
sys.path.insert(0,'/tmp/claude-0/s1r'); sys.path.insert(0,'/tmp/claude-0/p9tools')
from analyses.completion_contract import first_stop
import experiments.learning_regime_p009.math_scoring as ms
from qtok import build
enc,dec,_=build('/tmp/claude-0/p9/qwen_tok.json')
tj=json.load(open('/tmp/claude-0/p9/qwen_tok.json')); special=tuple(a['id'] for a in tj['added_tokens'] if a.get('special'))
gold={json.loads(l)['problem_id']:json.loads(l)['answer'] for l in open('/tmp/claude-0/s0a2/inputs/math500.jsonl')}
ep=json.load(open('/tmp/claude-0/s1i/ar/S1_ENDPOINT.json')); ids=[e['problem_id'] for e in ep]
res={}; flagged={}
for run in ('s1_s17_n400','s1_s17_n3200'):
    B='/tmp/claude-0/fp/'+run+'/'; bad=collections.Counter()
    dec_rows={d['problem_id']:d for d in json.load(open(B+'orc/DECODED_ROWS.json'))}
    srows={d['problem_id']:d for d in json.load(open(B+'orc/SCORING_ROWS.json'))}
    pairs={}
    for f in glob.glob(B+'sc/job/payload/pairs/*.json'):
        p=json.load(open(f)); pairs[tuple(p['pair'])]=p['observation']['symbolic']
    orc=json.load(open(B+'sc/LOCAL_ORACLE_AUDIT.json'))
    mine={}; stops=collections.Counter(); flags=[]
    for off in (0,256):
        raw=json.load(open(B+f'gen/endpoint/raw/{off:05d}.json'))
        if [r['problem_id'] for r in raw]!=ids[off:off+256]: bad['order']+=1
        for row,item in zip(ep[off:off+256],raw):
            pid=row['problem_id']
            if item['prompt_token_ids']!=row['input_ids']: bad['prompt']+=1
            ev=first_stop(item['token_ids'],dec,151643,1024,special)
            if ev!=dec_rows[pid]['stop']: bad['event']+=1
            if srows[pid]['gold']!=gold[pid]: bad['gold']+=1
            if srows[pid]['answer_segment']!=ev['answer_segment']: bad['segment']+=1
            stops[ev['stop_reason']]+=1
            ex=ms.last_box(ev['answer_segment'])
            if ev['stop_reason'] in ('length_cap','invalid_special_token') or not ex['answer']:
                d=ms.decide(gold[pid],ex,{},stop_reason=ev['stop_reason'])
            else:
                sym=pairs.get((gold[pid],ex['answer']))
                if sym is None: bad['missing_pair']+=1; continue
                d=ms.decide(gold[pid],ex,sym,stop_reason=ev['stop_reason'])
                if sym['status']!='compared' or d['string_symbolic_disagreement']:
                    flags.append(dict(pid=pid,gold=gold[pid],ans=ex['answer'],sym=sym,str_eq=d['normalized_string_equal'],correct=d['correct']))
            mine[pid]=d['correct']
    agree=mine==orc['question_correct']
    print(run,'rows',len(mine),'correct',sum(mine.values()),'oracle',orc['correct'],'agree',agree,'stops',dict(stops),'issues',dict(bad),'flagged',len(flags))
    # dose
    plan=json.load(open(f'/tmp/claude-0/s1i/ar/{run}_plan.json')); encd=json.load(open(f'/tmp/claude-0/s1i/ar/{run}_encoded.json'))
    t=pp=0; dm=0
    for step,idx in enumerate(plan['updates'],1):
        d=json.load(open(B+f'gen/completed/update_{step:04d}.json')); a=json.load(open(B+f'gen/intents/update_{step:04d}.json'))
        st=sum(encd[i]['n_supervised'] for i in idx); pr=sum(encd[i]['n_processed'] for i in idx); t+=st; pp+=pr
        w=dict(step=step,indices=idx,lr=plan['lrs'][step-1],supervised_tokens=st,processed_tokens=pr)
        if a!=w or any(d.get(k)!=v for k,v in w.items()) or d['cumulative_targets']!=t or d['cumulative_processed']!=pp: dm+=1
    names={os.path.basename(f)[:-5] for f in glob.glob(B+'gen/completed/*.json')}
    mp=json.load(open(B+'gen/MERGE_PROOF.json')); pe=json.load(open(B+'gen/TRAINING_PROCESS_EXITED.json'))
    print('  dose mismatches',dm,'targets',t,'units',len(names),'merge',mp['merge_dtype'],mp['saved_dtype'],mp['optimizer_updates_after_terminal_save'],'exit',pe['exitcode'],pe['joined_before_endpoint'])
    res[run]=mine; flagged[run]=flags
lo,hi=res['s1_s17_n400'],res['s1_s17_n3200']
d=sum(hi[i] for i in ids)-sum(lo[i] for i in ids)
print('PAIR',sum(lo.values()),sum(hi.values()),'delta',d,'discordant',sum(lo[i]!=hi[i] for i in ids),'futility stop?',100*d<2*500)
json.dump(flagged,open('/tmp/claude-0/fp/flagged.json','w'),ensure_ascii=False,indent=1)
