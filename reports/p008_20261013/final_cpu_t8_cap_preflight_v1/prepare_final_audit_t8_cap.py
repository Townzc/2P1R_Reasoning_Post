"""PREPARED ONLY: freeze real completed inputs, then admit after real review.

No generation, cloud upload, dispatch, old-oracle rerun or automatic retry.
Use freeze -> publish an actual-byte I/O proposal -> admit after scoped review.
Any failed partial preparation is preserved and must be reconciled separately.
"""
from pathlib import Path
import argparse
import ast
import datetime
import hashlib
import json
import shutil
import subprocess
import time

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, manifest, verify
from experiments.sft_allocation_p008.audit_cap_binding import (
    CONFIG, PARENT_LABEL, PARENT_ARCHIVE, ARCHIVES, FAILED_STUDENTS, REPLACEMENTS, REPLACEMENT_CAMPAIGN, physical_roster, source_key,
    validate, validate_label, validate_all_labels)
from experiments.sft_allocation_p008.audit_bundle import CONTAINERS
from experiments.sft_allocation_p008.audit_t8_cap_records import KEY, CAP_SPEC, validate_cap_inputs, validate_cap_label, require_remote_cap_records
from experiments.sft_allocation_p008.completion_queue import require_handoff, transfer_record
from experiments.sft_allocation_p008.evidence_bundle import pack
from experiments.sft_allocation_p008.pool_lineage import PARENT_CAMPAIGN, CHILD_CAMPAIGN, CHILD_RUN
from experiments.sft_allocation_p008.provider_release import read_stopped_apps
from scripts.p008_final_cpu_guard import CURRENT_MODULE, require_current_entry

R = Path(__file__).resolve().parent
ROOT = R.parents[2]
STUDENT = R / 'student_completion_r1'
CHILD = R / 'd2_continuation_r1'
REPL = R / 'student_lr_replacements_r1'
FAILED = STUDENT / 'lr_preflight_failures_r1'
REPL_SPEC = ROOT / 'reports/p008_20261013/student_lr_replacement_admission_v1/ADMISSION.json'
OUT = STUDENT / 'final_audit_t8_cap_r1'
PUBLIC = ROOT / 'reports/p008_20261013/final_audit_t8_cap_admission_v1'
PROPOSAL = ROOT / 'reports/p008_20261013/final_audit_t8_cap_proposal_v1'
CLI = str(ROOT / '.local/midpoint_20261011/venv/bin/modal')
CPU_MODULE = ROOT / CURRENT_MODULE


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def code_review():
    review = read(R / 'CPU_T8_CAP_CODE_ACCEPTED.json')
    if (review['scope'] != 'p008_cpu_replacement_integrity_code'
            or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or sha(R / review['local_report_path']) != review['report_sha256']):
        raise ValueError('Real new lineage code review and original report required')
    names = next(ast.literal_eval(x.value) for x in ast.parse(CPU_MODULE.read_text()).body
                 if isinstance(x, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'SOURCES' for t in x.targets))
    source = {n: sha(ROOT / n) for n in names}
    require_current_entry(str(CPU_MODULE.relative_to(ROOT)), source)
    if source != review['source_files']:
        raise ValueError('Code review does not cover current exact CPU sources')
    for name, value in source.items():
        original = subprocess.check_output(['git', 'show', review['target_commit'] + ':' + name], cwd=ROOT)
        if hashlib.sha256(original).hexdigest() != value:
            raise ValueError('Review target/source bytes differ')
    return review, source


def exact_provider_id(provider):
    if provider['owned_containers'] or len(provider['apps']) != 1:
        raise ValueError('Expected one original released app for source')
    app = provider['apps'][0]
    if app.get('state', app.get('lifecycle', {}).get('state')) != 'stopped':
        raise ValueError('Earlier closeout was not stopped')
    return app['app_id']


def collect_local_labels():
    """Read earlier proofs without rerunning any old model/export/raw oracle."""
    labels, provider_ids = {}, {}
    reconciliation_path = R / 'interrupted_pools/pool_d2/reconciliation_r1/RECONCILIATION.json'
    preservation = R / 'interrupted_pools/pool_d2/preservation_r1'
    rec = read(reconciliation_path)
    parent_cfg = read(preservation / 'evidence/intent.json')['config']
    old_provider = read(CHILD / 'closeout_r1/provider.json')
    parent_app = next(x['app_id'] for x in old_provider['original_apps']
                      if x['app_id'] != exact_provider_id(read(R / 'closeouts/pool_d1/provider.json')))
    labels[PARENT_LABEL] = dict(campaign=PARENT_CAMPAIGN, run_id='pool_d2',
        config=parent_cfg, claim=rec['parent_claim'], terminal=rec['parent_terminal'],
        reconciliation=rec, reconciliation_json=reconciliation_path.read_text(),
        preserved_manifest=read(preservation / 'LOCAL_MANIFEST.json'))
    provider_ids[PARENT_LABEL] = parent_app
    replacement = read(REPL_SPEC)
    for name in sorted(FAILED_STUDENTS):
        p = replacement['parents'][name]
        original_manifest = FAILED / name / 'LOCAL_MANIFEST.json'
        labels[name] = dict(campaign=p['campaign'],run_id=name,
            config=replacement['original_spec']['configs'][name],claim=p['claim'],terminal=p['terminal'],
            reconciliation=replacement['zero_update_reconciliation'],reconciliation_json=(FAILED/'RECONCILED.json').read_text(),
            preserved_manifest=read(original_manifest),preserved_manifest_json=original_manifest.read_text(),
            replacement_spec=replacement)
        provider_ids[name] = p['provider_app_id']
    for name in sorted(physical_roster() - set(ARCHIVES)):

        root = R if name == 'pool_d1' else CHILD if name == CHILD_RUN else REPL if name in REPLACEMENTS else STUDENT
        campaign = PARENT_CAMPAIGN if name == 'pool_d1' else CHILD_CAMPAIGN if name == CHILD_RUN else REPLACEMENT_CAMPAIGN if name in REPLACEMENTS else read(STUDENT / 'plan.json')['campaign_id']
        closeout = root / ('closeout_r1' if name == CHILD_RUN else 'closeouts/' + name)
        evidence = root / ('export_r1/evidence' if name == CHILD_RUN else 'exports/' + name + '/evidence')
        envelope = read(root / 'runs' / name / 'result.json')
        terminal = envelope['receipt']
        if terminal['status'] != 'completed':
            raise ValueError('Missing or failed retained source; do not silently drop a label')
        ledger = read(closeout / 'ledger.json')
        prefix = 'midpoint/' + campaign + '/'
        claim = ledger[prefix + 'claim/' + name]
        cfg = read(evidence / 'intent.json')['config']
        oracle_path = evidence / 'LOCAL_ORACLE_AUDIT.json'
        oracle = read(oracle_path)
        if (terminal != ledger[prefix + 'terminal/' + name]
                or terminal['claim_sha256'] != digest(claim)
                or oracle['passed'] is not True
                or oracle.get('artifact_digest', oracle.get('manifest_digest')) != digest(envelope['artifact_manifest'])
                or digest(envelope['artifact_manifest']) != terminal['evidence_sha256']):
            raise ValueError('Original completed terminal/claim/local oracle mismatch')
        if name not in ('pool_d1', CHILD_RUN):
            expected = read(REPL / (name + '.json')) if name in REPLACEMENTS else read(R / 'student_preparation_r1' / (name + '.json'))
            if (cfg != expected or oracle['outputs_rescored'] != 1319
                    or oracle['updates_verified'] != cfg['updates']
                    or oracle['targets_verified'] != cfg['targets']):
                raise ValueError('Incomplete exact student dose or endpoint oracle')
        labels[name] = dict(campaign=campaign, run_id=name, config=cfg, claim=claim,
                            envelope=envelope, local_oracle=oracle,
                            local_oracle_json=oracle_path.read_text())
        if name not in ('pool_d1', CHILD_RUN):
            labels[name]['original_student_spec'] = replacement['original_spec']
            if name != 'base':
                inputs = R / 'student_preparation_r1/inputs'
                labels[name]['frozen_input_bytes'] = dict(manifest_json=(inputs/'manifest.json').read_text(),
                    plan_json=(inputs/cfg['plan_file']).read_text())
            if name in REPLACEMENTS:
                labels[name]['replacement_spec'] = replacement
        if cfg.get('training_multiple') == 8:
            labels[name]['t8_operational_evidence'] = dict(intent_json=(evidence/'intent.json').read_text(),
                original_ledger_intent=ledger[prefix+'intent/'+name],
                amendment_record=ledger[KEY], supplement_record=ledger[KEY+'/reserved/'+name])
        provider_ids[name] = exact_provider_id(read(closeout / 'provider.json'))
    if set(labels) != physical_roster() or len(set(provider_ids.values())) != 24:
        raise ValueError('All24 exact physical sources required')
    return labels, provider_ids



def operational_basis(labels):
    cap_spec = read(ROOT/'reports/p008_20261013/student_t8_cap_9600_v1/ADMISSION.json')
    if digest(cap_spec) != CAP_SPEC:
        raise ValueError('Exact published T8 cap admission required')
    records = {}
    for name in cap_spec['runs']:
        evidence = labels[name]['t8_operational_evidence']
        if KEY in records and records[KEY] != evidence['amendment_record']:
            raise ValueError('Original global supplement differs between collected ledgers')
        records[KEY] = evidence['amendment_record']
        records[KEY+'/reserved/'+name] = evidence['supplement_record']
    return dict(t8_cap_spec=cap_spec, t8_cap_ledger_records=records,
        t8_runtime_source_files=read(ROOT/'reports/p008_20261013/student_t8_cap_9600_v1/SOURCE_BUNDLE.json'))


def remote_preflight(plan, owner, original, labels, ids, require_inputs_absent):
    """Read-only actual lifecycle and original claim/terminal comparison."""
    import modal
    from modal.exception import NotFoundError
    if time.time() + 4000 > plan['deadline_epoch']:
        raise ValueError('Complete finite CPU window unavailable')
    containers = json.loads(subprocess.check_output([CLI, 'container', 'list', '--json'], text=True))
    apps = read_stopped_apps(CLI, [ids[n] for n in sorted(ids)], containers)
    db = modal.Dict.from_name('sft-allocation-midpoint-claims-v1', create_if_missing=False)
    volume = modal.Volume.from_name('sft-allocation-midpoint-v1', create_if_missing=False)
    require_handoff(db, plan, original, owner, 'audit')
    operational = operational_basis(labels)
    operational['labels'] = {n:dict(claim=x['claim']) for n,x in labels.items()}
    require_remote_cap_records(db, operational)
    prefix = 'midpoint/' + plan['campaign_id'] + '/'
    if any(db.get(prefix + k + '/audit') is not None for k in ('claim', 'intent', 'terminal')):
        raise ValueError('Existing or uncertain CPU attempt; never retry')
    if any(k.startswith(prefix + 'audit/') or k.startswith(prefix + 'attempt/audit/') for k in db.keys()):
        raise ValueError('Existing CPU attempt/unit evidence')
    if (OUT / 'runs/audit').exists():
        raise ValueError('Original CPU dispatch directory exists')
    for name, label in labels.items():
        terminal = label['terminal'] if name in ARCHIVES else label['envelope']['receipt']
        if (db.get(source_key(label, 'claim')) != label['claim']
                or db.get(source_key(label, 'terminal')) != terminal):
            raise ValueError('Actual source claim/terminal changed')
    suffixes = ('audit', CONFIG['input_directory']) if require_inputs_absent else ('audit',)
    for suffix in suffixes:
        try:
            list(volume.iterdir('/' + plan['campaign_id'] + '/' + suffix))
        except NotFoundError:
            continue
        raise ValueError('Existing remote path; reconcile rather than overwrite')
    if time.time() + 4000 > plan['deadline_epoch']:
        raise ValueError('Full window exhausted during preflight')
    return dict(utc=utc(), apps=apps, containers=containers)


def freeze():
    if OUT.exists() or PUBLIC.exists() or PROPOSAL.exists():
        raise ValueError('Existing immutable preparation; preserve and reconcile')
    review, source = code_review()
    labels, ids = collect_local_labels()  # Fails before new output if any source is missing.
    plan, original, owner = read(STUDENT / 'plan.json'), read(R / 'plan.json'), read(R / 'OWNER_STUDENT_COMPLETION.json')
    provider = remote_preflight(plan, owner, original, labels, ids, True)
    student_spec = read(ROOT / 'reports/p008_20261013/student_admission_v1/ADMISSION.json')
    OUT.mkdir()
    dump(OUT / 'PREPARATION_INTENT.json', dict(utc=utc(), source_files=source,
        labels=sorted(labels), model_calls=0, rule='Preserve any partial output; no whole-preparation replay'))
    inputs = OUT / CONFIG['input_directory']; inputs.mkdir()
    for label_name, archive_name in ARCHIVES.items():
        original_source = (R / 'interrupted_pools/pool_d2/preservation_r1/evidence'
                           if label_name == PARENT_LABEL else FAILED / label_name / 'evidence')
        staging = OUT / ('original_copy_' + label_name); staging.mkdir()
        contents = labels[label_name]['preserved_manifest']
        original_failure = read(original_source / 'failure_manifest.json')
        if set(contents) != set(original_failure) | {'failure_manifest.json'}:
            raise ValueError('Failure preservation contains foreign or missing original file')
        for name, record in contents.items():
            path = original_source / name
            if path.is_symlink() or path.stat().st_size != record['bytes'] or sha(path) != record['sha256']:
                raise ValueError('Original preserved bytes changed before packing')
            target = staging / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        pack(staging)
        if read(staging / 'compact_manifest.json') != contents:
            raise ValueError('Archive must contain exactly preserved original bytes')
        archive = inputs / archive_name; archive.mkdir(parents=True)
        for name in sorted(CONTAINERS):
            shutil.copyfile(staging / name, archive / name)
        labels[label_name]['archive_files'] = manifest(archive)
    for name, label in labels.items():
        dump(inputs / (name + '.json'), label)
    im = dict(files=manifest(inputs)); dump(inputs / 'manifest.json', im)
    records = {name:dict(campaign=value['campaign'], run_id=value['run_id'], claim=value['claim'],
        terminal=value['terminal'] if name in ARCHIVES else value['envelope']['receipt'],
        provider_stopped=True, owned_containers=0, app_id=ids[name], label_sha256=digest(value))
        for name, value in labels.items()}
    basis = dict(plan=plan, original_plan=original, student_completion_owner=owner,
        student_slot_transfer=transfer_record(plan, original, owner), config=CONFIG,
        code_review={k:review[k] for k in ('scope','decision','target_commit','report_sha256','source_files')},
        labels=records, config_sha256={n:digest(v['config']) for n,v in labels.items()},
        input_manifest=im, pool_lineages=student_spec['pool_lineages'],
        draw_oracle_sha256=student_spec['draw_local_oracle_sha256'],replacement_spec=read(REPL_SPEC))
    basis.update(operational_basis(labels))
    validate_cap_inputs(basis)
    total = state_bytes = compact_bytes = 0
    for name, label in labels.items():
        validate_label(basis, name, label)
        files = label['archive_files'] if name in ARCHIVES else label['envelope']['artifact_manifest']
        copied = {n:v for n,v in files.items() if n in CONTAINERS or n.endswith('/state.pt')}
        total += sum(v['bytes'] for v in copied.values())
        state_bytes += sum(v['bytes'] for n,v in copied.items() if n.endswith('/state.pt'))
        compact_bytes += copied['compact_evidence.tar.gz']['bytes']
    dump(OUT / 'BASIS.json', basis)
    dump(OUT / 'provider.json', provider)
    dump(OUT / 'BYTE_ACCOUNTING.json', dict(utc=utc(), source_files=source,
        labels_sha256=digest(records), actual_transfer_bytes=total, actual_state_bytes=state_bytes,
        actual_compact_bytes=compact_bytes, logical_runs=21, physical_sources=24,
        status='frozen_inputs_only_no_io_numeric_acceptance_no_upload_no_call'))
    print(json.dumps(dict(frozen=True, logical_runs=21, physical_sources=24, uploaded=False, dispatched=False)))


def publish_proposal():
    """An explicitly prepared actual-byte estimate is data, not external PASS."""
    if PROPOSAL.exists() or PUBLIC.exists():
        raise ValueError('Immutable proposal already exists')
    review, source = code_review()
    basis = read(OUT / 'BASIS.json'); accounting = read(OUT / 'BYTE_ACCOUNTING.json')
    io = read(OUT / 'FINAL_IO_PROPOSAL.json')
    if any(io.get(k) != accounting[k] for k in ('source_files','labels_sha256','actual_transfer_bytes','actual_state_bytes','actual_compact_bytes')):
        raise ValueError('Proposal must bind every actual byte and source')
    if (io.get('complete_dispatch_window_seconds') != 4000 or io.get('passed') is not True
            or not 0 < io['forecast_seconds'] <= 3180 or not io.get('timing_evidence')):
        raise ValueError('Local finite I/O criterion and its real evidence are required')
    for item in io['timing_evidence']:
        path = (ROOT / item['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha(path) != item['sha256']:
            raise ValueError('Missing actual timing source; scenarios are not measurements')
    verify(OUT / CONFIG['input_directory'], basis['input_manifest']['files'])
    PROPOSAL.mkdir()
    dump(PROPOSAL / 'BASIS.json', basis); dump(PROPOSAL / 'IO_PROPOSAL.json', io)
    dump(PROPOSAL / 'BYTE_ACCOUNTING.json', accounting); dump(PROPOSAL / 'SOURCE_BUNDLE.json', source)
    shutil.copyfile(__file__, PROPOSAL / 'PREPARATION_SOURCE.py')
    (PROPOSAL / 'REVIEW_REQUEST.md').write_text(
        '# Exact final CPU numerical review\n\n'
        'All21 logical outcomes/24 physical sources are now frozen. Review actual source/byte counts and the I/O forecast, including its uncertainty and3300-second cap. The original D2 parent and two zero-update students remain failed; replacements retain distinct physical identities. The eight T8 records additionally bind the original failed timing criterion, exact operational9600 amendment, original claim, and five-cent supplements. This is a local criterion, not a fabricated external PASS or CPU dispatch.\n')
    dump(PROPOSAL / 'MANIFEST.json', manifest(PROPOSAL))
    print('Prepared actual-byte numerical proposal only; publish fixed commit and await real scoped review')


def admit():
    if PUBLIC.exists() or (OUT / 'binding.json').exists():
        raise ValueError('Existing immutable CPU admission')
    review, source = code_review()
    basis = read(OUT / 'BASIS.json'); io = read(PROPOSAL / 'IO_PROPOSAL.json')
    numeric = read(R / 'CPU_T8_CAP_NUMERIC_ACCEPTED.json')
    if (numeric['scope'] != 'p008_cpu_replacement_integrity_numeric'
            or numeric['decision'] not in ('PASS','PASS-WITH-NOTES')
            or sha(R / numeric['local_report_path']) != numeric['report_sha256']
            or numeric['io_gate_sha256'] != digest(io)):
        raise ValueError('Actual fixed-scope numerical review required')
    proposal_target = json.loads(subprocess.check_output(['git','show',numeric['target_commit'] + ':' + str(PROPOSAL.relative_to(ROOT) / 'IO_PROPOSAL.json')],cwd=ROOT))
    if proposal_target != io or basis['code_review']['source_files'] != source:
        raise ValueError('Review target or exact CPU source changed')
    binding = dict(basis, io_gate=io, numeric_review={k:numeric[k] for k in ('scope','decision','target_commit','report_sha256','io_gate_sha256','t8_cap_spec_sha256','t8_cap_ledger_sha256','original_N2_passed','post_hoc_engineering_deviation')})
    spec = dict(status='admitted_after_all_local_oracles_and_resource_release',
        binding_sha256=digest(binding), source_files=source,
        original_plan_sha256=digest(binding['original_plan']), student_plan_sha256=digest(binding['plan']))
    release = dict(source_files=source, spec_sha256=digest(spec))
    roster = validate(binding, spec, release)
    labels = {n:read(OUT / CONFIG['input_directory'] / (n+'.json')) for n in roster}
    validate_all_labels(binding, labels)
    remote_preflight(binding['plan'],binding['student_completion_owner'],binding['original_plan'],
                     labels,{n:x['app_id'] for n,x in binding['labels'].items()},True)
    dump(OUT / 'binding.json', binding); PUBLIC.mkdir()
    dump(PUBLIC / 'ADMISSION.json',spec); dump(PUBLIC / 'BINDING.json',binding)
    dump(PUBLIC / 'SOURCE_BUNDLE.json',source); dump(PUBLIC / 'MANIFEST.json',manifest(PUBLIC))
    print('Exact CPU admission prepared; publish before the separate one-time upload')


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('freeze','publish-proposal','admit'))
    actions={'freeze':freeze,'publish-proposal':publish_proposal,'admit':admit}
    actions[parser.parse_args().action]()
