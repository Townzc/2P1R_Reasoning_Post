"""Publish each original E9 single endpoint once from saved proofs, no scoring."""
import argparse,ast,hashlib,json,shutil,tarfile
from pathlib import Path
from experiments.p010.common import read,dump,sha,digest,manifest,utc
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps


def archive(dest,files):
    members={n:dict(bytes=p.stat().st_size,sha256=sha(p)) for n,p in files.items()}
    with tarfile.open(dest,'x:gz') as t:
        for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
    with tarfile.open(dest) as t:
        assert {m.name for m in t.getmembers()}==set(members)
        for m in t.getmembers():
            assert m.isfile() and hashlib.sha256(t.extractfile(m).read()).hexdigest()==members[m.name]['sha256']
    return dict(bytes=dest.stat().st_size,sha256=sha(dest),members=members)


def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    with Path(src).open('rb') as f,dst.open('xb') as g:shutil.copyfileobj(f,g)
    assert sha(src)==sha(dst)


def safe(path):
    if Path(path).suffix in ('.json','.jsonl','.md','.txt'):
        data=Path(path).read_text()
        if '/Users/' in data or '/var/folders/' in data:raise ValueError('Private local locator: '+str(path))


def publish(run):
    assert run in ('e9_s17_n400','e9_s17_n3200','e9_base_math')
    baseline=(run=='e9_base_math')
    r=Path('.local/p010_20261019/r1');p=Path('reports/p010_20261019');receipt=r/'e9_runs'/run
    export=r/'e9_exports'/run;oracle=r/'e9_oracles'/run;records=r/'e9_records'/run;score=r/'e9_scores'/run
    spec_path=p/'e9_runtime_v1/SPEC.json';spec=read(spec_path);env=read(receipt/'RESULT.json');local=read(receipt/'INTENT.json');sent=read(receipt/'SUBMITTED.json')
    generation=read(oracle/'COMPLETED.json');scored=read(score/'LOCAL_ORACLE_AUDIT.json');done=read(score/'COMPLETED.json');payload=score/'job/payload'
    collection=read(export/'COMPLETED.json');provider=read(export/'PROVIDER_PRIVATE.json');ledger=read(records/'RECORDS.json')
    assert env['status']=='completed' and generation['passed'] and done['passed'] and scored['passed']
    assert all(not (x/'FAILED.json').exists() for x in (oracle,score,payload,records))
    assert generation['original_receipt_sha256']==sha(receipt/'RESULT.json')==collection['original_result_sha256']
    assert generation['spec_sha256']==sha(spec_path) and generation['source_files']==spec['source_files']
    assert generation['outputs_decoded']==500 and generation['targets_verified']==(0 if baseline else 2097148) and generation['updates_verified']==(0 if baseline else 1024)
    assert generation['full_state_loaded_once'] is (not baseline) and generation['symbolic_scoring_performed'] is False
    assert scored['full_generation_proof_sha256']==sha(oracle/'COMPLETED.json') and done['oracle_sha256']==sha(score/'LOCAL_ORACLE_AUDIT.json')
    assert scored['original_binding']['original_scoring_rows_sha256']==sha(oracle/'SCORING_ROWS.json')
    assert scored['scoring_payload_sha256']==sha(payload/'COMPLETED.json') and scored['scoring_control_sha256']==sha(score/'job/COMPLETED.json')
    if baseline:
        assert scored['state_sha256'] is None and generation['state_sha256'] is None
    else:
        assert scored['state_sha256']==generation['state_sha256']==env['artifact']['all_files']['checkpoint_1024/state.pt']['sha256']
    assert generation['technical_unknown']==0 and scored['independent_A3_pending'] is True
    assert ledger['e9/'+run+'/terminal']==env and collection['provider_stopped'] and provider['app_id']==sent['app_id']
    assert read(records/'COMPLETED.json')['records_sha256']==sha(records/'RECORDS.json')
    validate_stopped_apps([sent['app_id']],provider['original_info'],provider['owned'])
    for n,h in spec['source_files'].items():assert sha(n)==h,n
    assert sha(export/'evidence.tar.gz')==env['artifact']['tar_sha256']
    # Full original compact contents have already passed their unique oracle.
    # Scan text for host locators before publishing any new directory.
    for f in (export/'evidence').rglob('*.json'):safe(f)
    for base in (oracle,payload,records):
        for f in base.rglob('*.json'):safe(f)
    for f in (receipt/'RESULT.json',receipt/'SUBMITTED.json',receipt/'INTENT.json',score/'LOCAL_ORACLE_AUDIT.json'):safe(f)
    out=p/'e9_results_v1'/run;out.mkdir(parents=True,exist_ok=False)
    copies={receipt/'RESULT.json':'ORIGINAL_RESULT_ENVELOPE.json',receipt/'SUBMITTED.json':'ORIGINAL_SUBMITTED.json',receipt/'INTENT.json':'ORIGINAL_LOCAL_INTENT.json',export/'COMPLETED.json':'ORIGINAL_COLLECTION_COMPLETED.json',export/'evidence.tar.gz':'original_evidence.tar.gz',oracle/'COMPLETED.json':'GENERATION_ORACLE.json',oracle/'DECODED_ROWS.json':'DECODED_ROWS.json',oracle/'SCORING_ROWS.json':'SCORING_ROWS.json',score/'LOCAL_ORACLE_AUDIT.json':'SCORING_ORACLE.json',score/'COMPLETED.json':'SCORING_COMPLETED.json',payload/'COMPLETED.json':'SCORE_PAYLOAD_COMPLETED.json',payload/'ALL_SCORED_ROWS.json':'ALL_SCORED_ROWS.json',payload/'AUDIT_SAMPLES.json':'AUDIT_SAMPLES.json',records/'RECORDS.json':'ORIGINAL_NAMED_LEDGER.json',records/'COMPLETED.json':'LEDGER_COMPLETED.json'}
    for src,name in copies.items():copy(src,out/name)
    for f in (payload/'audit_by_evaluation').glob('*.json'):copy(f,out/'audit_by_evaluation'/f.name)
    dump(out/'SCORING_JOURNAL_ARCHIVE.json',archive(out/'original_scoring_journal.tar.gz',{f.relative_to(payload).as_posix():f for f in payload.rglob('*') if f.is_file()}))
    life=provider['original_info'][0]['lifecycle']
    dump(out/'PROVIDER.json',dict(app_id=sent['app_id'],lifecycle={k:life[k] for k in ('created_at','state','stopped_at')},owned_count=len(provider['owned']),read_utc=provider['utc'],private_original_sha256=sha(export/'PROVIDER_PRIVATE.json'),projection='Actor identity omitted; original private bytes retained.'))
    endpoints=scored['endpoints']
    summary=dict(run=run,training_seed=None if baseline else 17,baseline_zero_training=baseline,student_model='allenai/OLMo-2-0425-1B',original_frozen_T72_training_texts_reused=not baseline,greedy_correct=endpoints['greedy']['correct'],greedy_denominator=500,logical_stops=scored['logical_stops'],technical_unknown=0,updates=0 if baseline else 1024,targets=0 if baseline else 2097148,bootstrap_performed=False,independent_A3_pending=True,state_sha256=generation['state_sha256'],execution_commit=local['execution'],original_spec_sha256=sha(spec_path),reserved_usd=local['budget']['new_reserved_usd'],is_final_cost=False,utc=utc())
    dump(out/'SUMMARY.json',summary)
    tree=ast.parse(Path('scripts/prepare_p010_runtime_packets.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='closure');ns=dict(ast=ast,Path=Path,sha=sha)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<existing pure source closure>','exec'),ns)
    sources=ns['closure'](['scripts/audit_p010_e9.py','scripts/score_p010_e9.py'])
    dump(out/'LOCAL_VERIFICATION_SOURCES.json',sources)
    for name in sources:copy(Path(name),out/'source'/name)
    copy(Path(__file__),out/'publisher.py')
    (out/'README.md').write_text('# '+run+' — original complete E9 endpoint, actual A3 pending\n\n'
        +'Original OLMo-2-0425-1B endpoint: '+str(summary['greedy_correct'])+'/500 greedy, with all caps and frozen parser decisions retained. Zero technical unknown. '
        +('This baseline has zero training updates and no checkpoint or repeated binary load. ' if baseline else 'The original student uses the same frozen T72 texts, seed17, complete1024 updates /2097148 targets, final adapter/optimizer/RNG and original full-state oracle. ')
        +'The original app is STOPPED with zero owned containers. No test-selected checkpoint, changed dose, sampled endpoint or repeated generation.\n\n'
        +'The original compact archive is copied byte-for-byte. The complete frozen CPU scoring journal preserves original pair attempts, chunks, fixed audit samples and Boolean tables. Publication does not decode, tokenize, symbolically score, deserialize state or bootstrap. '
        +'Independent actual A3 and fixed-sample adjudication remain pending; public state hashes do not imply external access to private binaries. Provider actor identity is projected with the private original SHA retained. '
        +'The '+str(summary['reserved_usd'])+'USD reservation is not observed spending, final invoice or remaining credit. Existing failed attempts retain their records and costs. '
        +'These are deterministic audit metadata, not course-report prose.\n')
    dump(out/'MANIFEST.json',manifest(out))
    dump(r/('PUBLICATION_'+run+'.json'),dict(utc=utc(),packet=str(out),manifest_sha256=sha(out/'MANIFEST.json'),new_model_calls=0,new_scores=0,new_state_loads=0))
    print(json.dumps(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);publish(p.parse_args().run)
