"""Module-qualified single invocation; import and total-cost watchdogs never relaunch."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from experiments.p011.forced_answer_ext3b import SPEC, SCOPE, LOCAL, STORE, admit, actual, checked_budget
from experiments.p011.owner_0205_common import create, read, utc

MODULE='experiments.p011.modal_forced_answer_ext3b'


def launch_command(review,budget):
    return ['.local/midpoint_20261011/venv/bin/modal','run','-m',MODULE,
            '--review',review,'--budget-json',budget]


def main():
    p=argparse.ArgumentParser();p.add_argument('--review',required=True);p.add_argument('--budget-json',required=True);a=p.parse_args()
    spec=admit(SPEC,a.review,SCOPE);actual(spec);check=checked_budget(read(a.budget_json),time.time())
    if (LOCAL/'ONE_MODEL_ATTEMPT_FENCE.json').exists():raise ValueError('Relaunch already consumed')
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/codex/icml-acl-2027'],text=True).split()[0]
    if head!=remote:raise ValueError('Published execution HEAD required before image build')
    for name in [*spec['source_files'],SPEC]:
        if subprocess.check_output(['git','show',head+':'+name])!=Path(name).read_bytes():raise ValueError('Unpublished relaunch source')
    out=LOCAL/'cli';out.mkdir(parents=True,exist_ok=False)
    start=time.time();import_deadline=start+600;cost_deadline=start+check['worker_hard_seconds']+660
    command=launch_command(a.review,a.budget_json)
    create(out/'ATTEMPT.json',{'utc':utc(),'epoch':start,'wrapper_pid':os.getpid(),'command':command,
           'import_deadline_epoch':import_deadline,'absolute_cost_deadline_epoch':cost_deadline,'further_retry':False})
    done=threading.Event();observed=set();stop_lock=threading.Lock()
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env={**os.environ,'PYTHONPATH':'.'})
    def stop(reason):
        if not stop_lock.acquire(blocking=False):return
        intent=LOCAL/'dispatch/INTENT.json'
        app=read(intent)['app_id'] if intent.exists() else next(iter(observed)) if len(observed)==1 else None
        result={'utc':utc(),'reason':reason,'app_id':app,'observed_apps':sorted(observed),'relaunch':False}
        if app:
            try:
                ret=subprocess.run(['.local/midpoint_20261011/venv/bin/modal','app','stop',app,'--yes'],capture_output=True,text=True,timeout=60)
                result.update(exit_code=ret.returncode,stdout=ret.stdout,stderr=ret.stderr)
            except BaseException as exc:result['stop_error']=type(exc).__name__+': '+str(exc)
        else:result['stop_error']='No unambiguous owned app ID; never stop unrelated apps'
        create(out/'WATCHDOG_STOP.json',result)
        if not done.wait(120) and process.poll() is None:process.terminate()
    def watch():
        imported=False;last_error=None
        while not done.wait(10):
            now=time.time()
            if not imported and (LOCAL/'dispatch/SUBMITTED.json').exists():
                try:
                    probe='import json,modal; print(json.dumps(modal.Dict.from_name('+repr(STORE)+",create_if_missing=False).get('imported')))"
                    ret=subprocess.run(['.local/midpoint_20261011/venv/bin/python','-c',probe],capture_output=True,text=True,timeout=20,check=True)
                    row=json.loads(ret.stdout)
                    if row:
                        if row['module']!=MODULE:raise ValueError('Remote module identity differs')
                        create(out/'IMPORT_WATCHDOG_PASSED.json',{'utc':utc(),'remote_import_receipt':row,'original_module_not_relaunched':True})
                        imported=True
                except Exception as exc:last_error=type(exc).__name__+': '+str(exc)
            if not imported and now>=import_deadline:
                stop('Worker did not acknowledge module import within600s; '+str(last_error));return
            if imported:return
    def cost_watch():
        if not done.wait(max(0,cost_deadline-time.time())):
            stop('Whole-attempt cumulative cost window reached')
    thread=threading.Thread(target=watch,daemon=True);thread.start()
    cost_thread=threading.Thread(target=cost_watch,daemon=True);cost_thread.start()
    with (out/'ORIGINAL_RUN.log').open('x') as log:
        for line in process.stdout:
            log.write(line);log.flush();observed.update(re.findall(r'\bap-[A-Za-z0-9]+\b',line))
    code=process.wait();done.set();thread.join(timeout=1);cost_thread.join(timeout=1)
    create(out/'CLI_EXIT.json',{'utc':utc(),'exit_code':code,'started_epoch':start,'observed_apps':sorted(observed),'further_retry':False})
    print('forced_answer_ext3b_r1 EXIT',code,flush=True);raise SystemExit(code)


if __name__=='__main__':main()
