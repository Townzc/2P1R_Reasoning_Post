"""Single module-qualified launch plus an independent cost-window watchdog.

The wall budget includes local build/startup and cannot reset on container import
failure. It never relaunches; it stops only this attempt's exact observed app.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from experiments.p011.ext4b_runtime_contract import SPEC,LOCAL,JOBS,review,entry_cli_directory
from experiments.p011.ext4b_path import budget_check,published
from experiments.p011.owner_0205_common import create,read,utc,sha,digest


def main():
    p=argparse.ArgumentParser();p.add_argument('--job',choices=JOBS,required=True);p.add_argument('--source-review',required=True);p.add_argument('--actual-review',required=True);p.add_argument('--budget-json',required=True);p.add_argument('--attempt',type=int,choices=(1,2),default=1);p.add_argument('--resume-json');a=p.parse_args()
    spec=review(SPEC,a.source_review,a.actual_review);published(Path.cwd(),spec);check=budget_check(read(a.budget_json),a.job,a.attempt,time.time())
    if (a.attempt==2)!=bool(a.resume_json):raise ValueError('Exact first versus one resumed attempt required')
    name=a.job+f'_attempt{a.attempt}';cli_directory=entry_cli_directory(spec,a.job,a.attempt)
    if a.attempt==1:
        parent=spec['preentry_schema_failures'][a.job]
        if (sha(parent['cli_exit_path'])!=parent['cli_exit_sha256'] or sha(parent['log_path'])!=parent['log_sha256']
                or read(parent['cli_exit_path'])['exit_code']!=1 or (LOCAL/'dispatch'/name).exists()):
            raise ValueError('Exact pre-dispatch schema failure required, never a model retry')
        fence=LOCAL/'preentry_relaunch_fences'/(a.job+'.json');fence.parent.mkdir(parents=True,exist_ok=True)
        create(fence,{'utc':utc(),'parent_binding_sha256':digest(parent),'maximum_extra_entries':1,'model_attempt':1})
    out=LOCAL/cli_directory/name;out.mkdir(parents=True,exist_ok=False)
    cmd=['.local/midpoint_20261011/venv/bin/modal','run','-m','experiments.p011.modal_ext4b','--job',a.job,'--attempt',str(a.attempt),'--source-review',a.source_review,'--actual-review',a.actual_review,'--budget-json',a.budget_json]
    if a.resume_json:cmd+=['--resume-json',a.resume_json]
    start=time.time();deadline=start+check['worker_seconds']+check['startup_seconds']+60
    create(out/'ATTEMPT.json',{'utc':utc(),'epoch':start,'wrapper_pid':os.getpid(),'command':cmd,'absolute_cost_watchdog_epoch':deadline,'automatic_relaunch':False})
    observed_apps=set();done=threading.Event()
    process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,env={**os.environ,'PYTHONPATH':'.'})
    def watchdog():
        if done.wait(max(0,deadline-time.time())):return
        intent=LOCAL/'dispatch'/name/'INTENT.json'
        app=read(intent)['app_id'] if intent.exists() else next(iter(observed_apps)) if len(observed_apps)==1 else None
        record={'utc':utc(),'absolute_deadline_epoch':deadline,'app_id':app,'observed_apps':sorted(observed_apps),'model_relaunched':False}
        if app is not None:
            try:
                ret=subprocess.run(['.local/midpoint_20261011/venv/bin/modal','app','stop',app,'--yes'],capture_output=True,text=True,timeout=60)
                record.update(exit_code=ret.returncode,stdout=ret.stdout,stderr=ret.stderr)
            except BaseException as exc:record.update(stop_error=type(exc).__name__+': '+str(exc))
        else:record['stop_error']='No unambiguous owned app id; never stop other apps'
        create(out/'COST_WATCHDOG_STOP.json',record)
        if not done.wait(120) and process.poll() is None:process.terminate()
    thread=threading.Thread(target=watchdog,daemon=True);thread.start()
    with (out/'ORIGINAL_RUN.log').open('x') as stream:
        for line in process.stdout:
            stream.write(line);stream.flush()
            observed_apps.update(re.findall(r'\bap-[A-Za-z0-9]+\b',line))
    code=process.wait();done.set();thread.join(timeout=1)
    create(out/'CLI_EXIT.json',{'utc':utc(),'exit_code':code,'wrapper_started_epoch':start,'automatic_retry':False,'observed_apps':sorted(observed_apps)})
    print(name,'EXIT',code,flush=True);raise SystemExit(code)


if __name__=='__main__':main()
