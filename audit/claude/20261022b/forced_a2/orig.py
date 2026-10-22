import sys,json,tarfile,hashlib,re,pickle
from array import array
TK=json.load(open(sys.argv[1])); out=sys.argv[2]
specials={t['id'] for t in TK['added_tokens'] if t.get('special')}
SUF=[198,522,26865,1339,19357,4226,25,1124,79075,90]
JOB={'long_baseline_S-L15_s17_owner_r1':'baseline','long_A1_S-F15_s17_owner_r2':'A1r2','long_A5_S-F15_s17_owner_r1':'A5','long_A6_S-F15_s17_owner_r1':'A6','long_A7_S-F15_s17_owner_r1':'A7','long_D1_S-F15_s17_owner_r1':'D1','long_D2_S-F15_s17_owner_r1':'D2'}
try: res=pickle.load(open(out,'rb'))
except Exception: res={'rows':{},'meta':{}}
tf=tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz')
for m in tf:
    n=m.name
    if not m.isfile(): continue
    cell=next((c for j,c in JOB.items() if j in n),None)
    if 'D2' in sys.argv[3] and cell is None and '/raw/eval_' in n: cell='D2'
    if cell is None: continue
    if re.search(r'(MODEL|EXPORT|model_files|export)',n,re.I) and m.size<2_000_000:
        res['meta'][n]=tf.extractfile(m).read().decode('utf-8','replace'); continue
    if '/raw/eval_' not in n or not n.endswith('.json'): continue
    if cell in ('D1','D2') and cell not in sys.argv[3]: continue
    rows=json.load(tf.extractfile(m))
    for r in rows:
        if not r['id'].startswith('math500:'): continue
        a=r['answers'][0]; g=a['token_ids']
        trunc = a['finish_reason']=='length' and len(g)==16384 and not any(t in specials for t in g)
        h=hashlib.sha256(array('I',r['prompt_token_ids']+g+SUF).tobytes()).hexdigest()
        key=(cell,r['id'])
        if key in res['rows']: raise SystemExit('dup '+str(key))
        res['rows'][key]=(trunc,a['finish_reason'],len(g),h,len(r['prompt_token_ids'])+len(g)+len(SUF))
    print(cell,n,len(rows),file=sys.stderr)
pickle.dump(res,open(out,'wb'))
