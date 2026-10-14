"""Verify the original final CPU proof bundle locally; never re-run science.

This checks the CPU's exact 24-source proof roster, hashes, original ledger,
admission, full-state identities and release evidence. It does not reload the
earlier state binaries or rescore their raw answers. Actual invocation requires
a scoped code review and a completed, stopped original CPU call.
"""
import argparse
import datetime
import json
import math
import re
from pathlib import Path

from experiments.sft_allocation_midpoint.common import read, dump, sha, digest, verify
from experiments.sft_allocation_p008.audit_cap_binding import (
    validate, validate_all_labels, physical_roster, source_key,
    ARCHIVES, FAILED_STUDENTS, CHILD_RUN)
from experiments.sft_allocation_p008.audit_bundle import CONTAINERS
from experiments.sft_allocation_p008.audit_t8_cap_records import (
    CAP_SPEC, is_t8, require_remote_cap_records)
from experiments.sft_allocation_p008.completion_queue import require_handoff
from experiments.sft_allocation_p008.provider_release import validate_stopped_apps

SCRIPT = 'scripts/audit_p008_final_cpu.py'
ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(actual, expected, message):
    # Canonical comparison distinguishes booleans from numeric 0/1, and rejects NaN.
    require(digest(actual) == digest(expected), message)


def nonnegative(value, message):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0, message)


def check_copy_timing(records, files):
    require(set(records) == set(files), 'Missing or extra file-transfer timing')
    for name, record in records.items():
        same(record['bytes'], files[name]['bytes'], 'Wrong measured transfer byte count')
        nonnegative(record['seconds'], 'Invalid measured copy/hash duration')


def check_proof(name, label, proof):
    """Pure comparison of one CPU proof against its exact frozen source label."""
    digest(proof)  # reject nonfinite JSON anywhere, including optional timing fields
    same(proof['passed'], True, 'CPU source proof did not pass')
    same(proof['new_model_calls'], 0, 'CPU proof reports a model call')
    same([proof['campaign'], proof['run_id']], [label['campaign'], label['run_id']],
         'Proof belongs to another physical source')
    if name in ARCHIVES:
        same(proof['original_status'], 'failed', 'Original failed parent was relabeled')
        same(proof['original_artifact_digest'], label['terminal']['evidence_sha256'],
             'Failure manifest digest changed')
        same(proof['files_verified'], len(label['preserved_manifest']),
             'Failure archive file roster changed')
        same(proof['raw_rescoring'], False, 'Integrity audit must not claim raw rescoring')
        check_copy_timing(proof['timings'], label['archive_files'])
        if name in FAILED_STUDENTS:
            same([proof['attempted_updates'], proof['endpoint_outputs']], [0, 0],
                 'Original zero-update failure gained scientific work')
        return

    cfg, envelope = label['config'], label['envelope']
    files, oracle = envelope['artifact_manifest'], label['local_oracle']
    same(proof['role'], cfg['role'], 'Physical source role changed')
    same(proof['files_verified'], len(files), 'Original artifact roster changed')
    same(proof['original_artifact_digest'], digest(files), 'Original manifest changed')
    same(proof['local_oracle_sha256'], digest(oracle), 'Bound independent oracle changed')
    if name == CHILD_RUN:
        same(proof['raw_rescoring'], False, 'Merged raw oracle must remain previously bound')
        check_copy_timing(proof['timings'], {n: files[n] for n in CONTAINERS})
        return

    steps = ([1024, 2048] if cfg['updates'] == 2048 else [cfg['updates']]) if cfg['role'] in ('main', 'bridge') else []
    states = {f'checkpoint_{step:04d}/state.pt' for step in steps}
    expected_hashes = {}
    for step in steps:
        value = files[f'checkpoint_{step:04d}/state.pt']['sha256']
        original = (oracle['state_sha256'] if step == cfg['updates']
                    else oracle['forensic_checkpoints'][str(step)]['sha256'])
        same(value, original, 'Frozen state and independent original oracle differ')
        expected_hashes[str(step)] = value
    same(proof['checkpoint_sha256'], expected_hashes, 'Missing, extra or substituted full state')
    copied = {n: files[n] for n in CONTAINERS | states}
    same(proof['copied_bytes'], sum(v['bytes'] for v in copied.values()), 'Copied byte total differs')
    timings = proof['timings']
    check_copy_timing(timings['copy_and_sha'], copied)
    same(set_to_list(timings['complete_state_validation_seconds']), sorted(expected_hashes),
         'Missing full-state validation timing')
    for value in timings['complete_state_validation_seconds'].values():
        nonnegative(value, 'Invalid full-state validation duration')
    for key in ('unpack_and_all_file_sha_seconds', 'total_seconds'):
        nonnegative(timings[key], 'Invalid CPU source timing')
    require('not repeated' in proof['raw_rescoring_scope'], 'Raw-oracle scope is overstated')
    if is_t8(label):
        wanted = dict(effective_worker_seconds=9600, original_config_seconds=9560,
                      original_reserved_cents=1253, supplement_reserved_cents=5,
                      total_reserved_cents=1258, original_N2_passed=False,
                      post_hoc_engineering_deviation=True, cap_spec_sha256=CAP_SPEC,
                      operational_evidence_sha256=digest(label['t8_operational_evidence']))
        same({k: proof[k] for k in wanted}, wanted, 'T8 operational amendment/history changed')


def set_to_list(value):
    return sorted(value)


def check_provider(provider, app_id, run_log):
    require(set(re.findall(r'\bap-[A-Za-z0-9]+\b', run_log)) == {app_id},
            'Provider identity does not match the original CPU invocation log')
    validate_stopped_apps([app_id], provider['apps'], provider['owned_containers'])
    require(not any(c['app_id'] == app_id for c in provider.get('other_containers', [])),
            'Original CPU still has a container')


def check_journal(root, binding, labels, result, ledger):
    roster = set(labels)
    same(sorted(result['labels']), sorted(roster), 'Missing or extra CPU proof')
    prefix = 'midpoint/' + binding['plan']['campaign_id'] + '/audit/'
    for directory in ('intents', 'proofs', 'completed'):
        names = {p.stem for p in (root / directory).glob('*.json')}
        require(names == roster, 'CPU on-disk journal roster is incomplete')
    for kind in ('unit', 'done'):
        actual = {k[len(prefix + kind + '/'):]: v for k, v in ledger.items()
                  if k.startswith(prefix + kind + '/')}
        require(set(actual) == roster, 'CPU remote journal roster is incomplete')
    for name in sorted(roster):
        label = labels[name]
        item = binding['labels'][name]
        unit = dict(label_sha256=digest(label), campaign=item['campaign'],
                    source_run_id=item['run_id'], original_terminal=item['terminal'])
        same(read(root / 'intents' / (name + '.json')), unit, 'CPU source intent changed')
        same(ledger[prefix + 'unit/' + name], unit, 'CPU immutable unit differs')
        proof_path = root / 'proofs' / (name + '.json')
        proof = read(proof_path)
        same(result['labels'][name], proof, 'CPU aggregate proof differs from saved proof')
        done = dict(proof_sha256=sha(proof_path), label_sha256=digest(label))
        same(read(root / 'completed' / (name + '.json')), done, 'CPU proof byte hash differs')
        same(ledger[prefix + 'done/' + name], done, 'CPU immutable completion differs')
        check_proof(name, label, proof)


def audit(args):
    root, inputs = Path(args.export_dir), Path(args.inputs)
    acceptance = read(args.code_acceptance)
    require(acceptance['scope'] == 'p008-final-cpu-local-finalizer-code'
            and acceptance['decision'] in ('PASS', 'PASS-WITH-NOTES')
            and re.fullmatch('[0-9a-f]{40}', acceptance['target_commit']),
            'Actual scoped finalizer code review required')
    same(acceptance['source_files'], {SCRIPT: sha(ROOT / SCRIPT)}, 'Finalizer review source differs')
    same(acceptance['report_sha256'], sha(args.review_report), 'Original review report bytes differ')

    binding, spec = read(args.binding), read(args.admission)
    envelope, ledger = read(args.receipt), read(args.ledger)
    sent, dispatch = read(root / 'intent.json'), read(args.dispatch)
    release = sent['release']
    same(sent['binding'], binding, 'CPU intent binding changed')
    same(dispatch['binding'], binding, 'Original submitted binding changed')
    same(dispatch['release'], release, 'Original submitted source changed')
    require(re.fullmatch('[0-9a-f]{40}', release['commit']), 'Exact published execution commit required')
    require(re.fullmatch('fc-[A-Za-z0-9]+', read(args.submitted)['call_id']),
            'Original provider call identity required')
    roster = validate(binding, spec, release)
    require(len(roster) == 24 and roster == physical_roster(), 'Exact 24 physical sources required')
    require(len(release['source_files']) == 19
            and 'experiments/sft_allocation_p008/modal_audit_t8_cap.py' in release['source_files'],
            'Wrong CPU runtime source roster')
    for path, value in release['source_files'].items():
        same(sha(ROOT / path), value, 'Frozen CPU source bytes changed')
    same(read(root / 'admission.json'), spec, 'CPU admission differs from archived bytes')
    same(read(inputs / 'manifest.json'), binding['input_manifest'], 'Frozen input manifest changed')
    verify(inputs, binding['input_manifest']['files'])
    labels = {n: read(inputs / (n + '.json')) for n in sorted(roster)}
    validate_all_labels(binding, labels)

    plan = binding['plan']
    prefix = 'midpoint/' + plan['campaign_id'] + '/'
    same(ledger[prefix + 'campaign'], plan, 'Original registered plan changed')
    require_handoff(ledger, plan, binding['original_plan'], binding['student_completion_owner'], 'audit')
    require_remote_cap_records(ledger, binding)
    for item in binding['labels'].values():
        for kind in ('claim', 'terminal'):
            same(ledger[source_key(item, kind)], item[kind], 'Original physical ledger changed')
    claim, intent, terminal = (ledger[prefix + k + '/audit'] for k in ('claim', 'intent', 'terminal'))
    wanted_intent = dict(run_id='audit', config_sha256=digest(binding),
                         source_sha256=digest(release['source_files']),
                         data_sha256=digest(binding['input_manifest']))
    same(intent, wanted_intent, 'Original CPU ledger intent differs')
    same(claim['intent_sha256'], digest(intent), 'CPU claim does not bind its intent')
    same(claim['plan_sha256'], digest(plan), 'CPU claim belongs to another plan')
    same(claim['run_id'], 'audit', 'CPU run identity differs')
    same(claim['reserved_cents'], 500, 'CPU reservation changed')
    attempts = {k: v for k, v in ledger.items() if k.startswith(prefix + 'attempt/audit/')}
    same(attempts, {prefix + 'attempt/audit/' + claim['attempt_id']: claim},
         'Missing or extra original CPU attempts')
    same(terminal, envelope['receipt'], 'CPU receipt differs from original ledger')
    same(terminal['status'], 'completed', 'Completed CPU required; preserve failures separately')
    same(terminal['claim_sha256'], digest(claim), 'CPU terminal belongs to another attempt')
    same(terminal['actual_cost_cents'], 500, 'CPU reserved-cost field changed')
    for key in ('started_epoch', 'hard_stop_epoch'):
        nonnegative(sent[key], 'Invalid original CPU clock')
    for key in ('claimed_epoch', 'deadline_epoch'):
        nonnegative(claim[key], 'Invalid CPU claim clock')
    nonnegative(terminal['finished_epoch'], 'Invalid CPU terminal clock')
    same(claim['deadline_epoch'] - claim['claimed_epoch'], 3300.0, 'CPU claim duration changed')
    same(sent['hard_stop_epoch'], min(sent['started_epoch'] + 3300, plan['deadline_epoch'] - 30),
         'CPU entry timer changed')
    require(sent['started_epoch'] <= claim['claimed_epoch'] <= terminal['finished_epoch']
            <= min(sent['hard_stop_epoch'], claim['deadline_epoch']), 'CPU completion exceeded original cap')

    files = read(root / 'artifact_manifest.json')
    same(files, envelope['artifact_manifest'], 'CPU artifact manifest changed')
    same(digest(files), terminal['evidence_sha256'], 'CPU terminal manifest digest differs')
    expected = {'intent.json', 'admission.json', 'result.json'} | set(CONTAINERS)
    expected |= {folder + '/' + n + '.json' for folder in ('intents', 'proofs', 'completed') for n in roster}
    require(set(files) == expected, 'Unexpected or missing CPU proof artifacts')
    verify(root, files)
    result = read(root / 'result.json')
    same(result, envelope['result'], 'CPU result differs from original envelope')
    wanted = dict(passed=True, t8_operational_amendment_verified=True, original_N2_passed=False,
                  post_hoc_engineering_deviation=True, logical_runs=21, physical_sources=24,
                  original_d2_status='failed', child_status='completed', reserved_cost_usd=5,
                  provider_invoice_usd=None, new_model_calls=0)
    same({k: result[k] for k in wanted}, wanted, 'CPU aggregate scope/lineage changed')
    nonnegative(result['wall_seconds'], 'Invalid CPU result duration')
    require(result['wall_seconds'] <= terminal['finished_epoch'] - sent['started_epoch'],
            'CPU reported duration exceeds actual terminal')
    check_journal(root, binding, labels, result, ledger)
    provider = read(args.provider)
    check_provider(provider, args.app_id, Path(args.run_log).read_text())
    return dict(schema='p008_final_cpu_local_verification_v1', passed=True,
                utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                logical_runs=21, physical_sources=24, completed_physical_sources=21,
                original_failed_sources=3, original_failures_preserved=True,
                state_binaries_bound=26, original_N2_passed=False, post_hoc_engineering_deviation=True,
                new_model_calls=0, new_raw_rescoring=False, state_binaries_reloaded_locally=False,
                source_state_validation='Original CPU proofs bind all26 independently loaded full states and prior local oracles',
                cpu_source_sha256=digest(release['source_files']), binding_sha256=digest(binding),
                admission_sha256=digest(spec), artifact_digest=digest(files),
                finalizer_source_sha256=sha(ROOT / SCRIPT), finalizer_review_sha256=sha(args.review_report),
                provider_app_id=args.app_id, provider_evidence_sha256=sha(args.provider),
                ledger_file_sha256=sha(args.ledger), original_receipt_sha256=sha(args.receipt),
                reserved_cost_usd=5, provider_invoice_usd=None, external_result_review='pending')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('export-dir', 'inputs', 'binding', 'admission', 'receipt', 'ledger',
                 'provider', 'app-id', 'run-log', 'dispatch', 'submitted', 'code-acceptance', 'review-report', 'out'):
        parser.add_argument('--' + name, required=True)
    arguments = parser.parse_args()
    if Path(arguments.out).exists():
        raise ValueError('Existing verification output; do not repeat completed work')
    proof = audit(arguments)
    dump(arguments.out, proof)
    print(json.dumps(proof))

