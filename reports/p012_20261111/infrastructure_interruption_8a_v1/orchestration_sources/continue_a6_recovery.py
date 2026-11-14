from pathlib import Path
import datetime,json,os,time,traceback
from a7_ops import ROOT,META,PUBLIC,PY,TINKER_PY,ENV,read,sha,lock,publish,accounting
from recovery_ops import retry_admission,start_any

import subprocess
A6=ROOT/'amendment6_v1'
STATE=META/'A6_3_RECOVERY_QUEUE.json';assert not STATE.exists()
NAMES=[f'a6_3_tinker_lora_4b_math_{c}_s17_20261113_v1' for c in ('e4','e8','l64')]
state={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'controller_pid':os.getpid(),
       'status':'running','finite_training_runs':NAMES,'one_retry_each':['E4','E8'],'events':[]}
children={}
FROZEN={str(p):sha(p) for p in [Path('experiments/p012/tinker_lora.py'),Path('experiments/p012/scoring.py'),
       A6/'prepare_t_post_any.py',A6/'score_a6.py',A6/'publish_a6_cell.py']}
def event(stage,**kw):
    x={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stage':stage,**kw};state['events'].append(x);state['updated_utc']=x['utc']
    p=STATE.with_suffix('.tmp');p.write_text(json.dumps(state,indent=2)+'\n');p.replace(STATE);print(json.dumps(x),flush=True)
def command(helper,*args):
    for p,h in FROZEN.items():assert sha(p)==h
    subprocess.run([PY,str(A6/helper),*args],env=ENV,check=True)
try:
    event('detached_controller_started',ppid=os.getppid(),process_group=os.getpgrp())
    deadline=time.monotonic()+8*3600
    for index,name in enumerate(NAMES):
        if index<2:
            d,pub,c=retry_admission(name);event('retry_admitted',run_id=name,commit=c)
        else:
            d=ROOT/'a6_runs_v1'/name
            with lock('BUDGET_ADMISSION.lock'):
                snap=accounting();r=read(d/'request_pending.json');cost=r['forecast']['forecast_usd']
                if snap['A6_3_accounted_and_reserved_usd']+cost>35:
                    state['status']='stopped_at_budget';event('L64_not_admitted',A6_3_current=snap['A6_3_accounted_and_reserved_usd'],next_buffered_usd=cost,cap=35);break
                command('admit_a6_prepared.py','a6_3_4b_l64_admission_v1',name)
                folder=PUBLIC/'a6_3_4b_l64_admission_v1';c=publish([folder],'P012: admit L64 after recovered E4/E8 settlement')
                pub=folder/'requests'/(name+'.json');event('L64_admitted',commit=c)
        start_any(d,pub,event,children)
        ev=d.with_name(name.replace('_s17_','_s17_greedy_'))
        while time.monotonic()<deadline:
            for n,p in children.items():
                code=p.poll()
                if code is not None and code!=0:raise RuntimeError(f'{n} exited{code}; no further retry')
            for folder in (d,ev):
                if (folder/'result/PARTIAL_USAGE.json').exists():raise RuntimeError('Partial usage: '+folder.name)
            if (d/'result/COMPLETE.json').exists():
                if not (ev/'request.json').exists():
                    command('prepare_t_post_any.py','a6_runs_v1/'+name)
                    evpub=PUBLIC/'tinker_lora_post_requests_v2'/(ev.name+'.json')
                    c=publish([evpub],'P012: publish recovered A6 reserved greedy request '+name);event('greedy_request_published',commit=c)
                if not (ev/'run.log').exists():start_any(ev,PUBLIC/'tinker_lora_post_requests_v2'/(ev.name+'.json'),event,children)
            if (ev/'result/COMPLETE.json').exists():
                command('score_a6.py',ev.name);command('publish_a6_cell.py',name)
                c=publish([PUBLIC/name.replace('_20261113','')],'P012: preserve recovered A6 result '+name)
                event('result_published',run_id=name,commit=c);break
            time.sleep(10)
        else:raise TimeoutError('Finite recovery deadline; no experiment killed')
    else:state['status']='complete';event('all_three_complete')
except BaseException as exc:
    state['status']='stopped_for_inspection';event('stopped',error=str(exc));traceback.print_exc();raise
