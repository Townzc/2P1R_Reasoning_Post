"""Run three untouched planned evaluations; missing training controls stay missing."""
import argparse
import json
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time

from . import screen_runtime as runtime
from . import screen_plan as spec
from .screen_continue import inherited_deadline
from .contracts import identity_hash
from .gpu_profile import ProfileError,durable_json,sha256,pinned_json,launch_guarded

PHASES=('eval_R','eval_W_prefix','eval_W_future')


def main(argv=None):
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument('--old-output',required=True)
    p.add_argument('--initialization-gate',required=True)
    extra,common=p.parse_known_args(argv)
    args=runtime.parse(common)
    if platform.system()!='Linux' or not args.execute_screen or not args.recover_initialization_timeout:
        raise ProfileError('explicit Linux repaired evaluation required')
    if args.recover_suite_watchdog or not args.retain_evaluation_unknowns:
        raise ProfileError('failed suite repair is prohibited; retain unknowns')
    if args._worker or args.phase or args.worker_deadline_epoch or not re.fullmatch('[a-f0-9]{40}',args.source_commit):
        raise ProfileError('evaluation parent owns worker phases/deadlines')
    old=Path(extra.old_output).resolve()
    split=pinned_json(args.split_json,args.split_sha256)
    plan=spec.validate_plan(pinned_json(args.plan_json,args.plan_sha256),split)
    args.plan_identity=identity_hash(plan)
    previous=json.loads((old/'continuation_intent.json').read_text())
    failure=json.loads((old/'continuation_failure.json').read_text())
    if previous['plan_sha256']!=args.plan_identity or failure['phase']!='R_future':
        raise ProfileError('wrong closed continuation')
    args.worker_deadline_epoch=inherited_deadline(previous,args.provider_deadline_epoch,time.time())
    for phase in PHASES:
        if (old/phase).exists():raise ProfileError('evaluation already attempted; no replay')
    for phase,rc in [('W_future',0),('R_future',1)]:
        receipt=json.loads((old/phase/'process_launcher_receipt.json').read_text())
        if receipt['returncode']!=rc:raise ProfileError('old phase not closed as expected')
        proc=Path(f"/proc/{receipt['pid']}/cmdline")
        if proc.exists() and b'q2_supervision_migration' in proc.read_bytes():raise ProfileError('old model worker still present')
    gate=Path(extra.initialization_gate)
    if json.loads((gate/'cpu_launcher_receipt.json').read_text())['returncode']!=0:
        raise ProfileError('original initialization gate did not pass')
    if not json.loads((gate/'preflight_complete.json').read_text())['saved_timeout_attributed']:
        raise ProfileError('initialization gate identity missing')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():
        raise ProfileError('GPU already has worker')
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False);args.out=str(out)
    runtime.disk_gate(out,initial=True);runtime.validate_environment(args,plan)
    for state in ['references','W_prefix','W_future']:(out/state).symlink_to(old/state,target_is_directory=True)
    for state in ['W_prefix','W_future']:runtime.source_for(args,state)
    refs=json.loads((out/'references/manifest.json').read_text())
    if refs['plan_sha256']!=args.plan_identity or sha256(out/'references/groundtruth.pickle')!=refs['sha256']:
        raise ProfileError('reference identity changed')
    durable_json(out/'evaluation_intent.json',{'source_commit':args.source_commit,
        'plan_sha256':args.plan_identity,'previous_source':previous['source_commit'],
        'phases':PHASES,'new_generations':3072,'new_optimizer_updates':0,
        'worker_deadline_epoch':args.worker_deadline_epoch,'provider_deadline_epoch':args.provider_deadline_epoch,
        'started_epoch':time.time(),'retain_unknown_scores':True,'suite_watchdog_repair_used':False,
        'missing_states':['C_prefix','C_future','R_future'],
        'all_three_primary_contrasts_available':False,'automatic_retry':False})
    command=[sys.executable,'-m','experiments.q2_supervision_migration.screen_runtime',*common,'--_worker']
    def interrupted(signum,frame):raise InterruptedError(f'evaluation parent received {signum}')
    previous_handler=signal.signal(signal.SIGTERM,interrupted)
    try:
        for phase in PHASES:
            runtime.remaining(args);runtime.disk_gate(out)
            phase_out=out/phase;phase_out.mkdir(exist_ok=False)
            end=min(args.worker_deadline_epoch,time.time()+plan['limits']['evaluation_phase_seconds'])
            rc=launch_guarded(command+['--phase',phase,'--worker-deadline-epoch',str(end)],phase_out,end-time.time(),phase='process')
            if rc:
                durable_json(out/'evaluation_failure.json',{'phase':phase,'retry':False,
                    'remaining_phases_not_run':list(PHASES[PHASES.index(phase)+1:])})
                return 1
        durable_json(out/'available_evaluations_complete.json',{'phases':PHASES,'finished_epoch':time.time(),
            'full_screen_complete':False,'missing_states':['C_prefix','C_future','R_future'],
            'unknown_scores_must_be_reported':True,'automatic_continuation':False})
        return 0
    except BaseException as exc:
        durable_json(out/'evaluation_parent_failure.json',{'error':repr(exc),'retry':False});raise
    finally:signal.signal(signal.SIGTERM,previous_handler)

if __name__=='__main__':raise SystemExit(main())
