"""One-time owner-requested maintenance pause; never discard a reserved generation."""
import argparse, collections, hashlib, json, os, signal, sys, time
from pathlib import Path

def reconciliation(events, saved, failed, allowed_runs):
    ids=[e['logical_id'] for e in events if e['kind']=='generation']
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate physical generation ID')
    base={i for i in ids if i.startswith('Base-dev/')}
    if len(base)!=512:raise ValueError('Base-dev physical coverage differs')
    if not failed.issubset(ids):raise ValueError('Missing original failed reservations')
    actual=set(ids)-base-failed
    if any(i.split('/')[0] not in allowed_runs for i in actual):raise ValueError('Unexpected evaluation namespace')
    if not saved.issubset(actual):raise ValueError('Saved output without its physical reservation')
    return sorted(actual-saved)

def self_test():
    base=[dict(kind='generation',logical_id='Base-dev/'+str(i)) for i in range(512)]
    bad={'Base-GSM8K/lost'}
    events=base+[dict(kind='generation',logical_id=i) for i in bad]+[dict(kind='generation',logical_id='SFT-GSM8K/a')]
    assert reconciliation(events,{'SFT-GSM8K/a'},bad,{'SFT-GSM8K'})==[]
    assert reconciliation(events,set(),bad,{'SFT-GSM8K'})==['SFT-GSM8K/a']
    for changed,saved,failed in [(events+events[-1:],set(),bad),(events,{'SFT-GSM8K/absent'},bad),(events,set(),{'missing'})]:
        try:reconciliation(changed,saved,failed,{'SFT-GSM8K'})
        except ValueError:pass
        else:raise AssertionError('Unsafe reconciliation accepted')
    print('5 maintenance-reconciliation checks passed')

def run(a):
    sys.path.insert(0,a.source)
    from experiments.public_math_pilot_v1.source_guard import verify_inventory
    from experiments.public_math_pilot_v1.runtime_common import checked_completed_batch,read
    from experiments.public_math_pilot_v1.runtime_evaluate import evaluation_jobs
    from experiments.public_math_pilot_v1.runtime_prepare import prepare_identity
    from experiments.public_math_pilot_v1.data import load_inputs
    from experiments.public_math_pilot_v1.tokenization import encode_prompt
    from experiments.public_math_pilot_v1.infrastructure_retry import GsmOomRetryLedger,SUFFIX
    root=Path(a.root);out=root/'main';source=Path(a.source)
    commit='c833d732a7e5b7ecf7589a41ea30f2fb7068a6d9'
    verify_inventory(source/'SOURCE_INVENTORY.json',source/'experiments/public_math_pilot_v1/preflight_inputs.json',expected_source_commit=commit,expected_inventory_sha256='59edaf26177686556c3a31df9f135276f215fdb76479d4299e0f9e2cfdca1ecc',repo_root=source)
    tokenizer,identity,_=prepare_identity(a.base,root/'release_v1',source/'experiments/public_math_pilot_v1/preflight_inputs.json')
    rows=[dict(id=r['problem_id'],prompt_ids=encode_prompt(tokenizer,r['question'])) for r in load_inputs(root/'release_v1')['gsm8k'][:128]]
    ledger=GsmOomRetryLedger(root/'physical_ledger.jsonl',out/'GSM128_OOM_RETRY.json',rows,identity)
    failed=ledger.retry_ids;names={j['name'] for j in evaluation_jobs()}
    proc=Path('/proc')/str(a.pid)
    def process():
        cmd=(proc/'cmdline').read_bytes().split(b'\0');cmd=[x.decode() for x in cmd if x]
        if ('experiments.public_math_pilot_v1.runtime_evaluate' not in cmd or cmd[cmd.index('--output')+1]!=str(out) or cmd[cmd.index('--source-commit')+1]!=commit or (proc/'cwd').resolve()!=source.resolve()):raise ValueError('Unexpected process identity')
        fields=(proc/'stat').read_text().split(') ',1)[1].split()
        return int(fields[19]),fields[0]
    started,state=process()
    if state in ('T','t'):raise ValueError('Process was already stopped by another operator')
    def matches():
        ticks,state=process()
        if ticks!=started:raise ValueError('PID reused')
        return state
    def saved_signature():
        return tuple(sorted(str(p) for n in names for p in (out/'generation'/n).glob('batch_*.json') if p.stem.split('_')[-1].isdigit()))
    def audit():
        saved=set();counts=collections.Counter();batch_hashes={}
        for n in sorted(names):
            folder=out/'generation'/n
            files=sorted(p for p in folder.glob('batch_*.json') if p.stem.split('_')[-1].isdigit())
            if not files:continue
            ident=read(folder/'identity.json')
            for path in files:
                result=read(path);request=result['request'];offset=int(path.stem.split('_')[-1]);size=ident['decoding']['batch_size']
                if request['logical_name']!=n or request['model']!=ident['model'] or request['decoding']!=ident['decoding'] or request['row_ids']!=ident['all_ids'][offset:offset+size]:raise ValueError('Saved batch identity differs')
                checked_completed_batch(path,request)
                if set(result['rng_after'])!={'torch','cuda'} or len(result['rng_after']['cuda'])!=1:raise ValueError('Incomplete recovery RNG')
                for r in result['records']:
                    logical=n+'/'+r['id'];physical=logical+SUFFIX if logical in failed else logical
                    if physical in saved:raise ValueError('Duplicate completed output')
                    saved.add(physical);counts[n]+=1
                batch_hashes[str(path.relative_to(out))]=hashlib.sha256(path.read_bytes()).hexdigest()
        events=[json.loads(s) for s in (root/'physical_ledger.jsonl').read_text().splitlines() if s.strip()]
        missing=reconciliation(events,saved,failed,names)
        return missing,dict(saved_evaluation_outputs=len(saved),saved_by_run=dict(counts),generation_physical_records=sum(e['kind']=='generation' for e in events),original_failed_generations=len(failed),uncommitted_evaluation_reservations=len(missing),completed_batch_sha256=batch_hashes)
    stopped=False;terminated=False;checks=0
    def abort(signum,frame):raise SystemExit('Pause helper interrupted')
    signal.signal(signal.SIGTERM,abort);signal.signal(signal.SIGINT,abort);signal.signal(signal.SIGHUP,abort)
    previous=None;deadline=time.monotonic()+a.max_seconds
    try:
        while time.monotonic()<deadline:
            current=saved_signature()
            if current==previous:time.sleep(.01);continue
            previous=current;matches();os.kill(a.pid,signal.SIGSTOP);stopped=True
            for _ in range(100):
                if matches() in ('T','t'):break
                time.sleep(.01)
            else:raise RuntimeError('Evaluator did not enter stopped state')
            checks+=1
            try:missing,proof=audit()
            except json.JSONDecodeError:
                os.kill(a.pid,signal.SIGCONT);stopped=False;continue
            if missing:
                print(json.dumps(dict(event='inflight_batch_preserved',uncommitted=len(missing),check=checks)),flush=True)
                os.kill(a.pid,signal.SIGCONT);stopped=False;continue
            matches()
            proof.update(pid=a.pid,process_start_ticks=started,checks=checks,status='durable_boundary_verified',observed_unix=time.time(),source_commit=commit,operator_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),reason='owner_requested_shutdown_for_same_instance_dual_A800_change',new_model_calls_by_helper=0)
            with (out/'MAINTENANCE_PAUSE_BOUNDARY.json').open('x') as f:json.dump(proof,f,indent=2);f.flush();os.fsync(f.fileno())
            os.kill(a.pid,signal.SIGTERM);os.kill(a.pid,signal.SIGCONT);stopped=False
            for _ in range(100):
                if not proc.exists():break
                time.sleep(.1)
            else:raise RuntimeError('Evaluator did not exit; do not shut down')
            terminated=True
            proof['status']='evaluator_stopped_at_durable_boundary';proof['stopped_unix']=time.time()
            with (out/'MAINTENANCE_PAUSE_COMPLETE.json').open('x') as f:json.dump(proof,f,indent=2);f.flush();os.fsync(f.fileno())
            print(json.dumps({k:v for k,v in proof.items() if k!='completed_batch_sha256'}),flush=True)
            return
        raise TimeoutError('No durable boundary captured; evaluator remains running')
    finally:
        if stopped and not terminated:
            try:
                matches();os.kill(a.pid,signal.SIGCONT)
            except FileNotFoundError:pass

if __name__=='__main__':
    if sys.argv[1:]==['--self-test']:self_test();raise SystemExit(0)
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--source',required=True);p.add_argument('--base',required=True);p.add_argument('--pid',type=int,required=True);p.add_argument('--max-seconds',type=float,default=900)
    run(p.parse_args())
