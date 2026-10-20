"""One bounded first-block observation for the accepted five original K1/E1d cells."""
import argparse,json,os,subprocess,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from experiments.p010.common import read,dump,sha,digest,utc


def startup(run,out):
    import modal
    root=Path('.local/p010_20261019/r1');spec=read('reports/p010_20261019/student_runtime_k1_e1d_v1/SPEC.json')
    if run not in spec['configs']:raise ValueError('Only original exact admitted cells')
    receipt=root/'student_runs'/run;sent=read(receipt/'SUBMITTED.json');local=read(receipt/'INTENT.json')
    if (receipt/'ERROR.json').exists() or (receipt/'RESULT.json').exists():
        raise ValueError('Closed original call requires closeout, not repeated startup')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    dump(out/'READ_INTENT.json',dict(utc=utc(),run=run,script_sha256=sha(__file__),local_cap_seconds=300,
        max_readers=2,new_model_calls=0,remote_writes=0,automatic_retry=False))
    timer=threading.Timer(300,lambda:os._exit(124));timer.daemon=True;timer.start()
    try:
        cli='.local/midpoint_20261011/venv/bin/modal'
        info=json.loads(subprocess.check_output([cli,'app','info',sent['app_id'],'--json'],text=True,timeout=45))
        containers=json.loads(subprocess.check_output([cli,'container','list','--json'],text=True,timeout=45))
        owned=[x for x in containers if x.get('app_id')==sent['app_id']]
        dump(out/'PROVIDER_PRIVATE.json',dict(app_id=sent['app_id'],original_info=info,owned=owned,utc=utc()))
        vol=modal.Volume.from_name('sft-allocation-midpoint-v1',create_if_missing=False)
        store=modal.Dict.from_name('p010-once-20261019',create_if_missing=False);prefix='student/'+run
        ledger={k:store.get(prefix+'/'+k) for k in ('claim','terminal','unit/training_block_0001_0016','done/training_block_0001_0016')}
        dump(out/'LEDGER.json',ledger)
        names=['INTENT.json','TRAINING_STARTED.json','training_environment.json','completed/training_block_0001_0016.json','completed/update_0016.json','forecasts/0000.json']
        def fetch(name):
            data=b''
            for chunk in vol.read_file('/p010-20261019/students/'+run+'/'+name):
                data+=chunk
                if len(data)>8*1024**2:raise ValueError('Bounded startup metadata too large')
            p=out/'original_files'/name;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(data)
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(fetch,names))
        files=out/'original_files';intent=read(files/'INTENT.json');started=read(files/'TRAINING_STARTED.json')
        env=read(files/'training_environment.json');ack=read(files/names[3]);update=read(files/names[4])
        identity=intent['identity'];cfg=spec['configs'][run]
        if (identity['run_id']!=run or identity['config']!=cfg or identity['execution']!=local['execution']
                or identity['source_files']!=spec['source_files'] or identity['input_files']!=spec['input_files']
                or identity['base_files']!=spec['model']['files'] or intent['claim']!=ledger['claim']
                or abs(intent['hard_deadline_epoch']-intent['worker_start_epoch']-4500)>.001
                or started['identity_sha256']!=digest(identity)
                or ack!=ledger['done/training_block_0001_0016'] or ack['count']!=16
                or ack['last_step']!=16 or update['step']!=16
                or ack['cumulative_targets']!=update['cumulative_targets']
                or 'H100' not in env['gpu'] or env['cuda']!='12.8'
                or env['deterministic_algorithms'] is not True):
            raise ValueError('Actual source/claim/configuration/GPU/first-block binding differs')
        proof=dict(passed=True,run=run,app_id=sent['app_id'],call_id=sent['call_id'],utc=utc(),
            source_count=len(identity['source_files']),gpu=env['gpu'],cuda=env['cuda'],
            first_updates=16,first_targets=ack['cumulative_targets'],
            worker_start_epoch=intent['worker_start_epoch'],hard_deadline_epoch=intent['hard_deadline_epoch'],
            observed_owned_containers=len(owned),original_terminal=ledger['terminal'],
            original_files={n:sha(files/n) for n in names},full_state_or_raw_oracle=False,
            partial_scores_computed=False,new_model_calls=0,remote_writes=0)
        dump(out/'COMPLETED.json',proof);return proof
    except BaseException as exc:
        dump(out/'FAILED.json',dict(type=type(exc).__name__,error=str(exc),unknown_not_cloud_failure=True,partial_preserved=True,automatic_retry=False));raise
    finally:timer.cancel()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(startup(a.run,a.out)))
