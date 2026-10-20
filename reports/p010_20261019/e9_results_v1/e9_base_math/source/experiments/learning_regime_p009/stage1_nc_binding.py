"""Exact two-NC slot, input, scientific-review and operational admission.

This module neither creates an acceptance nor grants authority to call a model.
Every partial dispatch/fence/claim is permanent, including unknown outcomes.
"""
from experiments.sft_allocation_midpoint.common import digest
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs
from experiments.learning_regime_p009.stage1_nc_contract import (
    CAMPAIGN, RUNS, slot, forecast, STAGE1_CAP_CENTS, STAGE1_NC_RESERVE_CENTS,
)

SCOPE = 'p009-stage1-NC-exact-runtime-and-timing-numeric'
G0_REPORT = '0e30ac3c2e3960042d791ea8b2ca40071342a0e3194a5697cdbff0213fc96cd1'
INPUT_REPORT = 'c9b44a8090c1cde9ec4e64361cc0ae47ad06a1798925c38aaf87ad9a6fbe58e8'
INPUT_BASIS = 'af7149bd26f0a46762f1a108e9ff6c9e6f1c3dadb9d9b4532aec6319f7b4be6a'
INPUT_ARCHIVE = '266fde7c700a5360594163162f24b662d04c51a306ec645445223c479c6ce92e'
INTERNAL_AMENDMENT = '4f2a56f3e794fd4182e1d9e36c30af0c09c0d6751dea157a3abd34918abf2872'


def dispatch_key(run):
    slot(run)
    return 'midpoint/'+CAMPAIGN+'/dispatch/'+run


def logical_key(run):
    slot(run)
    return 'midpoint/p009-stage1-logical/'+run+'/dispatch'


def intent(spec, run):
    return dict(run_id=run, config_sha256=digest(spec['configs'][run]),
                source_sha256=digest(spec['source_files']), data_sha256=digest(spec['inputs']))


def marker(spec, run, release):
    return dict(campaign=CAMPAIGN, run_id=run, spec_sha256=digest(spec),
                source_sha256=digest(spec['source_files']),
                input_manifest_sha256=digest(spec['inputs']),
                provider_app_id=release['dispatch_app_id'],
                execution_commit=release['execution_commit'], automatic_retry=False)


def reviewed(item, scope, target, report_sha):
    if (item.get('scope') != scope or item.get('target_commit') != target
            or item.get('report_sha256') != report_sha
            or len(item.get('report_commit', '')) != 40):
        raise ValueError('Real exact fixed scoped review required')


def validate(spec, plan, run, release):
    cap = slot(run)
    wanted = dict(scope=SCOPE, campaign=CAMPAIGN, slots={k:slot(k) for k in RUNS},
        engine_kwargs=engine_kwargs(), stage1_cap_cents=STAGE1_CAP_CENTS,
        new_reserved_cents=STAGE1_NC_RESERVE_CENTS, experiment_cap_cents=13000,
        project_cap_cents=45000, protected_original_cents=5000,
        G0_report_sha256=G0_REPORT, input_report_sha256=INPUT_REPORT,
        input_basis_file_sha256=INPUT_BASIS, input_archive_file_sha256=INPUT_ARCHIVE,
        internal_only_amendment_sha256=INTERNAL_AMENDMENT,
        maximum_concurrent_workers=4, first_paid_measurement_exceptions=0,
        deterministic_cublas_workspace=':4096:8', torch_threads=4,
        training_process_exit_before_vllm=True, historical_HF_effect_comparison=False)
    if any(spec.get(k) != v for k,v in wanted.items()):
        raise ValueError('Exact NC science/engine/owner budget scope changed')
    if (plan['campaign_id'] != CAMPAIGN or digest(plan) != spec['plan_sha256']
            or plan['slots'] != {k:dict(stage='stage1_nc', reserved_cents=slot(k)['reserved_cents']) for k in RUNS}
            or plan['total_cap_cents'] != STAGE1_NC_RESERVE_CENTS
            or plan['stage_caps_cents'] != {'stage1_nc':STAGE1_NC_RESERVE_CENTS}
            or release['source_files'] != spec['source_files']
            or release['input_readback'] != spec['inputs']
            or not spec.get('base', {}).get('files')
            or spec['base']['remote_path'] != spec['base']['tokenizer_remote_path']
            or not spec['base']['remote_path'].startswith('/evidence/')
            or not spec['remote_inputs'].startswith('/evidence/'+CAMPAIGN+'/inputs/')):
        raise ValueError('Finite plan/source/input/base-tokenizer binding differs')
    for name in RUNS:
        cfg = spec['configs'][name]; recipe = slot(name)
        if any(cfg.get(k) != recipe[k] for k in ('setting','seed','n','updates','targets')):
            raise ValueError('Actual immutable NC recipe differs')
    if spec['stage_remaining_before_cents'] != {
            k:STAGE1_CAP_CENTS-i*slot(k)['reserved_cents'] for i,k in enumerate(RUNS)}:
        raise ValueError('Whole original Stage1 reservation basis required')
    review = release['runtime_review']
    if (review.get('scope') != SCOPE or review.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or review.get('target_commit') != release['review_target']
            or len(review.get('report_commit','')) != 40 or len(review.get('report_sha256','')) != 64
            or review.get('source_files') != spec['source_files']
            or review.get('spec_sha256') != digest(spec)
            or review.get('timing_sha256') != digest(spec['timing'])
            or review.get('input_basis_file_sha256') != INPUT_BASIS
            or review.get('input_archive_file_sha256') != INPUT_ARCHIVE
            or review.get('all_18_training_hosts_included') is not True
            or review.get('uncalibrated_timing_proxy_scope_accepted') is not True
            or review.get('training_process_exit_before_vllm') is not True
            or review.get('new_reserved_cents') != STAGE1_NC_RESERVE_CENTS
            or review.get('first_paid_measurement_exceptions') != 0):
        raise ValueError('Actual exact executable AND numeric source-bound review is missing')
    g0 = release['G0_review']
    reviewed(g0, 'p009-stage0-generation-complete-raw-and-GSM-G0-A2',
             '192f9156c9235d1bcc3433ac5eade608ef5bbec9', G0_REPORT)
    if (g0.get('decision') != 'PASS_RAW_INTEGRITY_WITH_GSM_GATE_DISPOSITIONS'
            or g0.get('G0', {}).get('NC') != dict(caps=[48,43], n=1319, passed=True,
                                                 student_zero_correct=650, teacher_correct=1106)):
        raise ValueError('Actual NC G0 must pass independently of S1/S2')
    core = release['core_review']; inp = release['input_review']; internal = release['internal_only_review']
    reviewed(core, 'p009-stage1-scientific-training-and-endpoint-core-code',
             '919ab478f4301333e79946d2e7427a457d165108', INPUT_REPORT)
    reviewed(inp, 'p009-stage1-NC-exact-input-and-plan',
             '7abac8610879ec3d79c49177dd29c1a6e7d934e0', INPUT_REPORT)
    for value in (core, inp):
        if value.get('decision') not in ('PASS','PASS-WITH-NOTES'):
            raise ValueError('Original actual NC core/input review must pass')
        if any(spec['source_files'].get(k) != v for k,v in value['source_files'].items()):
            raise ValueError('Accepted transitive source bytes changed')
    if inp.get('basis_file_sha256') != INPUT_BASIS or inp.get('archive_file_sha256') != INPUT_ARCHIVE:
        raise ValueError('Exact actual NC input basis/archive differs')
    reviewed(internal, 'p009-p0-vllm-internal-only-owner-amendment',
             '2d3e1dd13277d556b18a3569cd80c252b112d54b',
             '9f13c52becf997815399a494bf78dede442de7939a47b4e5f091c9d589508a74')
    if (internal.get('decision') != 'PASS' or internal.get('amendment_sha256') != INTERNAL_AMENDMENT
            or internal.get('comparison_scope') != 'P009_within_vllm_only'
            or internal.get('original_scientific_comparability_passed') is not False):
        raise ValueError('Original P0 failure and owner internal-only scope remain binding')
    budget = release['budget']
    if (budget.get('stage1_prior_reserved_cents') != 0
            or budget.get('new_reserved_cents') != STAGE1_NC_RESERVE_CENTS
            or budget.get('stage1_cap_cents') != STAGE1_CAP_CENTS
            or budget.get('experiment_cap_cents') != 13000
            or type(budget.get('project_prior_upper_cents')) is not int
            or not 0 <= budget['project_prior_upper_cents'] <= 32000):
        raise ValueError('Whole experiment and Stage1 budget not bound')
    f = forecast(0., 64, 6, spec['timing']['training_block_seconds'],
                 spec['timing']['endpoint_batch_seconds'], spec['stage_remaining_before_cents'][run])
    if (not f['admitted'] or len(spec['timing']['training_hosts']) != 18
            or not spec.get('required_records') or len(spec.get('required_stopped_app_ids', [])) != 7):
        raise ValueError('All prior timing/lineage and finite forecast must be admitted')
    return cap


def require_unused(records, run, plan):
    prefix = 'midpoint/'+CAMPAIGN+'/'
    if prefix+'campaign' in records and records[prefix+'campaign'] != plan:
        raise ValueError('An existing immutable campaign plan differs')
    for key in records:
        if not key.startswith(prefix):
            raise ValueError('Foreign namespace in full campaign listing')
        suffix = key[len(prefix):]; parts = suffix.split('/')
        valid = (suffix == 'campaign'
            or (len(parts)==2 and parts[0] in ('claim','intent','terminal','dispatch') and parts[1] in RUNS)
            or (len(parts)==3 and parts[0]=='attempt' and parts[1] in RUNS and bool(parts[2]))
            or (len(parts)==3 and parts[0] in RUNS and parts[1] in ('unit','done') and bool(parts[2])))
        if not valid:
            raise ValueError('Unknown campaign record blocks a new dispatch')
        if (suffix in {f'{k}/{run}' for k in ('claim','intent','terminal','dispatch')}
                or suffix.startswith('attempt/'+run+'/') or suffix.startswith(run+'/')):
            raise ValueError('Any claim/intent/attempt/unit/result blocks resubmission')
    order = list(RUNS); i = order.index(run)
    for earlier in order[:i]:
        prior = records.get(dispatch_key(earlier))
        if not isinstance(prior, dict) or not prior.get('provider_app_id'):
            raise ValueError('NC fixed dispatch order must be retained')
        if prefix+'terminal/'+earlier in records and records[prefix+'terminal/'+earlier].get('status') != 'completed':
            raise ValueError('An earlier failure/unknown needs a concrete disposition')
    if any(dispatch_key(later) in records for later in order[i+1:]):
        raise ValueError('Later dispatch exists before this original slot')
