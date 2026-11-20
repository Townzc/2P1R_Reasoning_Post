import json,glob,sys,gzip,re,collections
sys.path.insert(0,'/tmp/claude-0/s0a2/pkg'); sys.path.insert(0,'/tmp/claude-0/p9tools')
from analyses.completion_contract import first_stop
from qtok import build
_,qdec,_=build('/tmp/claude-0/p9/qwen_tok.json')
tj=json.load(open('/tmp/claude-0/p9/qwen_tok.json')); SP={a['id'] for a in tj['added_tokens'] if a.get('special')}
R='/tmp/claude-0/s0a2'
rows=json.load(gzip.open('/tmp/claude-0/p1f/reports/p009_20261014/p1_first100_actual_v1/ROWS.json.gz'))
byid={r['id']:r for r in rows}
DS={'math_procurement':('teacher_p2_p3',[151645,151643],1024),'teacher_math_zero':('teacher_p2_p3',[151645,151643],1024),'qwen_math_zero':('qwen_p3',[151643],1024),'qwen_math_four':('qwen_p3',[151643],1024)}
bad=collections.Counter(); seen=0
for ds,(run,eos,cap) in DS.items():
    for f in sorted(glob.glob(f'{R}/ex/{run}/{ds}/raw/*.json')):
        for r in json.load(open(f)):
            cid=r['candidate_id']; row=byid.get(cid)
            if row is None: bad['missing_'+ds]+=1; continue
            seen+=1; ids=r['token_ids']
            native=next((t for t in ids if t in eos),eos[0])
            ev=first_stop(ids,qdec,native,cap,SP)
            if ev['stop_reason']!=row['stop_reason']: bad['stop']+=1
            if ev.get('answer_segment')!=row['answer_segment']: bad['segment']+=1
print('matched rows',seen,'of',len(rows),dict(bad))
