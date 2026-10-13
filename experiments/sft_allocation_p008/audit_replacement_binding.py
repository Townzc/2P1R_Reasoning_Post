"""Exact final CPU inputs: 21 logical runs, 24 real sources including two zero-update failures.

Pure admission checks. A code review cannot manufacture completed evidence or
authorize a cloud run. The actual immutable admission does not yet exist.
"""
import hashlib
import json
import math
import re
from experiments.sft_allocation_midpoint.common import digest
from .contract import run_roster
from .completion_queue import CAMPAIGN as STUDENT_CAMPAIGN, validate_plan as validate_completion_plan, transfer_record
from .pool_lineage import PARENT_CAMPAIGN, CHILD_CAMPAIGN, CHILD_RUN, validate_pool_lineages
from .audit_binding import validate_label as validate_original_label
from .audit_bundle import CONTAINERS
from .audit_frozen_plan import REPLACEMENTS, ORIGINAL_SPEC

CONFIG = dict(run_id='audit', role='audit', max_seconds=3300, readers=2,
              input_directory='audit_inputs_replacements')
PARENT_LABEL = 'pool_d2_parent'
PARENT_ARCHIVE = 'parent_archive'
REPLACEMENT_CAMPAIGN = 'p008-student-lr-replacement-20261013-r1'
REPLACEMENT_SPEC = '3e1c792425b311af81f0c4305939758f187c1c4506082e04acd73a7d95c36b3e'
FAILED_STUDENTS = frozenset(REPLACEMENTS.values())
ARCHIVES = {PARENT_LABEL: PARENT_ARCHIVE, **{n: 'failed_students/' + n for n in FAILED_STUDENTS}}
ORIGINAL_PLAN_SHA256 = 'abd0935222aac96713b9ec4ac18c406d5a7caee39e477f1bd5b07b936c19844e'


def _hash(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def evidence_file_hash(raw_json, value):
    """The earlier G1 uses file-byte SHA, not canonical JSON object digest."""
    if not isinstance(raw_json, str) or json.loads(raw_json) != value:
        raise ValueError('Exact original JSON bytes and parsed record must agree')
    return hashlib.sha256(raw_json.encode('utf-8')).hexdigest()


def physical_roster():
    return {x['run_id'] for x in run_roster(8, False, 2)} | {
        'base', 'pool_d1', PARENT_LABEL, CHILD_RUN} | set(REPLACEMENTS)


def source_key(item, kind):
    if kind not in ('terminal', 'claim'):
        raise ValueError('Only original source evidence keys')
    return f"midpoint/{item['campaign']}/{kind}/{item['run_id']}"


def validate(binding, spec, release):
    plan, cfg = binding['plan'], binding['config']
    original, owner = binding['original_plan'], binding['student_completion_owner']
    validate_completion_plan(plan, original, owner)
    if (cfg != CONFIG or plan['campaign_id'] != STUDENT_CAMPAIGN
            or plan['slots']['audit']['reserved_cents'] != 500
            or spec['original_plan_sha256'] != digest(original)
            or digest(original) != ORIGINAL_PLAN_SHA256
            or spec['student_plan_sha256'] != digest(plan)
            or binding['student_slot_transfer'] != transfer_record(plan, original, owner)):
        raise ValueError('Exact authorized finite successor and original500-cent CPU slot required')
    if (spec['status'] != 'admitted_after_all_local_oracles_and_resource_release'
            or spec['binding_sha256'] != digest(binding)
            or spec['source_files'] != release['source_files']
            or digest(spec) != release['spec_sha256']):
        raise ValueError('Exact published lineage CPU admission required')
    review = binding['code_review']
    if (review['scope'] != 'p008_cpu_replacement_integrity_code'
            or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or review['source_files'] != release['source_files']
            or not re.fullmatch('[0-9a-f]{40}', review['target_commit'])
            or not _hash(review['report_sha256'])):
        raise ValueError('Real new-source code review required')
    roster = physical_roster()
    if set(binding['labels']) != roster or set(binding['config_sha256']) != roster:
        raise ValueError('All 24 physical sources required; no silently dropped parent')
    expected_files = {x + '.json' for x in roster} | {
        archive + '/' + x for archive in ARCHIVES.values() for x in CONTAINERS}
    if set(binding['input_manifest']['files']) != expected_files:
        raise ValueError('Exact labels plus three-file failed-parent archive required')
    for record in binding['input_manifest']['files'].values():
        if type(record['bytes']) is not int or record['bytes'] <= 0 or not _hash(record['sha256']):
            raise ValueError('Invalid admitted input hash/size')
    replacement = replacement_spec(binding)
    lineage_records = validate_pool_lineages(binding['pool_lineages'], binding['draw_oracle_sha256'])
    for name, item in binding['labels'].items():
        campaign = (REPLACEMENT_CAMPAIGN if name in REPLACEMENTS else CHILD_CAMPAIGN if name == CHILD_RUN else PARENT_CAMPAIGN
                    if name in ('pool_d1', PARENT_LABEL) else STUDENT_CAMPAIGN)
        run = 'pool_d2' if name == PARENT_LABEL else name
        status = 'failed' if name in ARCHIVES else 'completed'
        if (item['campaign'] != campaign or item['run_id'] != run
                or item['terminal']['status'] != status
                or item['terminal']['claim_sha256'] != digest(item['claim'])
                or not _hash(item['terminal']['evidence_sha256'])
                or item['provider_stopped'] is not True or item['owned_containers'] != 0
                or not item['app_id'] or not _hash(item['label_sha256'])):
            raise ValueError('Actual stopped source, claim and terminal required')
        if campaign in (PARENT_CAMPAIGN, STUDENT_CAMPAIGN):
            expected_plan = original if campaign == PARENT_CAMPAIGN else plan
            if item['claim'].get('plan_sha256') != digest(expected_plan):
                raise ValueError('Original or successor claim belongs to another plan')
        if name in FAILED_STUDENTS:
            parent = replacement['parents'][name]
            if any(item[k] != parent[k] for k in ('campaign','run_id','claim','terminal')) or item['app_id'] != parent['provider_app_id']:
                raise ValueError('Original zero-update failed source changed')
        if name in REPLACEMENTS and item['claim'].get('plan_sha256') != replacement['plan_sha256']:
            raise ValueError('Replacement source does not bind its independent plan')
        if name in ('pool_d1', PARENT_LABEL, CHILD_RUN):
            if dict(campaign=campaign, run_id=run, terminal=item['terminal']) not in lineage_records:
                raise ValueError('Audit source is not the reviewed pool lineage')
    if len({item['app_id'] for item in binding['labels'].values()}) != 24:
        raise ValueError('Each physical source must retain its distinct provider identity')
    io = binding['io_gate']
    numeric = binding['numeric_review']
    if (io['passed'] is not True or io['source_files'] != release['source_files']
            or io['labels_sha256'] != digest(binding['labels'])
            or not math.isfinite(io['forecast_seconds']) or not 0 < io['forecast_seconds'] <= 3180
            or io['complete_dispatch_window_seconds'] != 4000
            or numeric['scope'] != 'p008_cpu_replacement_integrity_numeric'
            or numeric['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or numeric['io_gate_sha256'] != digest(io)
            or not re.fullmatch('[0-9a-f]{40}', numeric['target_commit'])
            or not _hash(numeric['report_sha256'])):
        raise ValueError('Actual bytes, finite I/O proposal and scoped numeric review required')
    return roster


def validate_label(binding, name, label):
    item = binding['labels'][name]
    if (digest(label) != item['label_sha256']
            or label['campaign'] != item['campaign'] or label['run_id'] != item['run_id']
            or digest(label['config']) != binding['config_sha256'][name]
            or label['claim'] != item['claim']):
        raise ValueError('Exact original input/config/claim binding differs')
    lineage = binding['pool_lineages']
    replacement = replacement_spec(binding)
    if name in FAILED_STUDENTS:
        parent = replacement['parents'][name]
        rec = replacement['zero_update_reconciliation']
        row = rec['runs'][name]
        if (label['terminal'] != item['terminal'] or label['reconciliation'] != rec
                or label['replacement_spec'] != replacement
                or evidence_file_hash(label['reconciliation_json'],rec) != replacement['zero_update_reconciliation_sha256']
                or digest(label['preserved_manifest']) != row['local_manifest_sha256']
                or label['config'] != replacement['original_spec']['configs'][name]
                or label['claim'] != parent['claim'] or label['terminal'] != parent['terminal']):
            raise ValueError('Exact original zero-update reconciliation and bytes required')
        # The original reconciliation stored this manifest's canonical digest;
        # its reconciliation_json field above is a file-byte hash instead.
        evidence_file_hash(label['preserved_manifest_json'],label['preserved_manifest'])
        _archive_binding(binding, name, label)
        return label
    if name == PARENT_LABEL:
        rec = label['reconciliation']
        if (label['terminal'] != item['terminal'] or label['config']['role'] != 'pool'
                or label['config']['run_id'] != 'pool_d2'
                or evidence_file_hash(label['reconciliation_json'], rec) != lineage['2']['parent_reconciliation_sha256']
                or rec['parent_terminal'] != item['terminal'] or rec['parent_claim'] != item['claim']
                or rec['passed'] is not True or rec['physical_raw_unknown'] != 0):
            raise ValueError('Real failed-parent reconciliation required')
        if set(label['archive_files']) != CONTAINERS:
            raise ValueError('Failed-parent archive roster differs')
        for file, record in label['archive_files'].items():
            if record != binding['input_manifest']['files'][PARENT_ARCHIVE + '/' + file]:
                raise ValueError('Parent archive not bound to readback inputs')
    elif name == CHILD_RUN:
        if (label['envelope']['receipt'] != item['terminal']
                or digest(label['envelope']['artifact_manifest']) != item['terminal']['evidence_sha256']
                or evidence_file_hash(label['local_oracle_json'], label['local_oracle']) != binding['draw_oracle_sha256']['2']
                or label['local_oracle'] != lineage['2']['merged_proof']
                or label['config']['run_id'] != CHILD_RUN or label['config']['role'] != 'pool_continuation'):
            raise ValueError('Completed child must bind the actual merged oracle')
    else:
        validate_original_label(binding, name, label)
        if name == 'pool_d1' and evidence_file_hash(label['local_oracle_json'], label['local_oracle']) != binding['draw_oracle_sha256']['1']:
            raise ValueError('D1 independent oracle changed')
    if name not in ('pool_d1', PARENT_LABEL, CHILD_RUN):
        original = replacement['original_spec']
        logical = REPLACEMENTS.get(name,name)
        expected = replacement['configs'][name] if name in REPLACEMENTS else original['configs'][name]
        if label['config'] != expected or label['original_student_spec'] != original:
            raise ValueError('CPU label cannot amend original scientific config')
        evidence_file_hash(label['local_oracle_json'],label['local_oracle'])
        if name in REPLACEMENTS:
            if label['replacement_spec'] != replacement or label['local_oracle'].get('logical_run_id') != logical:
                raise ValueError('Replacement local oracle belongs to another logical cell')
        if name != 'base' and not all(k in label.get('frozen_input_bytes',{}) for k in ('manifest_json','plan_json')):
            raise ValueError('Exact frozen input bytes required for every student')
    return label


def _archive_binding(binding, name, label):
    archive = ARCHIVES[name]
    if set(label['archive_files']) != CONTAINERS:
        raise ValueError('Exact failed-source archive roster required')
    for filename, record in label['archive_files'].items():
        if binding['input_manifest']['files'].get(archive + '/' + filename) != record:
            raise ValueError('Failed-source archive binding differs')


def replacement_spec(binding):
    spec = binding['replacement_spec']
    if (digest(spec) != REPLACEMENT_SPEC or digest(spec['original_spec']) != ORIGINAL_SPEC
            or spec['original_execution_plan'] != binding['plan']
            or spec['mapping'] != REPLACEMENTS
            or spec['owner']['stage_cap_cents'] != 26604
            or spec['zero_update_reconciliation']['passed'] is not True):
        raise ValueError('Exact owner-approved two-replacement admission required')
    return spec


def validate_all_labels(binding, labels):
    if set(labels) != physical_roster():
        raise ValueError('Incomplete physical inputs')
    total = state_bytes = compact_bytes = 0
    for name, label in labels.items():
        validate_label(binding, name, label)
        files = (label['archive_files'] if name in ARCHIVES
                 else label['envelope']['artifact_manifest'])
        copied = {k: v for k, v in files.items() if k in CONTAINERS or k.endswith('/state.pt')}
        total += sum(v['bytes'] for v in copied.values())
        state_bytes += sum(v['bytes'] for k, v in copied.items() if k.endswith('/state.pt'))
        compact_bytes += copied['compact_evidence.tar.gz']['bytes']
    io = binding['io_gate']
    if (io['actual_transfer_bytes'] != total or io['actual_state_bytes'] != state_bytes
            or io['actual_compact_bytes'] != compact_bytes):
        raise ValueError('I/O gate does not count all original source bytes')
    return labels
