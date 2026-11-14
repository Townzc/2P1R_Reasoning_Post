"""Finite T-GSM pretraining sampling queue; unchanged reviewed scientific tools."""
from pathlib import Path
import datetime,json,os,subprocess,sys,time,traceback,zipfile
sys.path.insert(0,'.local/p012_20261111/amendment7_v1')
from a7_ops import ROOT,PUBLIC,PY,TINKER_PY,ENV,lock,publish,read,sha

META=ROOT/'t_gsm_v1';ADMISSION=PUBLIC/'tinker_gsm_pre_admission_v1'
STATE=META/'PRE_SAMPLING_QUEUE.json';assert not STATE.exists()
state={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'controller_pid':os.getpid(),
       'status':'running','events':[],'scope':'Five greedy baselines then three existing independent-seed pass8 endpoints. NLL waits for storage disposition; no training checkpoint is created here.'}
children={};manifest=read(ADMISSION/'ADMISSION.json')
names=[x['run_id'] for x in manifest['endpoints'] if x['endpoint'] not in ['nll','holdout8']]
samples=[next(x['run_id'] for x in manifest['endpoints'] if x['endpoint']=='holdout8' and x['key']==m) for m in ['9b_base','9b','4b']]
frozen={str(p):sha(p) for p in [Path('experiments/p012/tinker_lora.py'),Path('experiments/p012/scoring.py'),Path('experiments/p012/termination_summary.py'),ROOT/'amendment5_v1/score_endpoint.py',ROOT/'amendment5_v1/check_t_v2.py']}
def event(stage,**kw):
    item={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stage':stage,**kw};state['events'].append(item);state['updated_utc']=item['utc']
    f=STATE.with_suffix('.tmp');f.write_text(json.dumps(state,indent=2)+'\n');f.replace(STATE);print(json.dumps(item),flush=True)
def check_sources():
    for p,h in frozen.items():assert sha(p)==h,p
def start(name):
    check_sources();d=ROOT/'tinker_formal_v1'/name;r=read(d/'request.json');pub=ADMISSION/'requests'/(name+'.json')
    assert r['mode']=='generate' and not r.get('sampler_path') and r['forecast']['admitted']
    assert not (d/'run.log').exists() and not (d/'result').exists()
    assert sha(d/'request.json')==sha(pub) and subprocess.check_output(['git','show','HEAD:'+str(pub)])==pub.read_bytes()
    assert r['forecast']['admission_sha256']==sha(ADMISSION/'ADMISSION.json')
    with (d/'run.log').open('x') as f:
        p=subprocess.Popen([TINKER_PY,str(ROOT/'amendment4_v1/launch_tinker_private.py'),str(d)],env=ENV,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    children[name]=p;event('launched',run_id=name,pid=p.pid)
def finish(name):
    d=ROOT/'tinker_formal_v1'/name;out=PUBLIC/name.replace('_20261114','')
    if out.exists():return True
    if not (d/'result/COMPLETE.json').exists():return False
    check_sources();req=read(d/'request.json');assert read(d/'result/COMPLETE.json')['success']
    checks=[]
    if req['n']==8:
        subprocess.run([PY,str(ROOT/'amendment5_v1/check_t_v2.py'),name],env=ENV,check=True)
        checks.append(PUBLIC/'review_a56115d6/first_run_checks'/(name+'.json'))
    assert not (d/'PREDICTION_BEFORE_SCORE.json').exists()
    (d/'PREDICTION_BEFORE_SCORE.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'prediction_commit':req['prediction_commit'],'raw_sha256':sha(d/'result/generation/raw.jsonl'),'pretraining':True},indent=2)+'\n')
    subprocess.run([PY,str(ROOT/'amendment5_v1/score_endpoint.py'),'tinker_formal_v1/'+name],env=ENV,check=True)
    term=read(d/'TERMINATION.json');out.mkdir(exist_ok=False)
    result={'track':'tinker_lora','task':'gsm8k','pretraining':True,'run_id':name,'model':req['model'],'seed':req['seed'],'input':req['evaluation'],'termination':term['all'],'usage':read(d/'result/USAGE.json'),'raw_sha256':sha(d/'result/generation/raw.jsonl'),'labels_sha256':sha(d/'score_v1/labels.jsonl'),'independent_numeric_audit':'pending'}
    if req['n']==8:result.update(pass_metrics=read(d/'PASS_METRICS.json'),first_run_check=read(d/'T4_FIRST_RUN_CHECK.json'))
    (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    with zipfile.ZipFile(out/'evidence.zip','x',zipfile.ZIP_DEFLATED) as z:
        for root,prefix in [(d/'result','generation_result'),(d/'score_v1','scores')]:
            for f in root.rglob('*'):
                if f.is_file():
                    data=f.read_bytes();assert b'/Users/' not in data;z.writestr(prefix+'/'+str(f.relative_to(root)),data)
        for n in ['TERMINATION.json','PREDICTION_BEFORE_SCORE.json','PASS_METRICS.json','T4_FIRST_RUN_CHECK.json']:
            if (d/n).exists():z.write(d/n,n)
    (out/'README.md').write_text('# Tinker / LoRA GSM8K pretraining measurement\n\n'+name+'\n\nComplete frozen C7 inputs, original outputs, scores, termination diagnostics and usage are retained in evidence.zip. Independent result review is pending.\n')
    c=publish([out,*checks],'P012: publish authorized T-GSM pretraining endpoint '+name);event('result_published',run_id=name,commit=c)
    return True
def wait_for(group):
    deadline=time.monotonic()+8*3600
    while time.monotonic()<deadline:
        for name,p in children.items():
            if p.poll() not in (None,0):raise RuntimeError(name+' failed; no automatic replay')
        done=[finish(n) for n in group]
        if all(done):return
        time.sleep(10)
    raise TimeoutError('Finite observation deadline; existing calls are not killed')
try:
    event('controller_started',ppid=os.getppid())
    for name in names:start(name)
    wait_for(names)
    for name in samples:start(name);wait_for([name])
    state['status']='sampling_complete_nll_pending';event('all_eight_sampling_endpoints_complete')
except BaseException as exc:
    state['status']='stopped_for_inspection';event('stopped',error=str(exc));traceback.print_exc();raise
