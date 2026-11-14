import copy,datetime,json,subprocess
from a7_ops import *

FAIL=PUBLIC/'infrastructure_interruption_8a_v1/FAILURES.json'

def retry_admission(name):
    record=next(x for x in read(FAIL)['components'] if x['run_id']==name)
    old=Path(record['archive_directory']);r=read(old/'request.json')
    assert sha(old/'request.json')==record['request_sha256'] and not r.get('infrastructure_retry')
    d=Path(record['original_directory']);assert not d.exists()
    pub=PUBLIC/('recovery_8a_'+name);assert not pub.exists()
    # A7 greedy remains reserved by its completed training request. A6 originals
    # moved to the failure archive, so re-admission reserves training plus greedy.
    amount=0 if r['mode']=='generate' else r['cpu_counts']['full_training_input_tokens']*r['prices_per_million']['train']/1e6*1.25+.1+r['forecast']['reserved_greedy_usd']
    with lock('BUDGET_ADMISSION.lock'):
        snap=accounting()
        key='A7_accounted_and_reserved_usd' if record['group']=='A7' else 'A6_3_accounted_and_reserved_usd'
        cap=60 if record['group']=='A7' else 35
        assert snap[key]+amount<=cap and snap['combined_reserved_usd']+amount<=485,('retry budget gate',key,snap[key],amount)
        pub.mkdir();(pub/'requests').mkdir();d.mkdir()
        admission=dict(snap,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),run_id=name,
            retry_attempt=1,group=record['group'],additional_buffered_usd=amount,
            group_next_usd=snap[key]+amount,combined_next_usd=snap['combined_reserved_usd']+amount,
            failure_ledger_sha256=sha(FAIL),admitted=True,scientific_configuration_unchanged=True)
        (pub/'ADMISSION.json').write_text(json.dumps(admission,indent=2)+'\n')
        original=copy.deepcopy(r)
        r['code_commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        r['forecast'].update(admitted=True,admission_file=str(pub/'ADMISSION.json'),admission_sha256=sha(pub/'ADMISSION.json'))
        r['infrastructure_retry']={'attempt':1,'maximum':1,'original_request_sha256':record['request_sha256'],
            'original_evidence_archive':record['evidence_archive'],'original_evidence_sha256':record['evidence_archive_sha256'],
            'failure_cost_upper_usd':record['usd'],'failure_ledger_sha256':sha(FAIL)}
        ignore={'code_commit','forecast','infrastructure_retry'}
        assert {k:v for k,v in r.items() if k not in ignore}=={k:v for k,v in original.items() if k not in ignore}
        data=json.dumps(r,indent=2)+'\n';assert '/Users/' not in data
        (d/'request.json').write_text(data);(pub/'requests'/(name+'.json')).write_text(data)
        if (old/'request_pending.json').exists():(d/'request_pending.json').write_bytes((old/'request_pending.json').read_bytes())
        (pub/'README.md').write_text('# One authorized infrastructure retry\n\nThe original incomplete attempt is archived and its cost remains charged. Model,data,seed,rank,learning rate,dose,renderer,scorer and model-runner source are identical. The retry uses a fresh output directory and one independent process session. No completed model call is replayed. The original category cap and combined cap pass including failure costs.\n')
        commit=publish([pub],'P012: admit one infrastructure retry '+name)
    return d,pub/'requests'/(name+'.json'),commit

def start_any(d,public_request,event,children):
    assert not (d/'run.log').exists() and not (d/'result').exists()
    r=read(d/'request.json');assert r['forecast']['admitted'] and r['source_sha256']==sha('experiments/p012/tinker_lora.py')
    assert sha(r['forecast']['admission_file'])==r['forecast']['admission_sha256']
    assert public_request.read_bytes()==(d/'request.json').read_bytes()==subprocess.check_output(['git','show','HEAD:'+str(public_request)])
    with (d/'run.log').open('x') as f:
        p=subprocess.Popen([TINKER_PY,str(ROOT/'amendment4_v1/launch_tinker_private.py'),str(d)],env=ENV,
            stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    children[d.name]=p;event('launched',run_id=d.name,pid=p.pid,independent_process_session=True,request_sha256=sha(d/'request.json'))
