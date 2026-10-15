# Exact53-source guard repair helper adaptation; original helpers unchanged.
"""Publish one completed replacement paired with the already-published NC400.

No raw scoring, binary-state loading, generation, provider calls or old archive
rebuilding. The original failed physical run is retained as a third lineage.
Exact code acceptance and actual full replacement oracle must precede use.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest, verify
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009.stage1_nc_guard_repair_binding import (
    validate, CAMPAIGN, RUN, dispatch_key, logical_key, marker)
from experiments.learning_regime_p009.stage1_nc_replacement_contract import (
    PARENT_CAMPAIGN, PARENT_RUN, ORIGINAL_NC400, PARENT_TARGET,
    PARENT_MANIFEST_SHA, PARENT_PRESERVED_SHA, PARENT_FAILURE_DIGEST, NC400_STATE_SHA)
from experiments.learning_regime_p009.stage1_analysis import nc_result
from scripts.publish_p009_stage0_result import archive_original

SCOPE = 'p009-stage1-NC-guard-repair-observation-and-pair-publication-code'
SPEC = Path('reports/p009_20261014/stage1_nc_guard_repair_preflight_v1/ADMISSION.json')
PARENT_PACKET = Path('reports/p009_20261014/stage1_nc_preemption_disposition_v1')
SOURCE_NAMES = (
    'scripts/p009_nc_guard_repair_observe.py',
    'scripts/publish_p009_nc_guard_repair_pair.py',
    'scripts/publish_p009_stage0_result.py',
)
OMIT = {'intent.json', 'compact_evidence.tar.gz', 'compact_manifest.json', 'bundle_receipt.json'}


def check_oracle(value, run, state_sha=None):
    scores = value.get('question_correct')
    if (value.get('passed') is not True or value.get('run_id') != run
        or value.get('updates_verified') != 1024 or value.get('targets_verified') != 2097148
        or value.get('outputs_rescored') != 1319 or value.get('total') != 1319
        or value.get('technical_unknown') != 0 or not isinstance(scores, dict)
        or len(scores) != 1319 or any(type(v) is not bool for v in scores.values())
        or sum(scores.values()) != value.get('correct')
        or (state_sha is not None and value.get('state_sha256') != state_sha)):
        raise ValueError('A complete source-bound original Boolean oracle is required')
    return value


def original_sibling():
    """Use the fixed published old oracle; never rebuild or reread its raw/state."""
    if sha(PARENT_PACKET/'MANIFEST.json') != PARENT_MANIFEST_SHA:
        raise ValueError('Original fixed outcome/preservation manifest changed')
    members = read(PARENT_PACKET/'MANIFEST.json')
    names = (ORIGINAL_NC400+'/LOCAL_ORACLE_AUDIT.json.gz', 'SUMMARY.json',
             PARENT_RUN+'_failed/PRESERVED.json', PARENT_RUN+'_failed/ORIGINAL_FAILURE_MANIFEST.json')
    for name in names:
        path = PARENT_PACKET/name
        if sha(path) != members[name]['sha256'] or path.stat().st_size != members[name]['bytes']:
            raise ValueError('An actually-used original publication member changed')
    if sha(PARENT_PACKET/names[2]) != PARENT_PRESERVED_SHA:
        raise ValueError('Failed physical parent preservation differs')
    if digest(read(PARENT_PACKET/names[3])) != PARENT_FAILURE_DIGEST:
        raise ValueError('Original failure evidence is not the preserved parent')
    summary = read(PARENT_PACKET/'SUMMARY.json')
    if (summary['nc3200']['status'] != 'failed' or summary['nc3200']['saved_checkpoint_count'] != 0
        or summary['nc3200']['saved_endpoint_outputs'] != 0
        or summary['nc3200']['parent_stays_failed'] is not True):
        raise ValueError('Never convert the failed physical parent into a completed run')
    with gzip.open(PARENT_PACKET/names[0], 'rt') as stream:
        value = check_oracle(json.load(stream), ORIGINAL_NC400, NC400_STATE_SHA)
    if value['correct'] != summary['nc400']['correct'] or value['logical_stops'] != summary['nc400']['logical_stops']:
        raise ValueError('Already-published sibling metadata differs')
    return value, dict(target_commit=PARENT_TARGET, manifest_sha256=PARENT_MANIFEST_SHA,
        original_oracle_gzip_sha256=members[names[0]]['sha256'], failed_parent_status='failed',
        failed_parent_preservation_sha256=PARENT_PRESERVED_SHA,
        old_raw_or_state_reloaded=False, old_archive_rebuilt=False,
        url='https://github.com/Townzc/2P1R_Reasoning_Post/tree/'+PARENT_TARGET+'/'+str(PARENT_PACKET))


def check_lineage(spec, sent, envelope, oracle, proof, provider, ledger, receipt_sha, ledger_sha):
    """Bind the new physical run and retained failed/sibling claims before analysis."""
    validate(spec, sent['plan'], RUN, sent['release'])
    if sent['run_id'] != RUN or sent['spec'] != spec:
        raise ValueError('Actual physical replacement/spec differs')
    claim = ledger['midpoint/'+CAMPAIGN+'/claim/'+RUN]
    terminal = ledger['midpoint/'+CAMPAIGN+'/terminal/'+RUN]
    expected = marker(spec, RUN, sent['release'])
    old_failure = ledger['midpoint/'+PARENT_CAMPAIGN+'/terminal/'+PARENT_RUN]
    if (terminal != envelope['receipt'] or terminal['status'] != 'completed' or terminal['run_id'] != RUN
        or terminal['claim_sha256'] != digest(claim) or terminal['attempt_id'] != claim['attempt_id']
        or terminal['evidence_sha256'] != digest(envelope['artifact_manifest'])
        or claim['reserved_cents'] != 655 or terminal['actual_cost_cents'] != 655
        or any(ledger.get(k) != v for k, v in spec['required_records'].items())
        or old_failure['status'] != 'failed' or old_failure['evidence_sha256'] != PARENT_FAILURE_DIGEST
        or any(ledger.get(k) != expected for k in (dispatch_key(RUN), logical_key(RUN)))
        or proof.get('passed') is not True or proof.get('original_failed_parent_retained') is not True
        or proof['ledger_sha256'] != ledger_sha or proof['original_receipt_sha256'] != receipt_sha):
        raise ValueError('New completion must retain both original physical lineages and reservations')
    check_oracle(oracle, RUN, envelope['artifact_manifest']['checkpoint_1024/state.pt']['sha256'])
    if oracle['artifact_digest'] != digest(envelope['artifact_manifest']):
        raise ValueError('Full oracle is not bound to this original replacement envelope')
    app = sent['release']['dispatch_app_id']; apps = spec['required_stopped_app_ids']+[app]
    if provider['app_ids'] != apps or provider['state'] != 'stopped' or provider['owned_container_ids']:
        raise ValueError('The complete original and replacement app roster must be STOPPED0')
    validate_stopped_apps(apps, provider['original_app_info'], provider['owned_containers'])
    return apps


def projection(value, prefix=''):
    """Remove only declared host-locator keys; hash and disclose every removal."""
    removed = {}
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            path = prefix+'.'+key if prefix else key
            if key in ('local_report_path', 'source_snapshot', 'raw_comment_local_path'):
                removed[path] = digest(item)
            else:
                out[key], part = projection(item, path); removed.update(part)
    elif isinstance(value, list):
        out = []
        for index, item in enumerate(value):
            item, part = projection(item, prefix+'.'+str(index)); out.append(item); removed.update(part)
    else:
        out = value
    return out, removed


def publish(root, out, code_path, analysis_path):
    root = Path(root); out = Path(out)
    if out.exists():
        raise ValueError('Existing/partial pair publication blocks whole-tool repetition')
    code = read(code_path); analysis = read(analysis_path); spec = read(SPEC)
    sources = {name: sha(name) for name in SOURCE_NAMES}
    if (code.get('scope') != SCOPE or code.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
        or code.get('source_files') != sources or len(code.get('target_commit', '')) != 40
        or len(code.get('report_commit', '')) != 40 or sha(code['local_report_path']) != code['report_sha256']):
        raise ValueError('Exact actual publication/observation code review is required')
    if (analysis.get('scope') != 'p009-stage1-registered-analysis-and-stop-code'
        or analysis.get('decision') not in ('PASS', 'PASS-WITH-NOTES')
        or analysis.get('target_commit') != '2c7d6b5ce7fe7d9c23ad59dc6e185493390f9a81'
        or sha(analysis['local_report_path']) != analysis['report_sha256']):
        raise ValueError('Original real registered analysis review is required')
    for name, h in {**spec['source_files'], **analysis['source_files']}.items():
        if sha(name) != h: raise ValueError('Exact reviewed source bytes changed')
    ev = root/'export_r1/evidence'; close = root/'closeout_r1'
    sent = read(ev/'intent.json'); dispatch = read(root/'runs'/RUN/'dispatch_intent.json')
    envelope = read(root/'runs'/RUN/'result.json'); oracle = read(ev/'LOCAL_ORACLE_AUDIT.json')
    ledger = read(close/'ledger.json'); provider = read(close/'provider.json'); proof = read(close/'COMPLETED.json')
    if (sent['release'] != dispatch['release'] or sent['plan'] != dispatch['plan']
        or read(ev/'result.json') != envelope['result']):
        raise ValueError('Original sent worker payload/envelope mismatch')
    for record in (sent['release']['runtime_review'], sent['release']['parent_disposition_review']):
        if sha(record['local_report_path']) != record['report_sha256']:
            raise ValueError('The true exact runtime and actual parent reports must remain present')
    apps = check_lineage(spec, sent, envelope, oracle, proof, provider, ledger,
        sha(root/'runs'/RUN/'result.json'), sha(close/'ledger.json'))
    verify(ev, envelope['artifact_manifest'])  # new export only; no state deserialization
    old, reference = original_sibling()
    endpoint = read(root.parent/'stage1_nc_inputs_r1/NC_ENDPOINT.json')
    ids = [row['problem_id'] for row in endpoint]
    for value in (old, oracle):
        if set(value['question_correct']) != set(ids):
            raise ValueError('Both original frozen full endpoints must have identical IDs')
    projected, removed = projection(sent)
    if '/Users/' in json.dumps(projected):
        raise ValueError('Unprojected private host locator must not be published')
    preclaim = Path('reports/p009_20261014/stage1_nc_replacement_preclaim_failure_v1')
    if sha(preclaim/'MANIFEST.json') != '1e7d53c4b4bb93fcfeb9fa5ec81b174c88e125a4ad56ba6ef143920fb27e249e':
        raise ValueError('Fixed public preclaim preservation packet differs')
    if sha(preclaim/'ZERO_WORK_VERIFIED.json') != spec['preclaim_proof_file_sha256']:
        raise ValueError('Actual preclaim proof differs; never invent a failed terminal')
    proxy = sent['release']['owner_proxy_decision']
    if sha(proxy['raw_comment_local_path']) != proxy['raw_comment_file_sha256'] or read(proxy['raw_comment_local_path']) != proxy['comment']:
        raise ValueError('Original actual proxy comment bytes must be present')
    provider_projected = dict(app_ids=apps, state='stopped', owned_container_count=0,
        observed_utc=provider['utc'], original_private_file_sha256=sha(close/'provider.json'),
        projection='Actor identities and unrelated rows omitted; full private original retained.',
        apps=[dict(app_id=x['app_id'], lifecycle={k: x['lifecycle'][k] for k in ('state','created_at','stopped_at')})
              for x in provider['original_app_info']])
    out.mkdir(parents=True, exist_ok=False)
    dump(out/'PUBLICATION_INTENT.json', dict(utc=datetime.now(timezone.utc).isoformat(),
        source_files=sources, original_sibling=reference,
        new_oracle_sha256=sha(ev/'LOCAL_ORACLE_AUDIT.json'), once_only=True,
        new_model_calls=0, new_raw_or_symbolic_scoring=0, old_binary_state_loaded=False))
    selected = {n: x for n, x in envelope['artifact_manifest'].items() if n not in OMIT and not n.endswith('.pt')}
    archive_original(ev, out/'REPLACEMENT_ORIGINAL_PUBLIC_MEMBERS.tar.gz', selected)
    with (ev/'LOCAL_ORACLE_AUDIT.json').open('rb') as source, (out/'REPLACEMENT_LOCAL_ORACLE.json.gz').open('xb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as stream: shutil.copyfileobj(source, stream)
    with gzip.open(out/'REPLACEMENT_LOCAL_ORACLE.json.gz', 'rb') as stream:
        h = hashlib.sha256()
        for block in iter(lambda: stream.read(2**20), b''): h.update(block)
    if h.hexdigest() != sha(ev/'LOCAL_ORACLE_AUDIT.json'):
        raise ValueError('Original full oracle gzip readback differs')
    dump(out/'ORIGINAL_SIBLING_AND_FAILURE_REFERENCE.json', reference)
    dump(out/'PRECLAIM_FAILURE_REFERENCE.json', dict(target_commit='e8f57a1973cacf7efd508b59df9a94fda1539a1a', packet=str(preclaim), manifest_sha256=sha(preclaim/'MANIFEST.json'), proof_file_sha256=spec['preclaim_proof_file_sha256'], original_private_manifest_sha256=spec['preclaim_manifest_file_sha256'], scientific_work=0, guard_claim=False, terminal=False, reserved_cents_retained=655))
    dump(out/'OWNER_PROXY_DECISION_PROJECTION.json', projection(proxy)[0])
    dump(out/'REPLACEMENT_ORIGINAL_ENVELOPE.json', envelope)
    shutil.copyfile(close/'ledger.json', out/'ORIGINAL_FULL_LEDGER.json')
    dump(out/'PROVIDER_PROJECTION.json', provider_projected)
    dump(out/'INTENT_PROJECTION.json', projected)
    dump(out/'PROJECTION.json', dict(files=selected,
        omitted={n:x for n,x in envelope['artifact_manifest'].items() if n not in selected},
        archive_sha256=sha(out/'REPLACEMENT_ORIGINAL_PUBLIC_MEMBERS.tar.gz'),
        original_manifest_digest=digest(envelope['artifact_manifest']),
        original_intent_file_sha256=sha(ev/'intent.json'),
        projected_intent_file_sha256=sha(out/'INTENT_PROJECTION.json'),
        removed_host_locators_sha256=removed, original_oracle_file_sha256=sha(ev/'LOCAL_ORACLE_AUDIT.json'),
        private_state_binary_omitted=True, public_state_hash_is_not_external_binary_loading=True))
    # The only paired decision call, after all bindings and an exclusive output intent.
    decision = nc_result(ids, old['question_correct'], oracle['question_correct'])
    dump(out/'REGISTERED_NC_DECISION.json', decision)
    dump(out/'SUMMARY.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        physical_runs={ORIGINAL_NC400:dict(status='completed',correct=old['correct'],total=1319,
            logical_stops=old['logical_stops'],state_sha256=old['state_sha256']),
            PARENT_RUN:dict(status='failed', scientific_endpoint_missing=True, filled_as_zero=False,
                original_evidence_sha256=PARENT_FAILURE_DIGEST),
            RUN:dict(status='completed',correct=oracle['correct'],total=1319,
                logical_stops=oracle['logical_stops'],state_sha256=oracle['state_sha256'])},
        logical_cells=2, physical_runs_count=3, complete_students_updates=1024,
        complete_students_targets=2097148, technical_unknown=0,
        actual_result_external_A4='PENDING', S1_runtime_admitted=False,
        reserved_cents=2620, preclaim_only_entry_calls=1, preclaim_only_has_no_scientific_terminal=True, reservation_is_actual_expense=False,
        owner_replacement_decision_blinded_to_NC400=False,
        post_failure_engineering_exception=True, original_failed_parent_retained=True,
        new_model_calls=0, new_scoring=0, new_bootstrap=False))
    for name, value in (('ACCEPTED_PUBLICATION.json',code),('ACCEPTED_ANALYSIS.json',analysis),
                        ('ACCEPTED_PARENT_A4.json',sent['release']['parent_disposition_review'])):
        dump(out/name, {k:v for k,v in value.items() if k!='local_report_path'})
    dump(out/'SOURCE_BINDING.json', dict(runtime_source_files=spec['source_files'],
        spec_sha256=digest(spec), analysis_source_files=analysis['source_files'],
        publication_source_files=sources, execution_commit=sent['release']['execution_commit']))
    shutil.copyfile(__file__, out/'PUBLICATION_SOURCE.py')
    (out/'README.md').write_text('''# Complete NC logical pair with retained preemption and preclaim failure

Original NC400 is referenced at its immutable original packet; its raw archive,
full state and oracle are not rerun or rebuilt. The independent NC3200 replacement
has its own complete source-bound 1024-step/2097148-target/1319-question oracle,
claim and STOPPED0 proof. The original NC3200 remains failed after preemption,
with896 saved steps, no checkpoint and no endpoint; it is never assigned zero.

The owner approved this one same-recipe replacement after the original NC400954
count was public. This is a disclosed post-failure engineering exception, not a
pre-registered or blinded decision. A further schema-repair entry required the actual owner-proxy decision and
independent exact53-source audit. Its predecessor had zero claim/model/output;
original fences and655-cent preclaim reservation remain. No automatic retry is
authorized. All original failure costs and655-cent reservations remain preserved.

The reviewed paired >=5pp stop rule is computed once from the two complete
Boolean tables. New actual independent A4 is required; this publication cannot
admit S1. There is no new scoring, bootstrap, model or checkpoint loading here.
Raw/metadata archive projection is byte-readback checked. Private intent and
state binary are omitted with explicit original hashes; provider actor identities
and known host report/owner-comment file locators are projected separately. Public state hashes do
not claim that the external reviewer read the private binary. Original P0
internal-only scope and all frozen parsing/length-cap rules are unchanged.
''')
    dump(out/'MANIFEST.json', manifest(out)); print(str(out))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for key in ('root','out','code-review','analysis-review'): parser.add_argument('--'+key,required=True)
    args = parser.parse_args(); publish(args.root,args.out,args.code_review,args.analysis_review)
