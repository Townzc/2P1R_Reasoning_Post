"""Publish one complete Stage0 generation slot from original audited evidence.

This local tool neither contacts Modal nor loads a model/tokenizer/scorer. It
preserves original evidence bytes, projects private metadata explicitly, and
leaves actual-result review, MATH P1 and G0 pending.
"""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
from pathlib import Path
import shutil
import tarfile

from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest,verify
from experiments.sft_allocation_p008.evidence_bundle import safe_name
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009.stage0_generation_contract_v2 import SLOTS,DATASETS
from experiments.learning_regime_p009.stage0_generation_binding_v2 import validate_release

ROOT=Path('.local/p009_20261014/r1/stage0_generation_budget_r2')
SPEC=Path('reports/p009_20261014/stage0_generation_runtime_preflight_v2/ADMISSION.json')
PUBLIC=Path('reports/p009_20261014/stage0_generation_results_v1')
SCOPE='p009-stage0-generation-result-publication-code'
OMIT={'intent.json','compact_evidence.tar.gz','compact_manifest.json','bundle_receipt.json'}


def archive_original(root,destination,selected):
    for name in selected:safe_name(name)
    with destination.open('xb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as zipped:
        with tarfile.open(fileobj=zipped,mode='w') as tar:
            for name in sorted(selected):
                info=tar.gettarinfo(str(root/name),arcname=name)
                info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                with (root/name).open('rb') as member:tar.addfile(info,member)
    observed={}
    with tarfile.open(destination,'r:gz') as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.name not in selected or member.name in observed:
                raise ValueError('Unsafe/duplicate/unexpected original archive member')
            raw=tar.extractfile(member).read()
            observed[member.name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    if observed!=selected:raise ValueError('Original archive readback differs; retain partial')


def publish(run):
    if run not in SLOTS:raise ValueError('Only one of the three original slots')
    dest=PUBLIC/run
    if dest.exists():raise ValueError('Immutable or partial publication exists; no whole publisher retry')
    code=read(ROOT/'PUBLICATION_CODE_ACCEPTED.json')
    if (code.get('scope')!=SCOPE or code.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or code.get('source_sha256')!=sha(__file__)
            or sha(code['local_report_path'])!=code['report_sha256']
            or len(code.get('report_commit',''))!=40):
        raise ValueError('True exact publisher code review required')
    spec=read(SPEC);ev=ROOT/'exports'/run/'evidence';close=ROOT/'closeouts'/run
    oracle=read(ev/'LOCAL_ORACLE_AUDIT.json');env=read(ROOT/'runs'/run/'result.json')
    intent=read(ev/'intent.json');release=intent['release']
    slot=validate_release(spec,intent['plan'],run,release)
    proof=read(close/'COMPLETED.json');provider=read(close/'provider.json')
    sent=read(ROOT/'runs'/run/'dispatch_intent.json')
    apps=spec['P0_app_ids']+[sent['provider_app_id']]
    expected={name:DATASETS[name]['n'] for name in slot['datasets']}
    if (oracle.get('passed') is not True or oracle['run_id']!=run or oracle['spec_sha256']!=digest(spec)
            or set(oracle['summaries'])!=set(expected) or set(oracle['decoded'])!=set(expected)
            or any(oracle['summaries'][n]['total']!=count or len(oracle['decoded'][n])!=count
                or oracle['summaries'][n]['technical_unknown']!=0 for n,count in expected.items())
            or env['receipt']['status']!='completed' or env['receipt']['run_id']!=run
            or env['result']['dataset_counts']!=expected
            or oracle['artifact_digest']!=digest(env['artifact_manifest'])
            or read(ev/'result.json')!=env['result'] or intent['spec']!=spec
            or proof['passed'] is not True or proof['ledger_sha256']!=sha(close/'ledger.json')
            or proof['original_receipt_sha256']!=sha(ROOT/'runs'/run/'result.json')
            or provider['app_ids']!=apps or provider['state']!='stopped'
            or provider['owned_container_ids']):
        raise ValueError('Exact complete local oracle/envelope/source/closeout required')
    validate_stopped_apps(apps,provider['original_app_info'],provider['owned_containers'])
    for n,h in spec['source_files'].items():
        if sha(n)!=h:raise ValueError('Reviewed generation source changed')
    verify(ev,env['artifact_manifest'])
    selected={n:v for n,v in env['artifact_manifest'].items() if n not in OMIT and not n.endswith('.pt')}
    omitted={n:v for n,v in env['artifact_manifest'].items() if n not in selected}
    dest.mkdir(parents=True,exist_ok=False)
    archive_original(ev,dest/'ORIGINAL_PUBLIC_MEMBERS.tar.gz',selected)
    # A compressed byte-for-byte oracle avoids GitHub's single-file size limit.
    with (ev/'LOCAL_ORACLE_AUDIT.json').open('rb') as f,(dest/'LOCAL_ORACLE_AUDIT.json.gz').open('xb') as out:
        with gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as zipped:shutil.copyfileobj(f,zipped)
    with gzip.open(dest/'LOCAL_ORACLE_AUDIT.json.gz','rb') as f:
        h=hashlib.sha256()
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    if h.hexdigest()!=sha(ev/'LOCAL_ORACLE_AUDIT.json'):raise ValueError('Oracle byte readback differs')
    dump(dest/'ORIGINAL_ENVELOPE.json',env)
    shutil.copyfile(close/'ledger.json',dest/'LEDGER.json')
    dump(dest/'PROVIDER.json',dict(app_ids=apps,state='stopped',owned_container_count=0,
        observed_utc=provider['utc'],original_private_file_sha256=sha(close/'provider.json'),
        projection='Original actor and unrelated workspace rows omitted; private original retained.',
        apps=[dict(app_id=x['app_id'],lifecycle={k:x['lifecycle'][k] for k in ('state','created_at','stopped_at')})
            for x in provider['original_app_info']]))
    dump(dest/'SOURCE_BINDING.json',dict(source_files=spec['source_files'],spec_sha256=digest(spec),
        execution_commit=release['execution_commit'],runtime_review=release['runtime_review']['report_commit'],
        runtime_review_sha256=release['runtime_review']['report_sha256'],
        original_intent_file_sha256=sha(ev/'intent.json'),original_oracle_file_sha256=sha(ev/'LOCAL_ORACLE_AUDIT.json'),
        original_dispatch_file_sha256=sha(ROOT/'runs'/run/'dispatch_intent.json'),
        source_target=release['review_target'],reserved_cents=slot['reserved_cents'],reservation_is_actual_expense=False))
    dump(dest/'PROJECTION.json',dict(files=selected,omitted=omitted,original_manifest_digest=digest(env['artifact_manifest']),
        archive_sha256=sha(dest/'ORIGINAL_PUBLIC_MEMBERS.tar.gz'),
        reason='Private original intent and packaging metadata omitted; all original raw outputs and saved batch metadata included. No binary state exists for these pure generation runs.'))
    dump(dest/'RESULTS.json',dict(run_id=run,summaries=oracle['summaries'],original_counts=expected,
        new_training_updates=0,P1_symbolic_scoring_performed=False,G0_admitted=False,
        actual_result_external_review='PENDING',created_utc=datetime.now(timezone.utc).isoformat()))
    shutil.copyfile(__file__,dest/'PUBLICATION_SOURCE.py')
    (dest/'README.md').write_text('''# Complete original Stage0 generation slot

All original rows for this slot are saved, independently decoded/lineage-checked
locally and the original provider is STOPPED with no owned containers. RESULTS
copies complete original counts and logical stop/cap records. GSM scores use the
frozen parser. MATH is decoded but unscored until real P1. This packet does not
admit G0 or any student, and actual-result independent review is pending.

The public tar contains original raw/batch/environment/result bytes, read back
against the original manifest. The original local oracle is losslessly compressed
and its decompressed SHA recorded. Private runtime intent and old packaging are
explicitly omitted; the original intent file SHA binds the private original.
Provider actor fields/unrelated rows are explicitly projected out. Failed P0
ancestors and their original claims remain in the source-bound ledger. No model,
scorer, tokenizer or cloud API is called by this publisher. No prior output or
scientific comparison is regenerated. Reservations are not invoices or balances.
''')
    dump(dest/'MANIFEST.json',manifest(dest))
    print(str(dest))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',choices=list(SLOTS),required=True)
    publish(p.parse_args().run)
