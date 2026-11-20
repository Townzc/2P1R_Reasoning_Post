import sys,json,tarfile,hashlib,pickle,collections
from array import array
orig=pickle.load(open(sys.argv[1],'rb'));man=json.load(open(sys.argv[2]))
tf=tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz');seen=set()
for m in tf:
    if not m.name.endswith('/REQUESTS.json'): continue
    cell=m.name.split('/')[-2]; raw=tf.extractfile(m).read()
    h=hashlib.sha256(raw).hexdigest(); reqs=json.loads(raw); del raw
    cfg=man['cells'][cell]; bad=collections.Counter()
    exp={k[1] for k,v in orig['rows'].items() if k[0]==cell and v[0]}
    ids=[r['id'] for r in reqs]
    keys=collections.Counter()
    for r in reqs:
        keys.update(r.keys())
        o=orig['rows'][(cell,r['id'])]
        if hashlib.sha256(array('I',r['prompt_token_ids']).tobytes()).hexdigest()!=o[3]: bad['ids_mismatch']+=1
        if r['prompt_token_ids'][-10:]!=[198,522,26865,1339,19357,4226,25,1124,79075,90]: bad['suffix']+=1
    ctx=max(len(r['prompt_token_ids']) for r in reqs)+64 if reqs else None
    pre=sum(len(r['prompt_token_ids']) for r in reqs)
    print(cell,'n',len(reqs),'file_sha_ok',h==cfg['request_file_sha256'],'ids==manifest',ids==cfg['ids'],
          'set==expected',set(ids)==exp,'bad',dict(bad),'ctx',ctx,cfg['required_context'],'prefill',pre,cfg['prefill_tokens'],
          'keys',sorted(keys),flush=True)
    seen.add(cell)
print('cells',sorted(seen))
