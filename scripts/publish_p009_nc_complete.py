"""Once-only complete NC pair publication and already-reviewed paired decision.

Only reads original local full oracles and their evidence. No model, symbolic
scorer, tokenizer, provider API or binary-state loading. Partial output blocks
whole-tool repetition. Actual A4 remains required after publication.
"""
import argparse
from datetime import datetime,timezone
import gzip,hashlib,shutil
from pathlib import Path

from experiments.sft_allocation_midpoint.common import read,dump,sha,digest,manifest,verify
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009.stage1_nc_binding import CAMPAIGN,RUNS,validate
from experiments.learning_regime_p009.stage1_analysis import nc_result
from scripts.publish_p009_stage0_result import archive_original

SCOPE='p009-stage1-NC-complete-publication-and-analysis-binding-code'
SPEC=Path('reports/p009_20261014/stage1_nc_runtime_preflight_v1/ADMISSION.json')
OMIT={'intent.json','compact_evidence.tar.gz','compact_manifest.json','bundle_receipt.json'}


def bound(root,run,spec):
    ev=root/'exports'/run/'evidence';close=root/'closeouts'/run
    oracle=read(ev/'LOCAL_ORACLE_AUDIT.json');env=read(root/'runs'/run/'result.json')
    original=read(ev/'intent.json');sent=read(root/'runs'/run/'dispatch_intent.json')
    proof=read(close/'COMPLETED.json');provider=read(close/'provider.json')
    cap=validate(spec,original['plan'],run,original['release'])
    apps=spec['required_stopped_app_ids']+[sent['provider_app_id']]
    if (oracle.get('passed') is not True or oracle['run_id']!=run
        or oracle['updates_verified']!=1024 or oracle['targets_verified']!=2097148
        or oracle['outputs_rescored']!=1319 or oracle['total']!=1319 or oracle['technical_unknown']!=0
        or oracle['artifact_digest']!=digest(env['artifact_manifest'])
        or oracle['state_sha256']!=env['artifact_manifest']['checkpoint_1024/state.pt']['sha256']
        or sum(oracle['question_correct'].values())!=oracle['correct']
        or env['receipt']['status']!='completed' or env['receipt']['run_id']!=run
        or read(ev/'result.json')!=env['result'] or original['spec']!=spec or original['run_id']!=run
        or original['release']!=sent['release'] or original['plan']!=sent['plan']
        or proof['passed'] is not True or proof['ledger_sha256']!=sha(close/'ledger.json')
        or proof['original_receipt_sha256']!=sha(root/'runs'/run/'result.json')
        or provider['app_ids']!=apps or provider['state']!='stopped' or provider['owned_container_ids']):
        raise ValueError('Both original full NC oracles/envelopes/states/provider proofs are required')
    validate_stopped_apps(apps,provider['original_app_info'],provider['owned_containers'])
    verify(ev,env['artifact_manifest'])
    return dict(ev=ev,close=close,oracle=oracle,envelope=env,intent=original,provider=provider,
                apps=apps,slot=cap,sent=sent)


def publish(root,out,code_path,analysis_path):
    root=Path(root);out=Path(out)
    if out.exists():raise ValueError('Prior/partial pair publication exists; no whole-tool retry')
    code=read(code_path);analysis=read(analysis_path);spec=read(SPEC)
    expected_sources={__file__.replace(str(Path.cwd())+'/', ''):sha(__file__),
        'scripts/publish_p009_stage0_result.py':sha('scripts/publish_p009_stage0_result.py')}
    if (code.get('scope')!=SCOPE or code.get('decision') not in ('PASS','PASS-WITH-NOTES')
        or code.get('source_files')!=expected_sources or len(code.get('target_commit',''))!=40
        or len(code.get('report_commit',''))!=40 or sha(code['local_report_path'])!=code['report_sha256']):
        raise ValueError('True exact publication/binding review required')
    if (analysis.get('scope')!='p009-stage1-registered-analysis-and-stop-code'
        or analysis.get('decision') not in ('PASS','PASS-WITH-NOTES')
        or analysis.get('target_commit')!='2c7d6b5ce7fe7d9c23ad59dc6e185493390f9a81'
        or sha(analysis['local_report_path'])!=analysis['report_sha256']):
        raise ValueError('Original exact registered-analysis acceptance required')
    for k,v in {**spec['source_files'],**analysis['source_files']}.items():
        if sha(k)!=v:raise ValueError('Accepted scientific/runtime/analysis bytes changed')
    values={run:bound(root,run,spec) for run in RUNS}
    endpoint=read(root.parent/'stage1_nc_inputs_r1/NC_ENDPOINT.json')
    ids=[x['problem_id'] for x in endpoint]
    for v in values.values():
        scores=v['oracle']['question_correct']
        if set(scores)!=set(ids) or any(type(x) is not bool for x in scores.values()):
            raise ValueError('Every frozen question needs an original Boolean verdict')
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'PUBLICATION_INTENT.json',dict(utc=datetime.now(timezone.utc).isoformat(),
        source_files=expected_sources,oracle_sha256={run:sha(v['ev']/'LOCAL_ORACLE_AUDIT.json') for run,v in values.items()},
        once_only=True,new_model_calls=0,new_raw_or_symbolic_scoring=0))
    for run,v in values.items():
        dest=out/run;dest.mkdir();ev=v['ev'];env=v['envelope'];close=v['close'];provider=v['provider']
        selected={n:x for n,x in env['artifact_manifest'].items() if n not in OMIT and not n.endswith('.pt')}
        omitted={n:x for n,x in env['artifact_manifest'].items() if n not in selected}
        archive_original(ev,dest/'ORIGINAL_PUBLIC_MEMBERS.tar.gz',selected)
        with (ev/'LOCAL_ORACLE_AUDIT.json').open('rb') as inp,(dest/'LOCAL_ORACLE_AUDIT.json.gz').open('xb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:shutil.copyfileobj(inp,gz)
        with gzip.open(dest/'LOCAL_ORACLE_AUDIT.json.gz','rb') as inp:
            h=hashlib.sha256()
            for block in iter(lambda:inp.read(2**20),b''):h.update(block)
        if h.hexdigest()!=sha(ev/'LOCAL_ORACLE_AUDIT.json'):raise ValueError('Original oracle gzip readback differs')
        dump(dest/'ORIGINAL_ENVELOPE.json',env);shutil.copyfile(close/'ledger.json',dest/'LEDGER.json')
        dump(dest/'PROVIDER.json',dict(app_ids=v['apps'],state='stopped',owned_container_count=0,
            observed_utc=provider['utc'],original_private_file_sha256=sha(close/'provider.json'),
            projection='Actor identities and unrelated rows omitted; original private provider evidence retained.',
            apps=[dict(app_id=x['app_id'],lifecycle={k:x['lifecycle'][k] for k in ('state','created_at','stopped_at')})
                for x in provider['original_app_info']]))
        projection=dict(v['intent']);projection['release']=dict(projection['release']);removed={}
        for k in ('runtime_review','core_review','input_review','G0_review','internal_only_review'):
            item=dict(projection['release'][k]);removed[k]=dict(removed_key='local_report_path',original_value_sha256=digest(item.pop('local_report_path')))
            projection['release'][k]=item
        budget=dict(projection['release']['budget'])
        if 'source_snapshot' in budget:
            removed['budget']=dict(removed_key='source_snapshot',original_value_sha256=digest(budget.pop('source_snapshot')))
        projection['release']['budget']=budget
        dump(dest/'INTENT_PROJECTION.json',projection)
        dump(dest/'PROJECTION.json',dict(files=selected,omitted=omitted,original_manifest_digest=digest(env['artifact_manifest']),
            archive_sha256=sha(dest/'ORIGINAL_PUBLIC_MEMBERS.tar.gz'),original_intent_file_sha256=sha(ev/'intent.json'),
            projected_intent_file_sha256=sha(dest/'INTENT_PROJECTION.json'),intent_projection_removed_fields=removed,
            original_oracle_file_sha256=sha(ev/'LOCAL_ORACLE_AUDIT.json'),
            reason='Full state binary, private original intent and old packaging omitted. Raw outputs, update/block records, checkpoint manifest and merge proof retained as original bytes. Public state hashes do not mean external binary loading.'))
    decision=nc_result(ids,values['nc_s17_n400']['oracle']['question_correct'],values['nc_s17_n3200']['oracle']['question_correct'])
    dump(out/'REGISTERED_NC_DECISION.json',decision)
    dump(out/'SUMMARY.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        runs={run:dict(correct=v['oracle']['correct'],total=1319,logical_stops=v['oracle']['logical_stops'],
            technical_unknown=0,updates=1024,targets=2097148,state_sha256=v['oracle']['state_sha256']) for run,v in values.items()},
        actual_result_external_A4='PENDING',S1_runtime_admitted=False,new_model_calls=0,new_scoring=0,
        no_new_bootstrap=True,reserved_cents=1310,reservation_is_actual_expense=False))
    dump(out/'ACCEPTED_PUBLICATION.json',{k:v for k,v in code.items() if k!='local_report_path'})
    dump(out/'ACCEPTED_ANALYSIS.json',{k:v for k,v in analysis.items() if k!='local_report_path'})
    dump(out/'SOURCE_BINDING.json',dict(runtime_source_files=spec['source_files'],spec_sha256=digest(spec),
        analysis_source_files=analysis['source_files'],publication_source_files=expected_sources,
        executed_commits={run:v['intent']['release']['execution_commit'] for run,v in values.items()}))
    shutil.copyfile(__file__,out/'PUBLICATION_SOURCE.py')
    (out/'README.md').write_text('''# Complete original NC pair and registered decision

Both original seed17 students used the frozen 1024 updates and 2097148 targets,
with complete source-bound local raw/state/dose oracles and provider STOPPED0.
The paired NC decision uses the already-reviewed original >=5pp stop rule once.
All 1319 question identities are matched. Actual independent A4 is pending;
publication does not authorize S1 dispatch. No bootstrap, generation, symbolic
scoring, training or checkpoint loading occurs in this publisher.

Each archive is an explicit original-byte projection with independent byte
readback. Private original intent and state binary remain locally preserved;
the public intent is a separate disclosed projection, not the original bytes.
Provider actors are removed and the private original SHA retained. Complete
checkpoint manifests, merge proof, all raw and unit/ack records are included.
Public state SHA is not a claim that the external reviewer loaded the binary.
Runtime and cost observations are not future-host guarantees. Reservations,
delayed platform usage and invoices are distinct. All earlier failures and
P0 internal-only limitations remain in the original provenance.
''')
    dump(out/'MANIFEST.json',manifest(out));print(str(out))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('root','out','code-review','analysis-review'):p.add_argument('--'+k,required=True)
    a=p.parse_args();publish(a.root,a.out,a.code_review,a.analysis_review)
