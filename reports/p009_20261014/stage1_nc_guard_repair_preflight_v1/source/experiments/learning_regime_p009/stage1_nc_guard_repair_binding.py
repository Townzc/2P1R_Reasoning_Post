"""One pre-claim schema repair; no original source, fence or science is rewritten."""
from datetime import datetime
from experiments.sft_allocation_midpoint.common import digest
from experiments.learning_regime_p009 import stage1_nc_replacement_binding as old
from experiments.learning_regime_p009.stage1_nc_replacement_contract import slot, forecast

CAMPAIGN=old.CAMPAIGN
RUN=old.RUN
SCOPE='p009-stage1-NC-preclaim-guard-intent-repair-runtime-and-numeric'
REQUEST='p009-stage1-NC-guard-intent-repair-r1'
OLD_SPEC_SHA='35b1755261290f97c4da03c1121b73ad1cb47e0abf52f657790464bfc381dcaf'
FAILED_APP='ap-iCt0KOKWNfNojiIzZv1LoM'
FAILED_CALL='fc-01M4Z33847TMFE5KP93N8B5NXQ'
NEW_FILES=(
    'experiments/learning_regime_p009/stage1_nc_guard_repair_binding.py',
    'experiments/learning_regime_p009/modal_stage1_nc_guard_repair.py',
    'scripts/p009_stage1_nc_guard_repair_io.py',
    'scripts/audit_p009_stage1_nc_guard_repair.py',
)


def dispatch_key(run):
    slot(run)
    return 'midpoint/'+CAMPAIGN+'/guard_intent_repair_dispatch/'+run


def logical_key(run):
    slot(run)
    return old.logical_key(run)+'/guard_intent_repair_r1'


def intent(spec,run):
    """The unchanged real RunGuard accepts exactly these four base fields."""
    slot(run)
    return dict(run_id=run,config_sha256=digest(spec['configs'][run]),
        source_sha256=digest(spec['source_files']),data_sha256=digest(spec['inputs']))


def check_proxy(spec,release):
    authority=spec['overnight_authority'];decision=release['owner_proxy_decision'];c=decision['comment']
    event=datetime.fromisoformat(c['created_at'].replace('Z','+00:00'))
    lower=datetime.fromisoformat(authority['recorded_utc']);upper=datetime.fromisoformat(authority['expires_utc'])
    if (c['user']['login']!='Townzc' or c.get('author_association')!='OWNER'
        or not c['body'].startswith('【Owner 代理决定】') or REQUEST not in c['body']
        or len(c['body'])<80 or not lower<=event<upper
        or c['html_url']!='https://github.com/Townzc/2P1R_Reasoning_Post/issues/13#issuecomment-'+str(c['id'])
        or decision.get('decision')!='APPROVE_ONE_REPAIR'
        or decision.get('spec_sha256')!=digest(spec)
        or decision.get('comment_sha256')!=digest(c)
        or len(decision.get('raw_comment_file_sha256',''))!=64
        or decision.get('single_new_call') is not True or decision.get('new_reserved_cents')!=655
        or decision.get('science_and_decision_rules_unchanged') is not True):
        raise ValueError('An original scoped proxy comment and independent exact audit are required')
    return decision


def marker(spec,run,release):
    slot(run)
    return dict(campaign=CAMPAIGN,run_id=run,spec_sha256=digest(spec),
        source_sha256=digest(spec['source_files']),provider_app_id=release['dispatch_app_id'],
        execution_commit=release['execution_commit'],preclaim_app_id=FAILED_APP,
        preclaim_proof_sha256=spec['preclaim_proof_file_sha256'],
        owner_proxy_comment_sha256=release['owner_proxy_decision']['comment_sha256'],
        prior_stage1_reserved_cents=1965,new_reserved_cents=655,
        original_fences_retained=True,automatic_retry=False)


def validate(spec,plan,run,release):
    cap=slot(run);original=spec['original_replacement_spec']
    if digest(original)!=OLD_SPEC_SHA:
        raise ValueError('The exact previously audited and failed entry must remain immutable')
    old.validate(original,plan,run,release['original_replacement_release'])
    changed={'scope','source_files','required_records','required_stopped_app_ids',
             'prior_stage1_reserved_cents','stage_remaining_before_cents'}
    if any(spec.get(k)!=v for k,v in original.items() if k not in changed):
        raise ValueError('Original recipe, dose, input, timing, plan or caps changed')
    if (set(spec['source_files'])!=set(original['source_files'])|set(NEW_FILES)
        or any(spec['source_files'][k]!=v for k,v in original['source_files'].items())
        or spec['scope']!=SCOPE or spec['prior_stage1_reserved_cents']!=1965
        or spec['stage_remaining_before_cents']!={RUN:3035}
        or spec['required_stopped_app_ids']!=original['required_stopped_app_ids']+[FAILED_APP]
        or release['source_files']!=spec['source_files'] or release['input_readback']!=spec['inputs']):
        raise ValueError('Exact new source or retained preclaim reservation differs')
    proof=spec['preclaim_proof'];records=spec['preclaim_records']
    expected={'midpoint/'+CAMPAIGN+'/campaign':plan,
              old.dispatch_key(run):spec['original_dispatch_marker'],
              old.logical_key(run):spec['original_dispatch_marker']}
    if records!=expected or spec['required_records']!={**original['required_records'],**records}:
        raise ValueError('Keep the exact registered plan and both consumed dispatch fences')
    if (proof.get('passed') is not True or proof.get('app_id')!=FAILED_APP or proof.get('call_id')!=FAILED_CALL
        or proof.get('ledger_sha256')!=spec['preclaim_ledger_file_sha256']
        or any(proof.get(k) is not False for k in ('claim','intent','attempt','terminal','remote_output_directory','checkpoint'))
        or proof.get('training_updates')!=0 or proof.get('endpoint_outputs')!=0
        or proof.get('reserved_cents_retained')!=655
        or spec['original_dispatch_marker']['provider_app_id']!=FAILED_APP):
        raise ValueError('Real stopped preclaim zero-work evidence is required; never invent a terminal')
    decision=check_proxy(spec,release);review=release['runtime_review']
    wanted=dict(scope=SCOPE,source_files=spec['source_files'],spec_sha256=digest(spec),
        timing_sha256=digest(spec['timing']),preclaim_proof_file_sha256=spec['preclaim_proof_file_sha256'],
        preclaim_manifest_file_sha256=spec['preclaim_manifest_file_sha256'],
        owner_authority_file_sha256=spec['overnight_authority_file_sha256'],
        owner_proxy_comment_sha256=decision['comment_sha256'],
        original_guard_four_field_schema=True,original_fences_and_failed_parents_retained=True,
        no_prior_replacement_training_or_endpoint=True,one_new_entry_call_only=True,
        prior_stage1_reserved_cents=1965,new_reserved_cents=655,first_paid_measurement_exceptions=0)
    if (any(review.get(k)!=v for k,v in wanted.items())
        or review.get('decision') not in ('PASS','PASS-WITH-NOTES')
        or review.get('target_commit')!=release['review_target']
        or any(len(review.get(k,''))!=n for k,n in (('target_commit',40),('report_commit',40),('report_sha256',64)))):
        raise ValueError('Proxy authority cannot substitute for this exact independent source/numeric audit')
    b=release['budget']
    if (any(b.get(k)!=v for k,v in dict(stage1_prior_reserved_cents=1965,new_reserved_cents=655,
          stage1_cap_cents=5000,experiment_cap_cents=13000).items())
        or type(b.get('project_prior_upper_cents')) is not int or not 0<=b['project_prior_upper_cents']<=32000):
        raise ValueError('All preclaim/setup failures retain reservations; no automatic budget release')
    if not forecast(0.,64,6,spec['timing']['training_block_seconds'],spec['timing']['endpoint_batch_seconds'],3035)['admitted']:
        raise ValueError('Original full-host timing and remaining stage budget must fit')
    return cap


def require_unused(records,run,plan,logical_records,spec):
    slot(run)
    expected={k:v for k,v in spec['preclaim_records'].items() if k.startswith('midpoint/'+CAMPAIGN+'/')}
    old_logical={k:v for k,v in spec['required_records'].items() if k.startswith('midpoint/p009-stage1-logical/')}
    if records!=expected or logical_records!=old_logical:
        raise ValueError('Any claim, attempt, repair marker, partial or unknown work blocks dispatch')
