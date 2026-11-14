import datetime,json,os,time,traceback
from a7_ops import *
from recovery_ops import retry_admission,start_any
from admit_a7_concise import admit,names_for

STATE=META/'A7_RECOVERY_QUEUE.json';assert not STATE.exists()
state={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'controller_pid':os.getpid(),
       'status':'running','authority_commit':AUTHORITY,'accepted_analysis_review':'8a8fac5c8ae75170e5c505f4215b5f1f9f0948d4',
       'finite_training_runs':names_for(17)+names_for(29),'infrastructure_retries':1,'events':[]}
children={}
def event(stage,**kw):
    x={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stage':stage,**kw};state['events'].append(x);state['updated_utc']=x['utc']
    p=STATE.with_suffix('.tmp');p.write_text(json.dumps(state,indent=2)+'\n');p.replace(STATE);print(json.dumps(x),flush=True)
try:
    event('detached_controller_started',ppid=os.getppid(),process_group=os.getpgrp())
    d,pub,c=retry_admission('a7_1_tinker_lora_4b_math_concise_s17_greedy_20261113_v1')
    event('retry_admitted',commit=c);start_any(d,pub,event,children)
    deadline=time.monotonic()+8*3600
    for seed in (17,29):
        if seed==29:
            record=admit(29);event('seed29_admitted',**record)
            for name in names_for(29):start(ROOT/'a7_runs_v1'/name,event,children)
        while time.monotonic()<deadline:
            failures(names_for(17)+names_for(29),children)
            for name in names_for(seed):finish(name,event,children)
            if all((PUBLIC/n.replace('_20261113','')/'RESULTS.json').exists() for n in names_for(seed)):
                event('seed_batch_complete',seed=seed);break
            time.sleep(10)
        else:raise TimeoutError('Finite recovery queue deadline; no experiment killed')
    event('all_fifteen_analysis_inputs_ready')
    subprocess.run([PY,str(META/'prepare_and_run_a7_analysis.py')],env=ENV,check=True)
    state['status']='complete';event('analysis_and_review_packet_published')
except BaseException as exc:
    state['status']='stopped_for_inspection';event('stopped',error=str(exc));traceback.print_exc();raise
