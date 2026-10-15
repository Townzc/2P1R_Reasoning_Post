"""Publish complete S1 evidence and the registered first-pair decision once.

Read-only with respect to science and providers. No model, tokenizer, symbolic
scorer, private binary deserialization, remote write, or approval writer. Saved
proofs and Boolean tables are checked before any publication directory exists.
The exact helper review is separate from the immutable full runtime review.
"""
import argparse
from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path
import shutil

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest, verify
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps
from experiments.learning_regime_p009.stage1_s1_funded_binding import (
    CAMPAIGN, RUNS, FIRST_PAIR, validate, intent, marker, dispatch_key, logical_key,
)
from experiments.learning_regime_p009.stage1_s1_score_proof import verify_score_payload
from experiments.learning_regime_p009.stage1_analysis import first_pair_decision
from scripts.publish_p009_stage0_result import archive_original

SPEC = Path('reports/p009_20261014/stage1_s1_runtime_preflight_v1/ADMISSION.json')
SCOPE = 'p009-stage1-S1-observation-and-complete-publication-code'
SOURCE_NAMES = (
    'scripts/p009_s1_observe.py', 'scripts/publish_p009_s1_results.py',
    'scripts/publish_p009_stage0_result.py',
)
OMIT = {'intent.json', 'compact_evidence.tar.gz', 'compact_manifest.json', 'bundle_receipt.json'}
PUBLIC_RUNS = Path('reports/p009_20261014/stage1_s1_results_v1')
NC_PACKET = Path('reports/p009_20261014/stage1_nc_guard_repair_complete_v1')
NC400_PACKET = Path('reports/p009_20261014/stage1_nc_preemption_disposition_v1')


def require(value, message):
    if not value:
        raise ValueError(message)


def source_review(path, spec):
    value = read(path)
    require(value.get('scope') == SCOPE and value.get('decision') in ('PASS', 'PASS-WITH-NOTES')
        and value.get('source_files') == {p:sha(p) for p in SOURCE_NAMES}
        and len(value.get('target_commit', '')) == 40 and len(value.get('report_commit', '')) == 40
        and sha(value['local_report_path']) == value['report_sha256'],
        'Actual exact complete helper code report required')
    for name, expected in spec['source_files'].items():
        require(sha(name) == expected, 'Original full reviewed runtime bytes changed')
    return value


def projection(value, prefix=''):
    removed = {}
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            path = prefix+'.'+key if prefix else key
            if key in ('local_report_path', 'source_snapshot', 'raw_comment_local_path'):
                removed[path] = digest(item)
            else:
                output[key], extra = projection(item, path)
                removed.update(extra)
    elif isinstance(value, list):
        output = []
        for index, item in enumerate(value):
            projected, extra = projection(item, prefix+'.'+str(index))
            output.append(projected)
            removed.update(extra)
    else:
        output = value
    return output, removed


def complete_boolean_table(value, ids, run):
    scores = value.get('question_correct')
    require(value.get('passed') is True and value.get('run_id') == run
        and value.get('total') == 500 and value.get('technical_unknown') == 0
        and value.get('updates_verified') == 1024 and value.get('targets_verified') == 2097148
        and isinstance(scores, dict) and set(scores) == set(ids)
        and len(ids) == len(set(ids)) == 500 and all(type(x) is bool for x in scores.values())
        and value.get('correct') == sum(scores.values()), 'Complete original500 Boolean table required')
    return scores


def check_complete(root, run, spec):
    require(run in RUNS, 'Only original registered S1 slots')
    ev = root/'exports'/run/'evidence'; close = root/'closeouts'/run
    generated = root/'oracles'/run; scored = root/'scores'/run
    for folder in (generated, scored):
        require(folder.is_dir() and not any(p.name == 'FAILED.json' for p in folder.rglob('*')),
            'Partial or failed oracle/scoring evidence must be retained, not published as complete')
    sent = read(ev/'intent.json'); dispatch = read(root/'runs'/run/'dispatch_intent.json')
    env = read(root/'runs'/run/'result.json'); ledger = read(close/'ledger.json')
    provider = read(close/'provider.json'); collected = read(close/'COMPLETED.json')
    validate(spec, sent['plan'], run, sent['release'])
    require(sent['spec'] == spec and sent['run_id'] == run and dispatch['run_id'] == run
        and dispatch['release'] == sent['release'] and dispatch['plan'] == sent['plan']
        and read(ev/'result.json') == env['result'], 'Original source, dispatch and returned envelope differ')
    pre = 'midpoint/'+CAMPAIGN+'/'; claim = ledger[pre+'claim/'+run]
    terminal = ledger[pre+'terminal/'+run]
    require(terminal == env['receipt'] and terminal['status'] == 'completed'
        and terminal['run_id'] == run and claim['run_id'] == run
        and claim['reserved_cents'] == terminal['actual_cost_cents'] == 655
        and terminal['attempt_id'] == claim['attempt_id']
        and ledger[pre+'attempt/'+run+'/'+claim['attempt_id']] == claim
        and terminal['claim_sha256'] == digest(claim)
        and terminal['evidence_sha256'] == digest(env['artifact_manifest'])
        and ledger[pre+'intent/'+run] == intent(spec,run)
        and claim['intent_sha256'] == digest(intent(spec,run))
        and claim['plan_sha256'] == digest(sent['plan'])
        and any_marker_matches(spec, run, sent['release'], ledger)
        and all(ledger.get(k) == v for k,v in spec['required_records'].items()),
        'Original completed claim, permanent fences and failed dependencies required')
    require(collected['passed'] is True and collected['ledger_sha256'] == sha(close/'ledger.json')
        and collected['original_receipt_sha256'] == sha(root/'runs'/run/'result.json'),
        'Actual single closeout proof differs')
    first = [] if run in FIRST_PAIR else sent['release']['futility_review']['first_pair_app_ids']
    apps = list(dict.fromkeys(spec['required_stopped_app_ids']+first+[dispatch['provider_app_id']]))
    require(provider['app_ids'] == apps and provider['state'] == 'stopped'
        and provider['owned_container_ids'] == [], 'Complete original app roster must be STOPPED0')
    validate_stopped_apps(apps, provider['original_app_info'], provider['owned_containers'])
    if run not in FIRST_PAIR:
        require(all(ledger.get(k) == v for k,v in sent['release']['futility_review']['required_terminal_records'].items()),
            'Actual reviewed first-pair terminals must remain')
    require(abs(sent['hard_deadline_epoch']-sent['worker_started_epoch']-4500) < .001
        and terminal['finished_epoch'] <= sent['hard_deadline_epoch'], 'Original full worker cap exceeded')
    for key in ('runtime_review','core_review','input_review','G0_review','internal_only_review','NC_A4_review'):
        review = sent['release'][key]
        require(sha(review['local_report_path']) == review['report_sha256'], 'Original exact full reports must be present')
    if run not in FIRST_PAIR:
        review = sent['release']['futility_review']
        require(sha(review['local_report_path']) == review['report_sha256'], 'Actual first-pair A4 report must be present')
    proxy = sent['release']['budget_owner_decision']
    require(sha(proxy['raw_comment_local_path']) == proxy['raw_comment_file_sha256']
        and read(proxy['raw_comment_local_path']) == proxy['comment'], 'Original owner proxy bytes changed')
    raw = read(generated/'COMPLETED.json'); oracle = read(scored/'LOCAL_ORACLE_AUDIT.json')
    rows = read(generated/'SCORING_ROWS.json'); score_done = read(scored/'COMPLETED.json')
    score_intent = read(scored/'INTENT.json'); control = read(scored/'job/COMPLETED.json')
    control_intent = read(scored/'job/INTENT.json')
    require(raw.get('passed') is True and raw.get('run_id') == run
        and raw.get('outputs_decoded') == 500 and raw.get('technical_unknown') == 0
        and raw.get('updates_verified') == 1024 and raw.get('targets_verified') == 2097148
        and raw.get('spec_sha256') == digest(spec) and raw.get('source_files') == spec['source_files']
        and raw.get('artifact_digest') == digest(env['artifact_manifest'])
        and raw.get('state_sha256') == env['artifact_manifest']['checkpoint_1024/state.pt']['sha256']
        and raw.get('original_intent_file_sha256') == sha(ev/'intent.json')
        and raw.get('original_receipt_file_sha256') == sha(root/'runs'/run/'result.json')
        and raw.get('original_ledger_file_sha256') == sha(close/'ledger.json')
        and raw.get('original_provider_file_sha256') == sha(close/'provider.json')
        and raw.get('scoring_rows_file_sha256') == sha(generated/'SCORING_ROWS.json')
        and raw.get('decoded_file_sha256') == sha(generated/'DECODED_ROWS.json')
        and raw.get('full_runtime_lineage_admission_checked') is True
        and raw.get('symbolic_scoring_performed') is False, 'Original complete full state/raw oracle required')
    ids = [r['problem_id'] for r in read(root.parent/'stage1_s1_inputs_r1/S1_ENDPOINT.json')]
    complete_boolean_table(oracle, ids, run)
    require([r['problem_id'] for r in rows] == ids, 'Frozen500 endpoint order changed')
    binding = oracle['original_binding']
    require(binding == score_intent['binding'] == read(scored/'job/BINDING.json')
        and binding['run_id'] == run and binding['spec_sha256'] == digest(spec)
        and binding['source_files'] == spec['source_files']
        and binding['original_generation_proof_file_sha256'] == sha(generated/'COMPLETED.json')
        and binding['original_scoring_rows_file_sha256'] == sha(generated/'SCORING_ROWS.json')
        and binding['original_receipt_file_sha256'] == sha(root/'runs'/run/'result.json')
        and binding['original_state_sha256'] == raw['state_sha256']
        and binding['actual_runtime_report_sha256'] == sent['release']['runtime_review']['report_sha256']
        and binding['local_scoring_versions'] == spec['local_scoring_versions']
        and binding['local_scenario_seconds'] == 5160.0
        and score_intent['local_wall_seconds'] == 6000 and score_intent['cleanup_allowance_seconds'] == 5,
        'Original independent frozen local scoring input/source/window differs')
    require(score_done['passed'] is True and score_done['oracle_file_sha256'] == sha(scored/'LOCAL_ORACLE_AUDIT.json')
        and score_done['control_file_sha256'] == sha(scored/'job/COMPLETED.json')
        and oracle['full_generation_oracle_file_sha256'] == sha(generated/'COMPLETED.json')
        and oracle['scoring_control_completed_file_sha256'] == sha(scored/'job/COMPLETED.json')
        and oracle['scoring_payload_completed_file_sha256'] == sha(scored/'job/payload/COMPLETED.json')
        and oracle['audit_samples_file_sha256'] == sha(scored/'job/payload/AUDIT_SAMPLES.json')
        and oracle['state_sha256'] == raw['state_sha256'] and oracle['artifact_digest'] == raw['artifact_digest']
        and oracle['logical_stops'] == raw['logical_stops'] and control['child_exit_code'] == 0
        and control['local_seconds'] == control_intent['local_seconds']
        and type(control['local_seconds']) is int and 0 < control['local_seconds'] <= 6000
        and math.isfinite(oracle['local_total_observed_seconds'])
        and 0 <= oracle['local_total_observed_seconds'] < 6000,
        'Complete independent scoring process/proof/hash chain required')
    checked = verify_score_payload(scored/'job/payload', rows, binding, control['local_seconds'])
    require(checked['passed'] and oracle['question_correct'] == checked['question_correct']
        and oracle['unique_symbolic_pairs'] == checked['unique_symbolic_pairs']
        and oracle['independent_adjudication_complete'] is False and oracle['external_A4_pending'] is True
        and oracle['scientific_G1_admitted'] is False,
        'Existing journal verdicts and still-pending actual adjudication must be reported exactly')
    projected, removed = projection(sent)
    require('/Users/' not in json.dumps(projected), 'Unprojected private host locator')
    provider_projection = dict(app_ids=apps, state='stopped', owned_container_count=0,
        observed_utc=provider['utc'], original_private_file_sha256=sha(close/'provider.json'),
        projection='Actor identities and unrelated rows omitted; full original private file retained.',
        apps=[dict(app_id=x['app_id'], lifecycle={k:x['lifecycle'][k]
              for k in ('state','created_at','stopped_at')}) for x in provider['original_app_info']])
    return dict(ev=ev, close=close, generated=generated, scored=scored, sent=sent, envelope=env,
        raw_proof=raw, oracle=oracle, ids=ids, ledger=ledger, provider=provider_projection,
        projected_intent=projected, removed=removed, original_app_id=dispatch['provider_app_id'])


def any_marker_matches(spec, run, release, ledger):
    expected = marker(spec,run,release)
    return all(ledger.get(k) == expected for k in (dispatch_key(run),logical_key(run)))


def file_roster(root, omit=()):
    files = {}
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(), 'Symlink evidence is not an original regular file')
        if p.is_file():
            name = p.relative_to(root).as_posix()
            if name not in omit:
                files[name] = dict(bytes=p.stat().st_size,sha256=sha(p))
    return files


def publish_run(root, out, run, code_path):
    require(not out.exists(), 'Prior or partial publication blocks whole-tool repetition')
    spec = read(SPEC); code = source_review(code_path,spec); item = check_complete(root,run,spec)
    env=item['envelope'];ev=item['ev'];scored=item['scored']; generated=item['generated']
    selected = {n:v for n,v in env['artifact_manifest'].items()
                if n not in OMIT and not n.endswith(('.pt','.safetensors'))}
    generation_files=file_roster(generated)
    score_files=file_roster(scored, ('job/worker.log',))
    excluded_log=scored/'job/worker.log'
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'PUBLICATION_INTENT.json',dict(run_id=run,utc=datetime.now(timezone.utc).isoformat(),
        source_files={p:sha(p) for p in SOURCE_NAMES}, new_model_calls=0,
        new_raw_decoding=0,new_symbolic_scoring=0,new_state_deserializations=0))
    archive_original(ev,out/'ORIGINAL_GENERATION_PUBLIC_MEMBERS.tar.gz',selected)
    archive_original(generated,out/'ORIGINAL_GENERATION_ORACLE.tar.gz',generation_files)
    archive_original(scored,out/'ORIGINAL_SCORING_EVIDENCE.tar.gz',score_files)
    for source,name in [(generated/'COMPLETED.json','GENERATION_PROOF.json'),
        (scored/'LOCAL_ORACLE_AUDIT.json','LOCAL_ORACLE_AUDIT.json'),
        (scored/'job/payload/AUDIT_SAMPLES.json','AUDIT_SAMPLES.json'),
        (item['close']/'ledger.json','ORIGINAL_FULL_LEDGER.json')]:
        shutil.copyfile(source,out/name)
    dump(out/'ORIGINAL_ENVELOPE.json',env)
    dump(out/'PROVIDER_PROJECTION.json',item['provider'])
    dump(out/'INTENT_PROJECTION.json',item['projected_intent'])
    dump(out/'PROJECTION.json',dict(generation_files=selected,generation_oracle_files=generation_files,
        original_scoring_files=score_files,
        omitted_generation={n:v for n,v in env['artifact_manifest'].items() if n not in selected},
        omitted_scoring_worker_log=dict(bytes=excluded_log.stat().st_size,sha256=sha(excluded_log)) if excluded_log.exists() else None,
        original_intent_file_sha256=sha(ev/'intent.json'),
        projected_intent_file_sha256=sha(out/'INTENT_PROJECTION.json'),
        removed_host_locators_sha256=item['removed'], original_artifact_digest=digest(env['artifact_manifest']),
        public_checkpoint_SHA_is_not_external_binary_read=True))
    dump(out/'SOURCE_BINDING.json',dict(runtime_source_files=spec['source_files'],spec_sha256=digest(spec),
        helper_source_files={p:sha(p) for p in SOURCE_NAMES},
        execution_commit=item['sent']['release']['execution_commit'],
        runtime_report_sha256=item['sent']['release']['runtime_review']['report_sha256'],
        NC_A4_report_sha256=item['sent']['release']['NC_A4_review']['report_sha256']))
    dump(out/'ACCEPTED_HELPER_REVIEW.json',projection(code)[0])
    oracle=item['oracle']
    dump(out/'SUMMARY.json',dict(run_id=run,app_id=item['original_app_id'],correct=oracle['correct'],
        total=500,logical_stops=oracle['logical_stops'],technical_unknown=0,updates=1024,targets=2097148,
        state_sha256=oracle['state_sha256'],reserved_cents=655,reservation_is_actual_expense=False,
        unique_symbolic_pairs=oracle['unique_symbolic_pairs'],
        outer_timeout_over_half_percent=oracle['outer_timeout_over_half_percent'],
        fallback_over_two_percent=oracle['fallback_over_two_percent'],
        original_labels_unchanged=True,independent_adjudication_complete=False,
        actual_result_A4='PENDING',scientific_G1_admitted=False,remaining_S1_admitted=False,
        new_raw_decoding=0,new_symbolic_scoring=0,new_state_deserializations=0,new_model_calls=0))
    (out/'README.md').write_text('''# Complete registered S1 endpoint; actual adjudication/A4 pending

This once-only packet copies the full original raw and scoring evidence, including
all confirmed symbolic failures/timeouts and fixed disagreement/fallback samples.
Existing Boolean verdicts are retained; no label correction, raw decoding, model
state deserialization or symbolic call occurs here. The fixed boxed denominator
comes from the original sample record, without a new extraction. Independent
adjudication and actual outcome A4 remain pending; this is not permission for a
later slot or G1. All prior failed NC identities and reservations remain bound.

Archives are read back byte-for-byte. The private intent, state binary, packaging
metadata and scoring worker log are omitted with original hashes. Known host
report/comment locators and provider actor identities are explicitly projected;
full private originals remain. A public state SHA does not assert an external
read of the private binary. The per-slot655 cents is reserved, not an invoice.
''')
    dump(out/'MANIFEST.json',manifest(out))
    return dict(out=str(out),run_id=run,correct=oracle['correct'],external_A4_pending=True)


def nc_metadata(spec):
    require(sha(NC_PACKET/'MANIFEST.json') == spec['NC_packet_manifest_sha256'], 'Fixed actual NC packet changed')
    members=read(NC_PACKET/'MANIFEST.json'); ref=read(NC_PACKET/'ORIGINAL_SIBLING_AND_FAILURE_REFERENCE.json')
    for name in ('REPLACEMENT_LOCAL_ORACLE.json.gz','ORIGINAL_SIBLING_AND_FAILURE_REFERENCE.json'):
        require(sha(NC_PACKET/name)==members[name]['sha256'], 'Referenced NC metadata changed')
    require(sha(NC400_PACKET/'MANIFEST.json')==ref['manifest_sha256'], 'Fixed NC400 parent packet changed')
    old=NC400_PACKET/'nc_s17_n400/LOCAL_ORACLE_AUDIT.json.gz'
    require(sha(old)==ref['original_oracle_gzip_sha256'], 'Original NC400 Boolean metadata changed')
    with gzip.open(old,'rt') as f: low=json.load(f)
    with gzip.open(NC_PACKET/'REPLACEMENT_LOCAL_ORACLE.json.gz','rt') as f: high=json.load(f)
    require(low['correct']==954 and high['correct']==967 and low['passed'] and high['passed']
        and low['technical_unknown']==high['technical_unknown']==0, 'Actual accepted NC metadata required')
    return list(low['question_correct']),low['question_correct'],high['question_correct']


def publish_first_pair(root,out,code_path,analysis_path):
    require(not out.exists(), 'Prior or partial first-pair publication blocks repetition')
    spec=read(SPEC);code=source_review(code_path,spec);analysis=read(analysis_path)
    require(analysis.get('scope')=='p009-stage1-registered-analysis-and-stop-code'
        and analysis.get('decision') in ('PASS','PASS-WITH-NOTES')
        and analysis.get('target_commit')=='2c7d6b5ce7fe7d9c23ad59dc6e185493390f9a81'
        and sha(analysis['local_report_path'])==analysis['report_sha256'], 'Actual original registered analysis review required')
    for path,h in analysis['source_files'].items():require(sha(path)==h,'Original registered analysis source changed')
    originals={};reference={};ids=None
    for run in FIRST_PAIR:
        item=check_complete(root,run,spec);published=PUBLIC_RUNS/run
        verify(published,read(published/'MANIFEST.json'))
        require(read(published/'LOCAL_ORACLE_AUDIT.json')==item['oracle'], 'Original published S1 oracle differs')
        require(ids is None or ids==item['ids'],'Both complete500 frozen endpoint IDs required')
        ids=item['ids']; originals[run]=item
        reference[run]=dict(packet=str(published),manifest_sha256=sha(published/'MANIFEST.json'),
            original_app_id=item['original_app_id'],terminal=item['envelope']['receipt'],
            original_oracle_sha256=sha(published/'LOCAL_ORACLE_AUDIT.json'))
    require(len({originals[k]['original_app_id'] for k in FIRST_PAIR}) == 2,
        'Two distinct original first-pair applications required')
    require(len({originals[k]['sent']['release']['NC_A4_review']['report_sha256'] for k in FIRST_PAIR}) == 1,
        'The pair must share the same actual NC A4 report')
    nc_ids,low,high=nc_metadata(spec)
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'PUBLICATION_INTENT.json',dict(utc=datetime.now(timezone.utc).isoformat(),
        sources={p:sha(p) for p in SOURCE_NAMES},originals=reference,new_scoring=0,new_generations=0))
    # The original registered first-pair point rule, once. No bootstrap is run here.
    value=first_pair_decision(nc_ids,low,high,ids,
        dict(n400=originals[FIRST_PAIR[0]]['oracle']['question_correct'],
             n3200=originals[FIRST_PAIR[1]]['oracle']['question_correct']),s1_G0_accepted=True)
    dump(out/'REGISTERED_FIRST_PAIR_DECISION.json',value)
    dump(out/'ORIGINAL_COMPLETE_ENDPOINT_REFERENCES.json',reference)
    dump(out/'REVIEW_BINDING.json',dict(NC_A4_report_sha256=originals[FIRST_PAIR[0]]['sent']['release']['NC_A4_review']['report_sha256'],
        S1_G0_report_sha256=spec['G0_report_sha256'],spec_sha256=digest(spec),source_files=spec['source_files'],
        actual_adjudication_and_A4='PENDING',remaining_S1_runtime_admitted=False,
        first_pair_run_ids=list(FIRST_PAIR),first_pair_app_ids=[originals[k]['original_app_id'] for k in FIRST_PAIR],
        required_terminal_records={'midpoint/'+CAMPAIGN+'/terminal/'+k:originals[k]['envelope']['receipt'] for k in FIRST_PAIR}))
    dump(out/'ACCEPTED_ANALYSIS_REVIEW.json',projection(analysis)[0])
    dump(out/'ACCEPTED_HELPER_REVIEW.json',projection(code)[0])
    (out/'README.md').write_text('''# Original S1 seed17 first-pair decision; actual A4 still required

Both500-row endpoints have complete original generation/state and frozen local
scoring proofs and STOPPED0 evidence. The original registered point futility rule
is evaluated once from their saved Boolean tables. No bootstrap, symbolic score,
raw decode, model call or binary load is added. The accepted NC Boolean metadata
are referenced by the original first_pair_decision function; old NC raw evidence
and archives are not rebuilt.

Fixed disagreement/fallback samples and original failed symbolic attempts are
in each endpoint packet. Independent adjudication and actual paired outcome A4
remain pending. Even a local continue decision does not authorize the later four
S1 slots. The original gap<2pp futility rule and every source/budget/runtime gate
remain; no new scientific arm or G1 claim is created here.
''')
    dump(out/'MANIFEST.json',manifest(out))
    return dict(out=str(out),decision=value['decision'],actual_A4_pending=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','first-pair'])
    p.add_argument('--root',required=True);p.add_argument('--out',required=True)
    p.add_argument('--run',choices=list(RUNS));p.add_argument('--code-review',required=True)
    p.add_argument('--analysis-review');a=p.parse_args()
    if a.action=='run' and not a.run:p.error('--run required')
    if a.action=='first-pair' and not a.analysis_review:p.error('--analysis-review required')
    result=(publish_run(Path(a.root),Path(a.out),a.run,a.code_review) if a.action=='run'
        else publish_first_pair(Path(a.root),Path(a.out),a.code_review,a.analysis_review))
    print(json.dumps(result))
