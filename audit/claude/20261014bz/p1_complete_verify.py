import json,glob,os,sys,re,hashlib,collections
R='/tmp/claude-0/p1a/ev/'
sys.path.insert(0,'/tmp/claude-0/p1a/reports/p009_20261014/p1_complete_scoring_v1/source')
from experiments.learning_regime_p009.math_scoring import decide, last_box
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
fsha=lambda p: hashlib.sha256(open(p,'rb').read()).hexdigest()
rows=json.load(open(R+'original/ROWS.json')); allrows=json.load(open(R+'original/ALL_SCORED_ROWS.json'))
coll=json.load(open('/tmp/claude-0/p1a/reports/p009_20261014/p1_complete_scoring_v1/COLLECTION.json'))
# originals hashes
bad=[k for k,v in coll['original_files'].items() if k not in coll['projected_intents'] and fsha(R+'original/'+k)!=v['sha256']]
print('original file hash mismatches',len(bad),'projected',len(coll['projected_intents']))
proj_ok=all(fsha(R+v['archive_member'])==v['projection_sha256'] for v in coll['projected_intents'].values()); print('projections hash ok',proj_ok)
# ROWS equals first100 packet rows (bx)
import gzip
bx=json.load(gzip.open('/tmp/claude-0/p1f/reports/p009_20261014/p1_first100_actual_v1/ROWS.json.gz'))
print('ROWS == bx-verified roster',rows==bx)
chunks=sorted(glob.glob(R+'original/journal/chunks/*'))
pos=0; merged=[]; issues=collections.Counter()
for i,c in enumerate(chunks):
    name=os.path.basename(c)
    ip=c+'/INTENT.json' if os.path.exists(c+'/INTENT.json') else R+'projected/journal/chunks/'+name+'/INTENT.json'
    it=json.load(open(ip)); res=json.load(open(c+'/RESULT.json')); comp=json.load(open(c+'/COMPLETED.json'))
    if it['start']!=pos or [r['id'] for r in rows[it['start']:it['end']]]!=[r['id'] for r in res['rows']]: issues['order']+=1
    if comp['result_sha256']!=fsha(c+'/RESULT.json') or comp['technical_unknown']!=0: issues['proof']+=1
    if ip.startswith(R+'original') and comp['intent_sha256']!=fsha(ip): issues['intent']+=1
    if not ip.startswith(R+'original') and comp['intent_sha256']!=coll['projected_intents']['journal/chunks/'+name+'/INTENT.json']['original_sha256']: issues['proj_orig']+=1
    merged+=res['rows']; pos=it['end']
print('chunks',len(chunks),'end',pos,'issues',dict(issues),'merged==ALL',merged==allrows)
pairs={}
for f in glob.glob(R+'original/journal/pairs/*.json'):
    r=json.load(open(f)); pairs[os.path.basename(f)[:-5]]=r
print('pairs',len(pairs),'statuses',collections.Counter(p['observation']['symbolic']['status'] for p in pairs.values()))
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
cnt=collections.defaultdict(collections.Counter); bad=collections.Counter(); fb=[]
for row,sc in zip(rows,allrows):
    s=sc['score']; ds=row['dataset']
    ans=mybox(row['answer_segment'])
    if row['stop_reason'] in('length_cap','invalid_special_token'):
        if sc['pair_id'] is not None or s['correct']: bad['cap']+=1
    elif not ans:
        if sc['pair_id'] is not None or s['correct']: bad['nobox']+=1
    else:
        p=pairs.get(sc['pair_id'])
        if p is None or p['pair']!=[row['gold'],ans]: bad['pair']+=1
        else:
            d=decide(row['gold'],{'answer':ans,'status':'box'},p['observation']['symbolic'],stop_reason=row['stop_reason'])
            if d['correct']!=s['correct']: bad['decide']+=1
    cnt[ds]['correct']+=s['correct']; cnt[ds]['caps']+=row['stop_reason']=='length_cap'; cnt[ds]['n']+=1
    if s.get('fallback_used'): fb.append((ds,row['id'],row['gold'],s.get('extracted_answer'),s['status'],s['correct']))
print('row consistency issues',dict(bad))
for k,v in cnt.items(): print(k,dict(v))
print('fallback rows'); [print(' ',x) for x in fb]
