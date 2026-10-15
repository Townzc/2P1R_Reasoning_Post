"""Bind one new physical slot to a preserved failure and direct owner exception.

No old fence, claim or failed terminal is ever cleared or repurposed. Historical
acceptances establish the original recipe; only a new exact review admits this call.
"""
import math
from experiments.sft_allocation_midpoint.common import digest
from experiments.learning_regime_p009.stage1_nc_binding import validate as validate_original
from experiments.learning_regime_p009.stage1_nc_replacement_contract import (
    CAMPAIGN, RUN, RUNS, PARENT_CAMPAIGN, PARENT_RUN, ORIGINAL_NC400,
    PARENT_TARGET, PARENT_SPEC_SHA, PARENT_MANIFEST_SHA, PARENT_PRESERVED_SHA,
    PARENT_FAILURE_DIGEST, NC400_STATE_SHA, OWNER_FILE_SHA, OWNER_CANONICAL,
    SCOPE, PARENT_SCOPE, STAGE1_CAP_CENTS, PRIOR_RESERVED_CENTS, NEW_RESERVED_CENTS,
    slot, forecast)


def dispatch_key(run):
    slot(run)
    return 'midpoint/'+CAMPAIGN+'/dispatch/'+run


def logical_key(run):
    slot(run)
    return 'midpoint/p009-stage1-logical/'+PARENT_RUN+'/independent_replacement_r1'


def intent(spec, run):
    slot(run)
    return dict(run_id=run, config_sha256=digest(spec['configs'][run]),
        source_sha256=digest(spec['source_files']), data_sha256=digest(spec['inputs']),
        failed_parent_terminal_sha256=digest(spec['required_records']['midpoint/'+PARENT_CAMPAIGN+'/terminal/'+PARENT_RUN]),
        owner_exception_sha256=OWNER_FILE_SHA)


def marker(spec, run, release):
    slot(run)
    return dict(campaign=CAMPAIGN, run_id=run, original_logical_run=PARENT_RUN,
        spec_sha256=digest(spec), source_sha256=digest(spec['source_files']),
        input_manifest_sha256=digest(spec['inputs']), provider_app_id=release['dispatch_app_id'],
        execution_commit=release['execution_commit'], owner_exception_sha256=OWNER_FILE_SHA,
        failed_parent_stays_failed=True, start_from_original_base=True, automatic_retry=False)


def extended_timing(original, extension, failed_terminal):
    """Keep every old host; append full NC400 and conservatively closed NC3200 intervals."""
    train=extension['nc400_full_block_intervals'];endpoint=extension['nc400_full_endpoint_intervals']
    rows=extension['failed_parent_forecasts']
    if (len(train)!=64 or len(endpoint)!=6 or len(rows)!=56
        or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in train+endpoint)):
        raise ValueError('All original observed NC timings are required')
    for i,x in enumerate(rows):
        if x['training_blocks_left']!=64-i or x['admitted'] is not True or x['endpoint_batches_left']!=6:
            raise ValueError('Original failed-parent forecast order differs')
    deltas=[b['elapsed_worker_seconds']-a['elapsed_worker_seconds'] for a,b in zip(rows,rows[1:])]
    partial=failed_terminal['finished_epoch']-extension['failed_parent_worker_started_epoch']-rows[-1]['elapsed_worker_seconds']
    if any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in deltas+[partial]):
        raise ValueError('Unknown/negative interrupted intervals may not become zero')
    return (original['training_block_seconds']+train+deltas+[partial],
            original['endpoint_batch_seconds']+endpoint)


def parent_records(spec):
    original=spec['original_spec'];records=dict(original['required_records'])
    old=spec['original_NC_records'];prefix='midpoint/'+PARENT_CAMPAIGN+'/'
    keys={prefix+'campaign'}
    for run in (ORIGINAL_NC400,PARENT_RUN):
        claim=old.get(prefix+'claim/'+run,{})
        keys.update(prefix+k+'/'+run for k in ('claim','intent','terminal','dispatch'))
        keys.add(prefix+'attempt/'+run+'/'+claim.get('attempt_id',''))
        keys.add('midpoint/p009-stage1-logical/'+run+'/dispatch')
    if set(old)!=keys or old[prefix+'campaign']!=spec['original_plan']:
        raise ValueError('Complete original NC claim/fence/terminal/attempt lineage required')
    for run,status in ((ORIGINAL_NC400,'completed'),(PARENT_RUN,'failed')):
        c=old[prefix+'claim/'+run];t=old[prefix+'terminal/'+run]
        if (t['status']!=status or c['run_id']!=run or t['run_id']!=run
            or t['claim_sha256']!=digest(c) or t['attempt_id']!=c['attempt_id']
            or old[prefix+'attempt/'+run+'/'+c['attempt_id']]!=c
            or c['reserved_cents']!=655 or t['actual_cost_cents']!=655):
            raise ValueError('Failed parent must stay failed; completed sibling cannot be replaced')
    if old[prefix+'terminal/'+PARENT_RUN]['evidence_sha256']!=PARENT_FAILURE_DIGEST:
        raise ValueError('Original preemption evidence differs')
    records.update(old)
    return records


def validate(spec, plan, run, release):
    cap=slot(run);old=spec['original_spec']
    if digest(old)!=PARENT_SPEC_SHA or digest(spec['owner_authority'])!=OWNER_CANONICAL:
        raise ValueError('Original admitted recipe or direct bounded owner exception differs')
    validate_original(old,spec['original_plan'],PARENT_RUN,release['original_release'])
    for n,h in old['source_files'].items():
        if spec['source_files'].get(n)!=h:
            raise ValueError('Every original accepted source byte must be retained')
    records=parent_records(spec);prefix='midpoint/'+PARENT_CAMPAIGN+'/'
    wanted=dict(scope=SCOPE,campaign=CAMPAIGN,slots={RUN:cap},
        owner_authority_file_sha256=OWNER_FILE_SHA,parent_packet_target=PARENT_TARGET,
        parent_packet_manifest_sha256=PARENT_MANIFEST_SHA,parent_preservation_file_sha256=PARENT_PRESERVED_SHA,
        stage1_cap_cents=STAGE1_CAP_CENTS,prior_stage1_reserved_cents=PRIOR_RESERVED_CENTS,
        new_reserved_cents=NEW_RESERVED_CENTS,experiment_cap_cents=13000,
        project_cap_cents=45000,protected_original_cents=5000,
        stage_remaining_before_cents={RUN:STAGE1_CAP_CENTS-PRIOR_RESERVED_CENTS},
        maximum_concurrent_workers=4,first_paid_measurement_exceptions=0,
        start_from_original_base=True,resume_from_failed_state=False,original_failed_parent_retained=True,
        training_process_exit_before_vllm=True,historical_HF_effect_comparison=False,
        deterministic_cublas_workspace=':4096:8',torch_threads=4,
        configs={RUN:old['configs'][PARENT_RUN]},required_records=records)
    if any(spec.get(k)!=v for k,v in wanted.items()):
        raise ValueError('Exact one-slot replacement, owner, lineage or whole budget differs')
    for k in ('inputs','remote_inputs','base','gold_file_sha256','G0_report_sha256',
              'input_report_sha256','input_basis_file_sha256','input_archive_file_sha256',
              'internal_only_amendment_sha256','engine_kwargs'):
        if spec.get(k)!=old[k]:raise ValueError('Original science/inputs/model/engine changed')
    expected_apps=old['required_stopped_app_ids']+[
        spec['original_NC_records'][prefix+'dispatch/'+r]['provider_app_id'] for r in (ORIGINAL_NC400,PARENT_RUN)]
    if spec['required_stopped_app_ids']!=expected_apps or len(set(expected_apps))!=9:
        raise ValueError('Every original predecessor and both NC apps must be retained')
    if (plan['campaign_id']!=CAMPAIGN or digest(plan)!=spec['plan_sha256']
        or plan['slots']!={RUN:dict(stage='stage1_nc_replacement',reserved_cents=655)}
        or plan['total_cap_cents']!=655 or plan['stage_caps_cents']!={'stage1_nc_replacement':655}
        or plan['deadline_epoch']!=spec['original_plan']['deadline_epoch']
        or release['source_files']!=spec['source_files'] or release['input_readback']!=spec['inputs']):
        raise ValueError('Single new plan/source/original readback differs')
    train,endpoint=extended_timing(old['timing'],spec['timing_extension'],records[prefix+'terminal/'+PARENT_RUN])
    timing=spec['timing']
    if (timing['training_block_seconds']!=train or timing['endpoint_batch_seconds']!=endpoint
        or timing['original_training_hosts']!=old['timing']['training_hosts']
        or timing['additional_physical_hosts']!=[ORIGINAL_NC400,PARENT_RUN]
        or timing['total_training_hosts']!=20 or timing['failed_last_interval_is_closure_proxy'] is not True):
        raise ValueError('No slow original or interrupted-host observation may be dropped')
    review=release['runtime_review']
    review_fields=dict(scope=SCOPE,source_files=spec['source_files'],spec_sha256=digest(spec),
        timing_sha256=digest(timing),owner_authority_file_sha256=OWNER_FILE_SHA,
        parent_packet_target=PARENT_TARGET,parent_packet_manifest_sha256=PARENT_MANIFEST_SHA,
        parent_preservation_file_sha256=PARENT_PRESERVED_SHA,
        input_basis_file_sha256=spec['input_basis_file_sha256'],input_archive_file_sha256=spec['input_archive_file_sha256'],
        all_20_training_hosts_included=True,failed_parent_interval_retained_as_proxy=True,
        uncalibrated_timing_proxy_scope_accepted=True,training_process_exit_before_vllm=True,
        new_reserved_cents=655,prior_stage1_reserved_cents=1310,first_paid_measurement_exceptions=0,
        independent_failed_parent_replacement_accepted=True)
    if (any(review.get(k)!=v for k,v in review_fields.items())
        or review.get('decision') not in ('PASS','PASS-WITH-NOTES')
        or review.get('target_commit')!=release['review_target']
        or len(review.get('target_commit',''))!=40 or len(review.get('report_commit',''))!=40
        or len(review.get('report_sha256',''))!=64):
        raise ValueError('True exact new runtime/source/input/numeric review is required')
    p=release['parent_disposition_review']
    if (p.get('scope')!=PARENT_SCOPE or p.get('target_commit')!=PARENT_TARGET
        or p.get('decision') not in ('PASS','PASS-WITH-NOTES')
        or p.get('actual_n400_integrity') not in ('PASS','PASS-WITH-NOTES')
        or p.get('failed_n3200_preservation') not in ('PASS','PASS-WITH-NOTES')
        or p.get('paired_NC_gate_available') is not False or p.get('S1_admitted') is not False
        or p.get('parent_manifest_sha256')!=PARENT_MANIFEST_SHA
        or p.get('failed_preservation_sha256')!=PARENT_PRESERVED_SHA
        or p.get('nc400_state_sha256')!=NC400_STATE_SHA
        or len(p.get('report_commit',''))!=40 or len(p.get('report_sha256',''))!=64):
        raise ValueError('Real actual completed/failed parent outcome disposition is required')
    b=release['budget']
    if (b.get('stage1_prior_reserved_cents')!=1310 or b.get('new_reserved_cents')!=655
        or b.get('stage1_cap_cents')!=5000 or b.get('experiment_cap_cents')!=13000
        or type(b.get('project_prior_upper_cents')) is not int
        or not 0<=b['project_prior_upper_cents']<=32000):
        raise ValueError('Retain all original reservations; one bounded new slot only')
    f=forecast(0.,64,6,train,endpoint,STAGE1_CAP_CENTS-PRIOR_RESERVED_CENTS)
    if not f['admitted']:raise ValueError('All observed host timing and whole-stage budget must fit')
    return cap


def require_unused(records,run,plan,logical_records):
    slot(run);prefix='midpoint/'+CAMPAIGN+'/'
    if records not in ({},{prefix+'campaign':plan}):
        raise ValueError('Any original/unknown replacement work blocks a new submission')
    expected={'midpoint/p009-stage1-logical/'+r+'/dispatch' for r in (ORIGINAL_NC400,PARENT_RUN)}
    if set(logical_records)!=expected:
        raise ValueError('Prior/unknown replacement or another Stage1 dispatch blocks this call')
    if any(not isinstance(v,dict) or not v.get('provider_app_id') for v in logical_records.values()):
        raise ValueError('Original logical predecessors are missing or unknown')
