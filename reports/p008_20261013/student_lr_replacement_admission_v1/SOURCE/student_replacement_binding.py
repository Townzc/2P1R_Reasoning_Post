"""Exactly two directly authorized zero-update replacements, never parent replay.

Physical identity, budget and failed-parent evidence are separate from the
unchanged logical science config. Existing source/input admissions stay intact.
"""
import math
from decimal import Decimal, ROUND_CEILING
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_midpoint.guard import RunGuard
from .completion_student_binding import validate_student_binding
from .completion_queue import require_handoff
from .main_binding import accepted, RATE_USD_PER_HOUR

PARENT_CAMPAIGN = 'p008-students-completion-20261013-r1'
CAMPAIGN = 'p008-student-lr-replacement-20261013-r1'
LOGICAL = ('d1_b1_p0_breadth_t1', 'd1_b1_p0_depth_t1')
MAPPING = {n + '_replacement_r1': n for n in LOGICAL}
ORIGINAL_SPEC = 'ab49b0a638090f61dfd39e7391c61e4427a47b6ea94acfe6e0de3c4f606b21ee'
ZERO_FIELDS = ('training_updates_attempted', 'training_updates_completed',
               'supervised_targets', 'endpoint_outputs', 'unresolved_scientific_units')


def validate_owner(owner):
    expected = dict(authority='Direct human reply in this chat',
                    answer='批准两项补跑及 $266.04 阶段上限',
                    original_stage_reservation_cents=24968,
                    additional_reservation_cents=1636,
                    stage_cap_cents=26604, total_stage_reservation_cents=26604,
                    project_ceiling_cents=45000, protected_cents=5000,
                    maximum_student_H100_workers=8, replacement_call_count=2,
                    maximum_calls_each=1, automatic_retry=False,
                    max_worker_seconds=6001, scientific_dose_and_inputs_unchanged=True,
                    material_freeze_utc='2026-10-14T04:00:00Z', runtime_review_required=True)
    if any(type(owner.get(k)) is not type(v) or owner[k] != v for k, v in expected.items()):
        raise ValueError('Exact direct two-call replacement authority required')
    if owner.get('logical_runs') != list(LOGICAL):
        raise ValueError('Owner did not authorize this logical roster')
    return True


def make_plan(original_plan, owner, created_epoch):
    validate_owner(owner)
    if (original_plan['campaign_id'] != PARENT_CAMPAIGN
            or type(created_epoch) not in (int, float) or not math.isfinite(created_epoch)):
        raise ValueError('Original completion campaign and finite clock required')
    result = dict(campaign_id=CAMPAIGN, created_epoch=created_epoch,
                  deadline_epoch=original_plan['deadline_epoch'], total_cap_cents=1636,
                  stage_caps_cents={'replacement': 1636},
                  slots={n: dict(stage='replacement', reserved_cents=818) for n in MAPPING})
    RunGuard({}, result)
    return result


def physical_config(logical_config):
    if logical_config['run_id'] not in LOGICAL:
        raise ValueError('Only the two zero-update logical cells can be replaced')
    result = dict(logical_config)
    result['logical_run_id'] = logical_config['run_id']
    result['run_id'] = logical_config['run_id'] + '_replacement_r1'
    return result


def validate_parent(spec, logical):
    parent = spec['parents'][logical]
    proof = spec['zero_update_reconciliation']
    row = proof['runs'][logical]
    if (proof.get('passed') is not True or proof.get('failed_records_preserved') is not True
            or set(proof['runs']) != set(LOGICAL) or row['status'] != 'failed'
            or any(type(row.get(k)) is not int or row[k] != 0 for k in ZERO_FIELDS)):
        raise ValueError('Full zero-update/zero-endpoint/zero-unknown proof required')
    if parent['campaign'] != PARENT_CAMPAIGN or parent['run_id'] != logical:
        raise ValueError('Parent physical identity differs')
    claim, bound, terminal = (parent[k] for k in ('claim', 'binding', 'terminal'))
    cfg = spec['original_spec']['configs'][logical]
    old_release = spec['original_releases'][logical]
    if (row['worker_claim'] != claim or row['terminal'] != terminal
            or terminal['status'] != 'failed' or terminal['run_id'] != logical
            or terminal['claim_sha256'] != digest(claim)
            or claim['run_id'] != logical or claim['intent_sha256'] != digest(bound)
            or claim['plan_sha256'] != digest(spec['original_execution_plan'])
            or bound['run_id'] != logical or bound['config_sha256'] != digest(cfg)
            or bound['source_sha256'] != digest(old_release['source_files'])
            or bound['data_sha256'] != cfg['input_sha256']
            or row['original_input_sha256'] != cfg['input_sha256']):
        raise ValueError('Original failed claim/intent/terminal lineage differs')
    dispatched = parent['dispatch_intent']
    provider = parent['provider_release']
    if (parent['provider_app_id'] != dispatched['provider_app_id']
            or dispatched['run_id'] != logical or dispatched['config'] != cfg
            or dispatched['release'] != old_release
            or provider['app_id'] != parent['provider_app_id']
            or provider['state'] != 'stopped' or provider['owned_containers'] != 0):
        raise ValueError('Parent provider differs from preserved reconciliation')
    return parent


def validate_binding(plan, cfg, release, spec):
    validate_owner(spec['owner'])
    if (spec['mapping'] != MAPPING or set(spec['parents']) != set(LOGICAL)
            or set(spec['configs']) != set(MAPPING)
            or digest(spec['original_spec']) != ORIGINAL_SPEC
            or spec['original_spec']['plan_sha256'] != digest(spec['original_execution_plan'])
            or release['spec_sha256'] != digest(spec)
            or plan != make_plan(spec['original_execution_plan'], spec['owner'], plan['created_epoch'])
            or digest(plan) != spec['plan_sha256']):
        raise ValueError('Exact two-slot plan, logical spec and parent mapping required')
    if (spec['parent_provider_apps'] != sorted(spec['parents'][n]['provider_app_id'] for n in LOGICAL)
            or len(set(spec['parent_provider_apps'])) != 2):
        raise ValueError('Exactly two original failed provider identities required')
    budget = spec['project_budget']
    metered = Decimal(budget['workspace_summary']['metered_cost'])
    # Intentionally double-count all P008 spend already in the meter. No prior
    # reservation is reclaimed and no credit adjustment is treated as income.
    conservative = int((metered * 100).to_integral_value(rounding=ROUND_CEILING)) + 26604
    if (not metered.is_finite() or metered < 0
            or conservative != budget['double_counted_meter_plus_full_stage_cents']
            or conservative > 45000 or 50000-conservative < 5000
            or gates_budget_invalid(budget)):
        raise ValueError('Project-wide budget evidence exceeds authority')
    run = cfg['run_id']
    if run not in MAPPING or cfg != spec['configs'][run]:
        raise ValueError('Unknown or changed physical replacement config')
    logical = MAPPING[run]
    science = spec['original_spec']['configs'][logical]
    if (cfg != physical_config(science) or cfg['updates'] != 256 or cfg['targets'] != 524287
            or cfg['max_seconds'] != 6001 or cfg['seed'] != 17 or cfg['training_multiple'] != 1):
        raise ValueError('Replacement science or worker cap changed')
    gates = release['gates']
    if (gates['owner'] != spec['owner']
            or gates['zero_update_reconciliation_sha256'] != spec['zero_update_reconciliation_sha256']
            or gates['input_readback'] != spec['input_readback']
            or gates['input_readback']['passed'] is not True
            or gates['input_readback']['input_sha256'] != cfg['input_sha256']):
        raise ValueError('Actual owner, reconciliation and reused input proof required')
    accepted(gates['runtime_review'], 'student-lr-replacement-runtime',
             release['source_files'], digest(spec))
    for name in LOGICAL:
        # Validate the real original G1/config record, never synthesize a PASS.
        validate_student_binding(spec['original_execution_plan'], spec['original_spec']['configs'][name],
                                 spec['original_releases'][name], spec['original_spec'])
        validate_parent(spec, name)
    minimum = math.ceil((6001 + 700) * RATE_USD_PER_HOUR / 3600 * 100)
    if minimum > 818 or plan['slots'][run]['reserved_cents'] != 818:
        raise ValueError('Complete worker/startup envelope is under-reserved')
    return science


def gates_budget_invalid(budget):
    return (budget.get('meter_is_delayed_not_invoice') is not True
            or budget.get('historical_closed_reservations_reused') is not False
            or budget.get('p008_full_reservation_cents') != 26604)


def require_parent_records(store, spec):
    """Fresh immutable parents and original handoff; no parent record is written."""
    for logical in LOGICAL:
        parent = validate_parent(spec, logical)
        for kind, field in (('claim', 'claim'), ('intent', 'binding'), ('terminal', 'terminal')):
            if store.get(f'midpoint/{PARENT_CAMPAIGN}/{kind}/{logical}') != parent[field]:
                raise ValueError('Original failed parent record missing or changed')
        old = spec['original_releases'][logical]
        require_handoff(store, spec['original_execution_plan'], spec['original_spec']['original_plan'],
                        old['gates']['student_completion_owner'], logical)
        for row in old['gates']['required_terminals']:
            if store.get(f"midpoint/{row['campaign']}/terminal/{row['run_id']}") != row['terminal']:
                raise ValueError('Original Phase0/pool dependency changed')
    return True
