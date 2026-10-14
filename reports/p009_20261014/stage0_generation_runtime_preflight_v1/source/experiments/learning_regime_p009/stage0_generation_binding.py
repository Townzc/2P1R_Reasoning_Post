"""Exact finite Stage0 admission; original P0 is reuse-only, never replayed."""
from experiments.sft_allocation_midpoint.common import digest
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs
from experiments.learning_regime_p009.stage0_generation_contract import (
    MODELS, DATASETS, SLOTS, slot_checked, PRIOR_RESERVED_CENTS,
)

CAMPAIGN = 'p009-stage0-generation-20261014-r1'
SCOPE = 'p009-stage0-generation-exact-runtime-and-numeric'
AMENDMENT_SHA = '4f2a56f3e794fd4182e1d9e36c30af0c09c0d6751dea157a3abd34918abf2872'
P0_ORACLE_SHA = 'b36d5c3730ec616f8220ebf04be35a3a75a52961028e4ad6d1ba9aca92e001ab'
P0_TARGET = '26d7cff6fe2b305542c70a3de1713d42ee87f015'
AMENDMENT_TARGET = '2d3e1dd13277d556b18a3569cd80c252b112d54b'
AMENDMENT_REPORT_SHA = '9f13c52becf997815399a494bf78dede442de7939a47b4e5f091c9d589508a74'
A2_REPORT_SHA = 'b129dceb9910a1c282e77967bb5f4a720212cb32f9c119f22e9ec52f64c2360d'


def dispatch_key(run):
    if run not in SLOTS:
        raise ValueError('Not a frozen slot')
    return 'midpoint/'+CAMPAIGN+'/dispatch/'+run


def dataset_key(name):
    if name not in DATASETS:
        raise ValueError('Not a frozen dataset')
    return 'midpoint/p009-stage0-frozen-dataset/'+name+'/dispatch'


def marker(spec, run, release):
    return dict(campaign=CAMPAIGN, run_id=run, spec_sha256=digest(spec),
        source_sha256=digest(spec['source_files']), provider_app_id=release['dispatch_app_id'],
        execution_commit=release['execution_commit'], input_manifest_sha256=digest(spec['inputs']),
        dataset_names=list(SLOTS[run]['datasets']), new_training_updates=0)


def intent(spec, run):
    return dict(run_id=run, config_sha256=digest(dict(spec_sha256=digest(spec), run_id=run)),
        source_sha256=digest(spec['source_files']), data_sha256=digest(spec['inputs']))


def validate_release(spec, plan, run, release):
    slot = slot_checked(run)
    exact = dict(scope=SCOPE, campaign=CAMPAIGN, engine_kwargs=engine_kwargs(),
        datasets=DATASETS, slots={n:slot_checked(n) for n in SLOTS},
        prior_reserved_cents=1004, stage0_cap_cents=2000, experiment_cap_cents=11000,
        total_new_reserved_cents=867, project_cap_cents=45000, protected_original_cents=5000,
        new_training_updates=0, fresh_outputs=14450, p0_regeneration=0,
        first_paid_batch_exceptions=3, maximum_concurrent_workers=3,
        internal_only_amendment_sha256=AMENDMENT_SHA, original_P0_oracle_sha256=P0_ORACLE_SHA)
    if any(spec.get(k) != v for k, v in exact.items()):
        raise ValueError('Exact science/engine/budget/owner-scope binding changed')
    if (plan['campaign_id'] != CAMPAIGN or digest(plan) != spec['plan_sha256']
            or plan['slots'] != {n:dict(stage='stage0_generation',reserved_cents=s['reserved_cents'])
                                 for n,s in SLOTS.items()}
            or plan['stage_caps_cents'] != {'stage0_generation':867} or plan['total_cap_cents'] != 867
            or release['source_files'] != spec['source_files']):
        raise ValueError('Fixed finite slots or exact sources differ')
    for name, model in MODELS.items():
        if (any(spec['models'][name].get(k) != v for k,v in model.items())
                or not spec['models'][name].get('files')
                or not spec['models'][name]['remote_path'].startswith('/evidence/')):
            raise ValueError('Original model identity/complete files differ')
    if {x['file']:x['sha256'] for x in DATASETS.values()} != {
            n:v['sha256'] for n,v in spec['inputs'].items()}:
        raise ValueError('Only the seven frozen generation inputs are permitted')
    review = release['runtime_review']
    if (review.get('scope') != SCOPE or review.get('decision') not in ('PASS','PASS-WITH-NOTES')
            or review.get('target_commit') != release['review_target']
            or len(review.get('report_commit','')) != 40 or len(review.get('report_sha256','')) != 64
            or review.get('spec_sha256') != digest(spec) or review.get('source_files') != spec['source_files']
            or review.get('first_paid_batch_exceptions_accepted') != 3
            or review.get('total_new_reserved_cents') != 867
            or review.get('internal_only_amendment_sha256') != AMENDMENT_SHA):
        raise ValueError('Real exact executable/input/numeric/bootstrap review required')
    scope = release['internal_only_review']; a2 = release['p0_integrity_review']
    if (scope.get('scope') != 'p009-p0-vllm-internal-only-owner-amendment'
            or scope.get('decision') != 'PASS' or scope.get('target_commit') != AMENDMENT_TARGET
            or scope.get('comparison_scope') != 'P009_within_vllm_only'
            or scope.get('post_result_amendment') is not True
            or scope.get('amendment_sha256') != AMENDMENT_SHA
            or scope.get('original_scientific_comparability_passed') is not False
            or scope.get('report_sha256') != AMENDMENT_REPORT_SHA
            or a2.get('scope') != 'p009-p0-complete-engine-parity-A2'
            or a2.get('decision') != 'PASS_RAW_LINEAGE_ACCOUNTING_ONLY'
            or a2.get('target_commit') != P0_TARGET
            or a2.get('report_sha256') != A2_REPORT_SHA
            or a2.get('report_sha256') != scope.get('actual_A2_report_sha256')):
        raise ValueError('Original raw A2 and exact post-result scope must both be retained')
    for item in (scope, a2):
        if len(item.get('report_commit','')) != 40 or len(item.get('report_sha256','')) != 64:
            raise ValueError('Fixed full review provenance required')
    budget = release['budget']
    if (budget.get('prior_reserved_cents') != PRIOR_RESERVED_CENTS
            or budget.get('new_slots_reserved_cents') != 867
            or budget.get('stage0_cap_cents') != 2000
            or budget.get('experiment_cap_cents') != 11000
            or type(budget.get('project_prior_upper_cents')) is not int
            or not 0 <= budget['project_prior_upper_cents'] <= 34000
            or release['input_readback'] != spec['inputs']
            or release['olmo_model_readback'] != spec['models']['olmo']['files']):
        raise ValueError('Budget or original uploaded bytes lack exact readback')
    if not spec.get('required_P0_records') or len(spec.get('P0_app_ids',[])) != 4:
        raise ValueError('Completed P0 and all failed predecessors remain bound')
    return slot


def require_unused(records, run, plan):
    """Complete campaign listing is checked before any dispatch marker/spawn."""
    prefix = 'midpoint/'+CAMPAIGN+'/'
    registered = records.get(prefix+'campaign')
    if prefix+'campaign' in records and registered != plan:
        raise ValueError('Existing campaign plan differs')
    endings = (f'claim/{run}',f'intent/{run}',f'terminal/{run}',f'dispatch/{run}')
    for key in records:
        if (key in {prefix+x for x in endings} or key.startswith(prefix+'attempt/'+run+'/')
                or key.startswith(prefix+run+'/')):
            raise ValueError('Any prior or uncertain work blocks re-dispatch')
    order = list(SLOTS); index = order.index(run)
    for earlier in order[:index]:
        dispatch = records.get(prefix+'dispatch/'+earlier)
        if (not isinstance(dispatch,dict) or dispatch.get('campaign') != CAMPAIGN
                or dispatch.get('run_id') != earlier or not dispatch.get('provider_app_id')):
            raise ValueError('Fixed reservation/dispatch order must be retained')
        terminal = records.get(prefix+'terminal/'+earlier)
        if prefix+'terminal/'+earlier in records and (
                not isinstance(terminal,dict) or terminal.get('status') != 'completed'):
            raise ValueError('Earlier failed/unknown slot requires concrete disposition')
    for later in order[index+1:]:
        if prefix+'dispatch/'+later in records:
            raise ValueError('Out-of-order dispatch exists')
