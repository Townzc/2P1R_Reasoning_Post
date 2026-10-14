"""PREPARED: one read-only ledger scan for a named finite set of stopped T8s.

No cloud jobs, model calls, remote writes, raw scoring, or existing closeout
replacement. Failure leaves the wave intent and all valid parts for explicit
bounded reconciliation, never a whole-wave retry. Local wall limit1200seconds.
"""
from pathlib import Path
import datetime, json, signal, subprocess, sys, traceback
import modal
from experiments.sft_allocation_midpoint.common import read, dump, digest, sha
from experiments.sft_allocation_p008.provider_release import read_stopped_apps
from experiments.sft_allocation_p008.student_t8_cap_binding import verify_supplement

r=Path(__file__).resolve().parent
s=r/'student_completion_r1';plan=read(s/'plan.json')
spec=read('reports/p008_20261013/student_t8_cap_9600_v1/ADMISSION.json')
runs=sorted(sys.argv[1:])
assert 1<=len(runs)<=8 and len(runs)==len(set(runs)) and set(runs)<=set(spec['runs'])
assert all(not (s/'closeouts'/run).exists() for run in runs)
wave_root=s/'t8_collection_waves'
for p in wave_root.glob('*/READ_INTENT.json'):
    assert not set(read(p)['runs']).intersection(runs), 'Prior collection intent exists; reconcile, never retry'
envelopes={};sent={}
for run in runs:
    envelopes[run]=read(s/'runs'/run/'result.json')
    sent[run]=read(s/'runs'/run/'dispatch_intent.json')
    env=envelopes[run]
    assert env['receipt']['status']=='completed' and env['receipt']['run_id']==run
    assert sent[run]['run_id']==run and sent[run]['plan']==plan
    assert sent[run]['config']['training_multiple']==8
    assert env['receipt']['evidence_sha256']==digest(env['artifact_manifest'])
wave=wave_root/digest(runs)
wave.mkdir(parents=True,exist_ok=False)
dump(wave/'READ_INTENT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
     runs=runs,envelope_sha256={run:sha(s/'runs'/run/'result.json') for run in runs},
     readonly=True,new_model_calls=0,new_remote_writes=0,local_seconds_limit=1200,
     script_sha256=sha(__file__)))
def timeout(*_):
    raise TimeoutError('Finite local collection window ended; preserve partial and reconcile')
signal.signal(signal.SIGALRM,timeout);signal.alarm(1200)
try:
    cli='.local/midpoint_20261011/venv/bin/modal'
    containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=60))
    apps=[sent[run]['provider_app_id'] for run in runs]
    assert len(set(apps))==len(runs)
    provider=read_stopped_apps(cli,apps,[c for c in containers if c['app_id'] in apps])
    infos={x['app_id']:x for x in provider}
    assert set(infos)==set(apps)
    d=modal.Dict.from_name('sft-allocation-midpoint-claims-v1',create_if_missing=False)
    prefix='midpoint/'+plan['campaign_id']+'/'
    other='midpoint/p008-student-lr-replacement-20261013-r1/'
    before={run:d.get(prefix+'terminal/'+run) for run in runs}
    assert all(before[run]==envelopes[run]['receipt'] for run in runs)
    # A single common snapshot; selected completed records are checked before
    # and after. Other still-running records are not claimed to be atomic.
    ledger={k:v for k,v in d.items() if k.startswith(prefix) or k.startswith(other)}
    for run in runs:
        assert ledger[prefix+'terminal/'+run]==before[run]
        verify_supplement(ledger,spec,run)
    dump(wave/'ledger.json',ledger)
    dump(wave/'PROVIDER_BEFORE.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         apps=provider,containers=containers))
    volume=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
    for run in runs:
        out=s/'closeouts'/run;out.mkdir(parents=True,exist_ok=False)
        (out/'ledger.json').hardlink_to(wave/'ledger.json')
        timestamps={}
        for folder in ('completed','intents'):
            for entry in volume.iterdir('/'+plan['campaign_id']+'/'+run+'/'+folder):
                name=folder+'/'+Path(entry.path).name
                assert name not in timestamps
                timestamps[name]=dict(mtime=float(entry.mtime),bytes=entry.size)
        assert timestamps
        dump(out/'TIMING_READ_METADATA.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
             scope='Original stopped Volume file mtimes, second precision; compact timestamps cannot establish timing',files=timestamps))
        x=infos[sent[run]['provider_app_id']]
        dump(out/'provider.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
             apps=[dict(app_id=x['app_id'],state=x['lifecycle']['state'],lifecycle=x['lifecycle'])],
             owned_containers=[],other_containers=containers))
        assert d.get(prefix+'terminal/'+run)==before[run]
        verify_supplement(d,spec,run)
        dump(out/'COLLECTION.json',dict(passed=True,wave=str(wave),runs=runs,
             common_ledger_sha256=sha(wave/'ledger.json'),one_ledger_scan=True,
             selected_terminal_before_after_equal=True,shared_snapshot_other_active_records_not_atomic=True,
             new_model_calls=0,new_remote_writes=0,raw_or_state_oracle_performed=False))
    assert all(d.get(prefix+'terminal/'+run)==before[run] for run in runs)
    dump(wave/'COMPLETED.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         passed=True,runs=runs,ledger_sha256=sha(wave/'ledger.json'),new_model_calls=0,new_remote_writes=0))
    print(json.dumps(dict(wave=str(wave),runs=runs,completed=True)))
except BaseException as exc:
    dump(wave/'ERROR.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),
         partial_parts_retained=True,whole_wave_retry_authorized=False,new_model_calls=0))
    raise
finally:
    signal.alarm(0)
