"""Explicit post-hoc +40s/+5c amendment; original failed criterion stays failed.

Original scientific config and unique RunGuard claim are reused, not migrated.
The immutable supplemental reservation is accounting metadata, no GPU function.
Both new source/spec review and separate amended numerical acceptance are needed.
"""
import math
from decimal import Decimal, ROUND_CEILING
from experiments.sft_allocation_midpoint.common import digest
from .completion_student_binding import validate_student_binding as validate_original
from .student_t8_binding import ORIGINAL, REPLACEMENTS, FAILED, expected_mapping, require_timing_terminals, pending_across_queues
from .main_binding import accepted

ORIGINAL_SPEC = 'ab49b0a638090f61dfd39e7391c61e4427a47b6ea94acfe6e0de3c4f606b21ee'
ORIGINAL_PROPOSAL = '0fb18e7408e8c6cfef69fc05c3f53dab1ce380591926df91dae4000e0bdde75e'
AMENDMENT_KEY = 'midpoint/' + ORIGINAL + '/t8_cap_9600_amendment'


def validate_owner(owner):
    fields = dict(authority='Direct human reply in this chat', answer='批准 9,600 秒及 $266.44 上限（推荐）',
        old_cap_seconds=9560,new_cap_seconds=9600,additional_reservation_cents=40,
        old_stage_cap_cents=26604,stage_cap_cents=26644,project_ceiling_cents=45000,protected_cents=5000,
        original_eight_T8_only=True,maximum_calls_each=1,automatic_retry=False,maximum_student_H100_workers=8,
        scientific_dose_inputs_and_endpoint_unchanged=True,margin_multiplier=1.2,soft_margin_seconds=30,
        material_freeze_utc='2026-10-14T04:00:00Z',exact_runtime_and_numeric_review_required=True,
        original_N2_failed_retained=True,post_hoc_engineering_deviation=True)
    if any(type(owner.get(k)) is not type(v) or owner[k] != v for k,v in fields.items()):
        raise ValueError('Exact direct bounded cap/budget authority required')


def amendment_record(spec):
    return dict(schema='p008_immutable_t8_cap_supplement_v1',spec_sha256=digest(spec),
        owner_sha256=digest(spec['owner']),original_plan_sha256=spec['plan_sha256'],
        original_failed_proposal_digest=ORIGINAL_PROPOSAL,runs=spec['runs'],
        old_reserved_cents_per_slot=1253,additional_cents_per_slot=5,total_additional_cents=40,
        effective_reserved_cents_per_slot=1258,original_run_claims_required=True,
        effective_worker_seconds=9600,original_N2_passed=False,post_hoc_engineering_deviation=True)


def register_amendment(store,spec):
    value=amendment_record(spec)
    if not store.put(AMENDMENT_KEY,value,skip_if_exists=True) and store.get(AMENDMENT_KEY)!=value:
        raise ValueError('Conflicting immutable cap supplement')
    return value


def supplement_key(run):
    return AMENDMENT_KEY+'/reserved/'+run


def reserve_supplement(store,spec,admitted):
    # Must follow the ORIGINAL scientific claim. A competing old/new worker
    # cannot reach this point after losing that claim. Any partial failure burns
    # the slot; it never authorizes another call or claim deletion.
    if admitted.campaign_id!=ORIGINAL or admitted.run_id not in spec['runs']:
        raise ValueError('Foreign scientific slot')
    value=amendment_record(spec)
    if store.get(AMENDMENT_KEY)!=value:
        raise ValueError('Missing immutable global supplement')
    claim=store.get('midpoint/'+ORIGINAL+'/claim/'+admitted.run_id)
    if claim is None or digest(claim)!=admitted.claim_sha256 or claim['attempt_id']!=admitted.attempt_id:
        raise ValueError('Original scientific claim not owned')
    record=dict(run_id=admitted.run_id,original_claim_sha256=admitted.claim_sha256,
                amendment_sha256=digest(value),supplement_reserved_cents=5,
                reservation_not_provider_expense=True)
    if not store.put(supplement_key(admitted.run_id),record,skip_if_exists=True):
        raise ValueError('Supplement already reserved; no replay')
    return record


def verify_supplement(store,spec,run):
    value=amendment_record(spec);claim=store.get('midpoint/'+ORIGINAL+'/claim/'+run)
    record=store.get(supplement_key(run))
    if store.get(AMENDMENT_KEY)!=value or claim is None or record!=dict(run_id=run,
       original_claim_sha256=digest(claim),amendment_sha256=digest(value),
       supplement_reserved_cents=5,reservation_not_provider_expense=True):
        raise ValueError('Original scientific claim and supplementary reservation differ')
    return record


def validate_student_binding(plan,cfg,release,spec):
    validate_owner(spec['owner'])
    original=spec['original_spec'];run=cfg['run_id']
    large=sorted(n for n,c in original['configs'].items() if c.get('training_multiple')==8)
    if (digest(original)!=ORIGINAL_SPEC or spec['original_spec_sha256']!=ORIGINAL_SPEC
        or spec['runs']!=large or len(large)!=8 or run not in large
        or cfg!=original['configs'][run] or spec['configs']!=original['configs']
        or spec['config_sha256']!=original['config_sha256']
        or digest(plan)!=original['plan_sha256'] or spec['plan_sha256']!=digest(plan)
        or spec['common_plan_gate_sha256']!=original['common_plan_gate_sha256']
        or release['spec_sha256']!=digest(spec)):
        raise ValueError('Original scientific plan/config/roster cannot change')
    # These are actual historical source/G1 releases, not fabricated new PASS.
    validate_original(plan,cfg,spec['original_g1_releases'][str(cfg['draw'])],original)
    fixed=dict(worker_cap_seconds=9600,platform_timeout_seconds=9660,startup_timeout_seconds=600,
        dispatch_window_seconds=10300,soft_margin_seconds=30,margin_multiplier=1.2,
        amended_threshold_seconds=9570,original_criterion_passed=False,
        new_slot_reservation_cents=1258,old_slot_reservation_cents=1253,additional_cents_per_slot=5,
        additional_total_cents=40,stage_cap_cents=26644,project_ceiling_cents=45000,protected_cents=5000,
        registered_plan_unchanged=True,original_claim_key_used=True,
        operational_cap_overrides_only_cfg_max_seconds=True,post_hoc_engineering_deviation=True)
    if any(type(spec.get(k)) is not type(v) or spec[k]!=v for k,v in fixed.items()):
        raise ValueError('Only exact finite operational amendment allowed')
    if any(plan['slots'][n]['reserved_cents']!=1253 for n in large):
        raise ValueError('Old registered reservation changed')
    minimum=math.ceil((9600+700)*4.393584/3600*100)
    if minimum!=1258 or 8*(minimum-1253)!=40 or 26604+40!=spec['stage_cap_cents']:
        raise ValueError('Full startup/closing reservation differs')
    budget=spec['project_budget'];meter=Decimal(budget['workspace_metered_usd'])
    if (not meter.is_finite() or meter<0 or int((meter*100).to_integral_value(rounding=ROUND_CEILING))+26644>45000
        or budget['project_ceiling_usd']!='450' or budget['protected_usd']!='50'
        or budget['all_failures_setup_build_storage_retained'] is not True):
        raise ValueError('Conservative full-meter plus entire-stage budget proof fails')
    gates=release['gates']
    if gates['cap_owner']!=spec['owner']:
        raise ValueError('Owner record mismatch')
    accepted(gates['runtime_review'],'t8-cap-9600-runtime',release['source_files'],digest(spec))
    proposal=gates['t8_timing_proposal']
    if (digest(proposal)!=ORIGINAL_PROPOSAL or proposal!=spec['original_failed_timing_proposal']
        or spec['original_proposal_digest']!=ORIGINAL_PROPOSAL
        or gates['t8_numeric_review'].get('original_N2_passed') is not False
        or gates['t8_numeric_review'].get('post_hoc_engineering_deviation') is not True):
        raise ValueError('Original failed timing proposal must remain exact and disclosed')
    validate_timing_gate(cfg,release,spec)
    # Runtime dependency gates must exactly reuse the historical G1 proof.
    old=spec['original_g1_releases'][str(cfg['draw'])]['gates']
    for key in ('required_terminals','pool_terminals','student_completion_owner','student_slot_transfer','upload'):
        if gates[key]!=old[key]:
            raise ValueError('Original data/dependency authority changed')
    return True


def validate_timing_gate(cfg, release, spec):
    original = spec["original_spec"]
    gates = release['gates']
    proposal = gates['t8_timing_proposal']
    review = gates['t8_numeric_review']
    accepted(review, 't8-cap-9600-numeric', release['source_files'], digest(spec))
    large = sorted(n for n, c in original['configs'].items()
                   if c.get('training_multiple') == 8)
    mapping = expected_mapping(original)
    if (len(large) != 8 or cfg['run_id'] not in large
            or cfg['training_multiple'] != 8 or cfg['role'] != 'main'
            or cfg['updates'] != 2048 or cfg['targets'] != 4194296
            or cfg['max_seconds'] != 9560):
        raise ValueError('Only the original eight unattempted full-dose T8 slots')
    if (review.get('passed') is not True or review.get('N2_closed') is not True
            or review.get('accepted_runs') != large
            or review.get('worker_caps') != {n: 9600 for n in large}
            or review.get('proposal_digest') != digest(proposal)
            or review.get('common_plan_gate_sha256') != spec['common_plan_gate_sha256']):
        raise ValueError('Actual complete numerical N2 acceptance is missing')
    # The estimate itself deliberately never grants permission. Acceptance is
    # a separate reviewed record, not a mutation of the original proposal.
    if (proposal.get('N2_closed') is not False
            or proposal.get('runtime_admission') is not False
            or proposal.get('engineering_criterion_passed') is not False
            or proposal.get('failed_host_dropped') is not False
            or proposal.get('new_model_calls') != 0
            or proposal.get('spec_sha256') != digest(original)
            or proposal.get('common_plan_gate_sha256') != spec['common_plan_gate_sha256']
            or proposal.get('logical_to_physical') != mapping
            or set(proposal.get('provenance', {})) != set(mapping)
            or set(proposal.get('failed_attempts_retained', {})) != set(FAILED)
            or set(proposal.get('components', {})) != set(mapping) - {'base'}
            or set(proposal.get('predictions', {})) != set(large)):
        raise ValueError('Complete original timing and failed-attempt lineage required')
    if proposal.get('policy', {}).get('schema') != 'p008_t1_first_timing_gate_v2':
        raise ValueError('Frozen C1/C2 timing policy required')
    for logical, item in mapping.items():
        p = proposal['provenance'][logical]
        terminal = p.get('terminal', {})
        if (p.get('physical_run_id') != item['run_id']
                or terminal.get('run_id') != item['run_id']
                or terminal.get('status') != 'completed'
                or any(len(p.get(k, '')) != 64 for k in
                       ('oracle_sha256', 'intent_sha256', 'provider_sha256'))):
            raise ValueError('Missing completed physical timing proof')
    for n in large:
        p = proposal['predictions'][n]
        seconds = p.get('with_margin_seconds')
        if (type(seconds) not in (int, float) or not math.isfinite(seconds)
                or seconds <= 0 or seconds > 9570 or p.get('allowed_seconds') != 9530
                or p.get('engineering_criterion_passed') is not False):
            raise ValueError('Frozen failed prediction does not fit the approved amended cap')
    # Exact terminal records are read again on the real worker, including both
    # original failed attempts; a logical replacement is never a relabeling.
    records = gates['t1_terminal_records']
    expected = {(x['campaign'], x['run_id']): 'completed' for x in mapping.values()}
    expected.update({(ORIGINAL, n): 'failed' for n in FAILED})
    actual = {(x['campaign'], x['run_id']): x['terminal'].get('status') for x in records}
    if len(records) != 13 or len(actual) != 13 or actual != expected:
        raise ValueError('All thirteen physical T1/base terminal records required')
    by_id = {(x['campaign'], x['run_id']): x['terminal'] for x in records}
    for logical, item in mapping.items():
        if by_id[(item['campaign'], item['run_id'])] != proposal['provenance'][logical]['terminal']:
            raise ValueError('Timing proposal and real terminal differ')
    for n in FAILED:
        failed = proposal['failed_attempts_retained'][n]
        if (failed.get('status') != 'failed'
                or failed.get('terminal') != by_id[(ORIGINAL, n)]
                or any(failed.get(k) != 0 for k in ('training_updates_attempted',
                       'training_updates_completed', 'supervised_targets',
                       'endpoint_outputs', 'unresolved_scientific_units'))):
            raise ValueError('Original zero-update failures must remain exact')
    return True
