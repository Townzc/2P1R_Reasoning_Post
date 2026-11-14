from pathlib import Path
from contextlib import contextmanager
import fcntl,json,os,subprocess
from a7_accounting import *

META=ROOT/'amendment7_v1';PY=str(ROOT/'venv/bin/python');TINKER_PY=str(ROOT/'tinker_venv312/bin/python');ENV=dict(os.environ,PYTHONPATH='.')
FROZEN={str(p):sha(p) for p in [Path('experiments/p012/tinker_lora.py'),Path('experiments/p012/scoring.py'),Path('experiments/p012/termination_summary.py'),META/'prepare_a7_post.py',META/'score_a7.py',META/'publish_a7_cell.py']}

@contextmanager
def lock(name):
    with (ROOT/'amendment6_v1'/name).open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)

def command(helper,*args):
    for p,h in FROZEN.items():assert sha(p)==h,'Active A7 source changed: '+p
    subprocess.run([PY,str(META/helper),*args],env=ENV,check=True)

def publish(paths,message):
    with lock('GIT_PUBLICATION.lock'):
        assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='codex/icml-acl-2027'
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],text=True).strip()
        paths=[Path(p) for p in paths];subprocess.run(['git','add',*map(str,paths)],check=True)
        archives=[str(f) for p in paths if p.is_dir() for f in p.rglob('*.zip')]
        if archives:subprocess.run(['git','add','-f',*archives],check=True)
        staged=subprocess.check_output(['git','diff','--cached','--name-only'],text=True).splitlines()
        assert all(any(f==str(p) or f.startswith(str(p)+'/') for p in paths) for f in staged)
        if staged:
            subprocess.run(['git','diff','--cached','--check'],check=True)
            subprocess.run(['git','commit','-m',message],check=True);subprocess.run(['git','push','origin','codex/icml-acl-2027'],check=True)
        return subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()

def start(d,event,children):
    assert not (d/'run.log').exists() and not (d/'result').exists(),'Refuse duplicate call'
    r=read(d/'request.json');assert r['forecast']['admitted'] and r['prediction_commit']==AUTHORITY
    admission=Path(r['forecast']['admission_file']);assert sha(admission)==r['forecast']['admission_sha256']
    p=admission.parent/'requests'/(d.name+'.json') if r['mode']=='train' else PUBLIC/'a7_post_requests_v1'/(d.name+'.json')
    assert p.read_bytes()==(d/'request.json').read_bytes()==subprocess.check_output(['git','show','HEAD:'+str(p)])
    assert r['source_sha256']==sha('experiments/p012/tinker_lora.py')
    with (d/'run.log').open('x') as f:
        proc=subprocess.Popen([TINKER_PY,str(ROOT/'amendment4_v1/launch_tinker_private.py'),str(d)],env=ENV,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    children[d.name]=proc;event('launched',run_id=d.name,pid=proc.pid,request_sha256=sha(d/'request.json'))

def finish(name,event,children):
    tr=ROOT/'a7_runs_v1'/name
    if not (tr/'result/COMPLETE.json').exists():return
    req=read(tr/'request.json');ev=tr.with_name(name.replace(f'_s{req["seed"]}_',f'_s{req["seed"]}_greedy_'))
    if not (ev/'request.json').exists():
        command('prepare_a7_post.py',name)
        c=publish([PUBLIC/'a7_post_requests_v1'/(ev.name+'.json')],'P012: publish reserved A7 greedy request '+name)
        event('evaluation_request_published',run_id=ev.name,commit=c)
    if not (ev/'run.log').exists():start(ev,event,children)
    if not (ev/'result/COMPLETE.json').exists():return
    if not (ev/'TERMINATION.json').exists():
        assert not (ev/'score.log').exists(),'Incomplete scoring requires inspection'
        command('score_a7.py',ev.name)
    pub=PUBLIC/name.replace('_20261113','')
    if not pub.exists():
        command('publish_a7_cell.py',name)
        c=publish([pub],'P012: preserve A7 result '+name);event('result_published',run_id=name,commit=c)

def failures(names,children):
    for name in names:
        d=ROOT/'a7_runs_v1'/name
        if not (d/'request.json').exists():continue
        r=read(d/'request.json');ev=d.with_name(name.replace(f'_s{r["seed"]}_',f'_s{r["seed"]}_greedy_'))
        for p in [d,ev]:
            if (p/'result/PARTIAL_USAGE.json').exists():raise RuntimeError('Partial usage: '+p.name)
            if (p/'run.log').exists() and 'Traceback (most recent call last)' in (p/'run.log').read_text(errors='replace'):raise RuntimeError('Call exception: '+p.name)
    for name,p in children.items():
        rc=p.poll()
        if rc is not None and rc!=0:raise RuntimeError(f'Child stopped: {name}, exit{rc}')
