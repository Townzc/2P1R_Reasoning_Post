import json,os,sys,random,shutil,copy,tarfile,gzip
from pathlib import Path
R='/tmp/claude-0/pubw/repo'; os.chdir(R); sys.path.insert(0,R)
import scripts.publish_p009_nc_complete as m
from experiments.sft_allocation_midpoint.common import read,dump as _dump,sha,digest,manifest
def dump(p,v):
    p=Path(p)
    if p.exists(): p.unlink()
    _dump(p,v)
m.validate=lambda spec,plan,run,release: dict(reserved_cents=655)
spec=read(m.SPEC); W=Path('/tmp/claude-0/pubw/w')
def build(mut=None):
    shutil.rmtree(W,ignore_errors=True); root=W/'stage1_nc_r1'; (W/'stage1_nc_inputs_r1').mkdir(parents=True)
    ids=[f'gsm8k/test/{i}' for i in range(1319)]; dump(W/'stage1_nc_inputs_r1/NC_ENDPOINT.json',[dict(problem_id=i) for i in ids])
    rep=W/'rep.md'; rep.write_text('report'); rs=sha(rep)
    rev=dict(local_report_path=str(rep),report_sha256=rs,target_commit='a'*40)
    random.seed(1)
    for k,run in enumerate(m.RUNS):
        ev=root/'exports'/run/'evidence'; ev.mkdir(parents=True)
        app='ap-run'+str(k)
        release=dict(runtime_review=dict(rev),core_review=dict(rev),input_review=dict(rev),G0_review=dict(rev),
            internal_only_review=dict(rev),budget=dict(observed_epoch=1,source_snapshot='/private/path/b.json'),execution_commit='e'*40)
        plan=dict(p=run)
        intent=dict(plan=plan,spec=spec,run_id=run,release=release)
        dump(ev/'intent.json',intent)
        for f in ('raw/batch_000.json','completed/update_0016.json','checkpoint_1024/manifest.json','checkpoint_1024/merge.json'):
            (ev/f).parent.mkdir(parents=True,exist_ok=True); (ev/f).write_text(json.dumps(dict(f=f,run=run)))
        (ev/'checkpoint_1024/state.pt').write_bytes(os.urandom(4096))
        for f in ('compact_evidence.tar.gz','compact_manifest.json','bundle_receipt.json'):(ev/f).write_text('pkg')
        result=dict(done=True,run=run); dump(ev/'result.json',result)
        am=manifest(ev)
        env=dict(receipt=dict(status='completed',run_id=run,evidence_sha256=digest(am)),artifact_manifest=am,result=result)
        (root/'runs'/run).mkdir(parents=True); dump(root/'runs'/run/'result.json',env)
        dump(root/'runs'/run/'dispatch_intent.json',dict(plan=plan,run_id=run,release=release,provider_app_id=app))
        qc={i:random.random()<0.5 for i in ids}
        dump(ev/'LOCAL_ORACLE_AUDIT.json',dict(passed=True,run_id=run,updates_verified=1024,targets_verified=2097148,outputs_rescored=1319,
            total=1319,technical_unknown=0,artifact_digest=digest(am),state_sha256=am['checkpoint_1024/state.pt']['sha256'],
            question_correct=qc,correct=sum(qc.values()),logical_stops=dict(native_eos=1300,max_tokens=19),decoded=[]))
        cl=root/'closeouts'/run; cl.mkdir(parents=True); dump(cl/'ledger.json',dict(x=1))
        apps=spec['required_stopped_app_ids']+[app]
        infos=[dict(app_id=a,actor='secret-user',lifecycle=dict(state='stopped',created_at='t0',stopped_at='t1')) for a in apps]
        dump(cl/'provider.json',dict(app_ids=apps,state='stopped',original_app_info=infos,owned_containers=[],owned_container_ids=[],utc='u'))
        dump(cl/'COMPLETED.json',dict(ledger_sha256=sha(cl/'ledger.json'),passed=True,original_receipt_sha256=sha(root/'runs'/run/'result.json')))
    code=dict(scope=m.SCOPE,decision='PASS',source_files={'scripts/publish_p009_nc_complete.py':sha('scripts/publish_p009_nc_complete.py'),
        'scripts/publish_p009_stage0_result.py':sha('scripts/publish_p009_stage0_result.py')},target_commit='8'*40,report_commit='c'*40,
        local_report_path=str(rep),report_sha256=rs)
    an=read('reports/p009_20261014/stage1_nc_publication_preflight_v1/SOURCE_BINDING.json') if os.path.exists('reports/p009_20261014/stage1_nc_publication_preflight_v1/SOURCE_BINDING.json') else None
    analysis=dict(scope='p009-stage1-registered-analysis-and-stop-code',decision='PASS',target_commit='2c7d6b5ce7fe7d9c23ad59dc6e185493390f9a81',
        local_report_path=str(rep),report_sha256=rs,source_files=AN)
    dump(W/'code.json',code); dump(W/'analysis.json',analysis)
    if mut: mut(root)
    return root,ids
AN=json.loads(open('/tmp/claude-0/pubw/t/an.json').read())
def run(mut=None,label=''):
    root,ids=build(mut); out=W/'pub'
    try: m.publish(root,out,W/'code.json',W/'analysis.json'); r='OK'
    except Exception as e: r=f'{type(e).__name__}: {e}'
    print(f'[{label}] {r} | out exists={out.exists()} files={sorted(p.name for p in out.iterdir()) if out.exists() else None}')
    return root,out,ids
root,out,ids=run(label='happy')
m.dump=_dump
for run_ in m.RUNS:
    with tarfile.open(out/run_/'ORIGINAL_PUBLIC_MEMBERS.tar.gz') as t: print(run_,sorted(t.getnames()))
    ip=read(out/run_/'INTENT_PROJECTION.json'); s=json.dumps(ip); print('  private path leaked:', 'rep.md' in s or '/private/' in s)
    pv=read(out/run_/'PROVIDER.json'); print('  actor leaked:', 'secret-user' in json.dumps(pv))
d=read(out/'REGISTERED_NC_DECISION.json'); print('decision',d['decision'],{k:d['pair'][k] for k in d['pair'] if 'sha' not in k})
o4=read(root/'exports/nc_s17_n400/evidence/LOCAL_ORACLE_AUDIT.json')['question_correct']; o32=read(root/'exports/nc_s17_n3200/evidence/LOCAL_ORACLE_AUDIT.json')['question_correct']
print('manual delta', sum(o32.values())-sum(o4.values()))
try: m.publish(root,out,W/'code.json',W/'analysis.json')
except Exception as e: print('[rerun]',e)
def tamper_state(root):
    p=root/'exports/nc_s17_n3200/evidence/LOCAL_ORACLE_AUDIT.json'; o=read(p); o['state_sha256']='0'*64; dump(p,o)
run(tamper_state,'state mismatch')
def missing_q(root):
    p=root/'exports/nc_s17_n400/evidence/LOCAL_ORACLE_AUDIT.json'; o=read(p); o['question_correct'].pop(ids_first); o['correct']=sum(o['question_correct'].values()); dump(p,o)
ids_first='gsm8k/test/0'; run(missing_q,'missing question')
def raw_changed(root):(root/'exports/nc_s17_n400/evidence/raw/batch_000.json').write_text('x')
run(raw_changed,'raw byte changed')
def no_created(root):
    p=root/'closeouts/nc_s17_n3200/provider.json'; o=read(p)
    for x in o['original_app_info']: x['lifecycle'].pop('created_at')
    dump(p,o)
run(no_created,'provider lacks created_at')
def no_snapshot_review(root):
    for run_ in m.RUNS:
        for p in (root/'exports'/run_/'evidence/intent.json',):
            pass
run(None,'sanity')
