"""Final CPU checks for the separately authorized operational T8 amendment.

These checks bind the original scientific config and claim, the exact archived
intent, both actual reviews, and the immutable 40-cent/5-cent reservations.
They neither rerun inference nor turn the original failed timing gate into PASS.
"""
import hashlib
import json
import math
import re
from pathlib import Path

from experiments.sft_allocation_midpoint.common import digest, read
from .audit_frozen_bundle import verify_packed_run as verify_original_packed_run

CAP_SPEC = '4ca2c55deb53307ddc96b8f6b631127958dd40ddbdc6d536986e38e7798a0044'
OLD_PROPOSAL = '0fb18e7408e8c6cfef69fc05c3f53dab1ce380591926df91dae4000e0bdde75e'
CAMPAIGN = 'p008-students-completion-20261013-r1'
KEY = 'midpoint/' + CAMPAIGN + '/t8_cap_9600_amendment'


def is_t8(label):
    return label['config'].get('training_multiple') == 8


def amendment_record(spec):
    if digest(spec) != CAP_SPEC:
        raise ValueError('Exact owner-approved operational amendment required')
    return dict(schema='p008_immutable_t8_cap_supplement_v1', spec_sha256=CAP_SPEC,
        owner_sha256=digest(spec['owner']), original_plan_sha256=spec['plan_sha256'],
        original_failed_proposal_digest=OLD_PROPOSAL, runs=spec['runs'],
        old_reserved_cents_per_slot=1253, additional_cents_per_slot=5,
        total_additional_cents=40, effective_reserved_cents_per_slot=1258,
        original_run_claims_required=True, effective_worker_seconds=9600,
        original_N2_passed=False, post_hoc_engineering_deviation=True)


def validate_cap_inputs(binding):
    spec = binding['t8_cap_spec']
    record = amendment_record(spec)
    sources = binding['t8_runtime_source_files']
    if (len(sources) != 35 or any(not re.fullmatch('[0-9a-f]{64}', v) for v in sources.values())
            or 'experiments/sft_allocation_p008/modal_students_t8_cap.py' not in sources):
        raise ValueError('Exact T8 runtime source roster required')
    records = binding['t8_cap_ledger_records']
    expected = {KEY} | {KEY + '/reserved/' + n for n in spec['runs']}
    if set(records) != expected or records[KEY] != record:
        raise ValueError('All eight supplements and original global amendment required')
    for name in spec['runs']:
        claim = binding['labels'][name]['claim']
        wanted = dict(run_id=name, original_claim_sha256=digest(claim),
            amendment_sha256=digest(record), supplement_reserved_cents=5,
            reservation_not_provider_expense=True)
        if records[KEY + '/reserved/' + name] != wanted:
            raise ValueError('Supplement does not bind its original scientific claim')
    return record


def validate_cap_numeric(binding):
    validate_cap_inputs(binding)
    numeric = binding['numeric_review']
    if (numeric.get('t8_cap_spec_sha256') != CAP_SPEC
            or numeric.get('t8_cap_ledger_sha256') != digest(binding['t8_cap_ledger_records'])
            or numeric.get('original_N2_passed') is not False
            or numeric.get('post_hoc_engineering_deviation') is not True):
        raise ValueError('CPU numerical review must cover actual amended T8 provenance')


def validate_cap_label(binding, name, label):
    if not is_t8(label):
        if 't8_operational_evidence' in label:
            raise ValueError('A T1, base or pool cannot be relabeled as amended T8')
        return label
    spec = binding['t8_cap_spec']
    record = amendment_record(spec)
    cfg = label['config']
    if (name not in spec['runs'] or cfg != spec['configs'][name]
            or label['campaign'] != CAMPAIGN or label['run_id'] != name
            or cfg['max_seconds'] != 9560 or cfg['updates'] != 2048
            or cfg['targets'] != 4194296):
        raise ValueError('Original T8 scientific identity must remain unchanged')
    proof = label['t8_operational_evidence']
    raw = proof['intent_json']
    sent = json.loads(raw)
    encoded = raw.encode('utf-8')
    if label['envelope']['artifact_manifest']['intent.json'] != dict(
            bytes=len(encoded), sha256=hashlib.sha256(encoded).hexdigest()):
        raise ValueError('Operational evidence must contain the exact archived intent bytes')
    release = sent['release']
    if (sent['config'] != cfg or digest(sent['plan']) != spec['plan_sha256']
            or release['spec_sha256'] != CAP_SPEC
            or release['source_files'] != binding['t8_runtime_source_files']):
        raise ValueError('Archived intent belongs to another cap, source or recipe')
    gates = release['gates']
    for key, scope in (('runtime_review', 't8-cap-9600-runtime'),
                       ('t8_numeric_review', 't8-cap-9600-numeric')):
        review = gates[key]
        if (review['scope'] != scope or review['verdict'] not in ('PASS', 'PASS-WITH-NOTES')
                or review['source_files'] != release['source_files']
                or review['spec_sha256'] != CAP_SPEC
                or not re.fullmatch('[0-9a-f]{40}', review['review_commit'])
                or not re.fullmatch('[0-9a-f]{64}', review['review_report_sha256'])):
            raise ValueError('Both real exact-scope T8 reviews required')
    numeric = gates['t8_numeric_review']
    if (numeric.get('original_N2_passed') is not False
            or numeric.get('post_hoc_engineering_deviation') is not True
            or numeric.get('passed') is not True or numeric.get('N2_closed') is not True
            or numeric.get('accepted_runs') != spec['runs']
            or numeric.get('worker_caps') != {n:9600 for n in spec['runs']}
            or numeric.get('proposal_digest') != OLD_PROPOSAL
            or gates['t8_timing_proposal'] != spec['original_failed_timing_proposal']
            or digest(gates['t8_timing_proposal']) != OLD_PROPOSAL):
        raise ValueError('Amended acceptance cannot erase original actual N2 failure')
    supplement = binding['t8_cap_ledger_records'][KEY + '/reserved/' + name]
    if (proof['amendment_record'] != record or proof['supplement_record'] != supplement
            or sent['supplement'] != supplement or sent['reserved_cents'] != 1253
            or sent['total_reserved_cents'] != 1258 or sent['effective_worker_seconds'] != 9600):
        raise ValueError('Archived original and supplemental reservations differ')
    claim = label['claim']
    original_intent = proof['original_ledger_intent']
    terminal = label['envelope']['receipt']
    if (claim['intent_sha256'] != digest(original_intent)
            or claim['plan_sha256'] != spec['plan_sha256']
            or original_intent['config_sha256'] != digest(cfg)
            or original_intent['source_sha256'] != digest(release['source_files'])
            or original_intent['data_sha256'] != cfg['input_sha256']
            or claim['deadline_epoch'] - claim['claimed_epoch'] != 9630
            or terminal['claim_sha256'] != digest(claim)
            or terminal['status'] != 'completed' or terminal['actual_cost_cents'] != 1253):
        raise ValueError('Original unique claim/intent/deadline/reservation differs')
    for field in ('started_epoch',):
        if type(sent[field]) not in (int, float) or not math.isfinite(sent[field]):
            raise ValueError('Finite original worker entry time required')
    result = label['envelope']['result']
    if (result['registered_slot_reserved_usd'] != 12.53
            or result['supplement_reserved_usd'] != .05 or result['reserved_cost_usd'] != 12.58
            or result['provider_invoice_usd'] is not None):
        raise ValueError('Reserved cost must remain distinct from invoice expense')
    oracle = label['local_oracle']
    for key, value in dict(original_N2_passed=False, post_hoc_engineering_deviation=True,
            effective_worker_seconds=9600, total_reserved_cents=1258,
            supplement_reserved_cents=5).items():
        if type(oracle.get(key)) is not type(value) or oracle[key] != value:
            raise ValueError('Independent local oracle does not bind amended operation')
    return label


def require_remote_cap_records(store, binding, check=lambda:None):
    """Read only; every retained immutable supplemental record must still agree."""
    validate_cap_inputs(binding)
    for key, expected in sorted(binding['t8_cap_ledger_records'].items()):
        check()
        if store.get(key) != expected:
            raise ValueError('Original remote operational cap record differs')
    check()


def verify_packed_run(source, destination, label, check=lambda:None):
    proof = verify_original_packed_run(source, destination, label, check)
    if is_t8(label):
        evidence = Path(destination) / 'evidence'
        cap = label['t8_operational_evidence']
        if (evidence / 'intent.json').read_text() != cap['intent_json']:
            raise ValueError('Actually read compact intent differs from admitted cap evidence')
        if digest(read(evidence / 'admission.json')) != CAP_SPEC:
            raise ValueError('Actually read amendment admission differs')
        proof.update(effective_worker_seconds=9600, original_config_seconds=9560,
            original_reserved_cents=1253, supplement_reserved_cents=5,
            total_reserved_cents=1258, original_N2_passed=False,
            post_hoc_engineering_deviation=True, cap_spec_sha256=CAP_SPEC,
            operational_evidence_sha256=digest(cap))
    return proof
