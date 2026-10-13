"""T8-only admission after the complete, separately reviewed T1 timing roster.

This module cannot create an acceptance. Both source review and the numerical
review must name the actual new source/spec and the immutable timing proposal.
Failed original slots stay failed; replacements have distinct physical names.
"""
import math
from experiments.sft_allocation_midpoint.common import digest
from .completion_student_binding import validate_student_binding as validate_original
from .main_binding import accepted

ORIGINAL = 'p008-students-completion-20261013-r1'
REPLACEMENTS = 'p008-student-lr-replacement-20261013-r1'
FAILED = ('d1_b1_p0_breadth_t1', 'd1_b1_p0_depth_t1')


def expected_mapping(spec):
    small = sorted(n for n, c in spec['configs'].items()
                   if c.get('training_multiple') == 1)
    if len(small) != 10 or not set(FAILED) <= set(small):
        raise ValueError('Original ten T1 members required')
    return {n: dict(campaign=REPLACEMENTS if n in FAILED else ORIGINAL,
                   run_id=n + '_replacement_r1' if n in FAILED else n)
            for n in small + ['base']}


def validate_timing_gate(cfg, release, spec):
    gates = release['gates']
    proposal = gates['t8_timing_proposal']
    review = gates['t8_numeric_review']
    accepted(review, 't8-numeric', release['source_files'], digest(spec))
    large = sorted(n for n, c in spec['configs'].items()
                   if c.get('training_multiple') == 8)
    mapping = expected_mapping(spec)
    if (len(large) != 8 or cfg['run_id'] not in large
            or cfg['training_multiple'] != 8 or cfg['role'] != 'main'
            or cfg['updates'] != 2048 or cfg['targets'] != 4194296
            or cfg['max_seconds'] != 9560):
        raise ValueError('Only the original eight unattempted full-dose T8 slots')
    if (review.get('passed') is not True or review.get('N2_closed') is not True
            or review.get('accepted_runs') != large
            or review.get('worker_caps') != {n: 9560 for n in large}
            or review.get('proposal_digest') != digest(proposal)
            or review.get('common_plan_gate_sha256') != spec['common_plan_gate_sha256']):
        raise ValueError('Actual complete numerical N2 acceptance is missing')
    # The estimate itself deliberately never grants permission. Acceptance is
    # a separate reviewed record, not a mutation of the original proposal.
    if (proposal.get('N2_closed') is not False
            or proposal.get('runtime_admission') is not False
            or proposal.get('engineering_criterion_passed') is not True
            or proposal.get('failed_host_dropped') is not False
            or proposal.get('new_model_calls') != 0
            or proposal.get('spec_sha256') != digest(spec)
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
                or seconds <= 0 or seconds > 9530 or p.get('allowed_seconds') != 9530
                or p.get('engineering_criterion_passed') is not True):
            raise ValueError('A reviewed T8 prediction does not fit the original cap')
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


def validate_student_binding(plan, cfg, release, spec):
    validate_original(plan, cfg, release, spec)
    return validate_timing_gate(cfg, release, spec)


def require_timing_terminals(store, gates):
    for item in gates['t1_terminal_records']:
        key = 'midpoint/' + item['campaign'] + '/terminal/' + item['run_id']
        if store.get(key) != item['terminal']:
            raise ValueError('A completed or failed T1 dependency changed')
    return True


def pending_across_queues(queues, store):
    """Read both canonical dispatch rosters; uncertain calls occupy capacity."""
    from pathlib import Path
    from experiments.sft_allocation_midpoint.common import read
    occupied = []
    for root, expected_campaign in queues:
        root = Path(root)
        plan = read(root/'plan.json')
        if plan['campaign_id'] != expected_campaign:
            raise ValueError('Queue identity differs')
        prefix = 'midpoint/' + expected_campaign + '/'
        for path in root.glob('runs/*/dispatch_intent.json'):
            item = read(path); run = item['run_id']
            if path.parent.name != run or item['plan'] != plan:
                raise ValueError('Canonical dispatch identity differs')
            terminal = store.get(prefix+'terminal/'+run)
            if terminal is not None and terminal.get('status') not in ('completed', 'failed'):
                raise ValueError('Unknown terminal status, reconcile before dispatch')
            if terminal is None:
                occupied.append(dict(run_id=expected_campaign+'/'+run,
                                     provider_app_id=item['provider_app_id']))
    return occupied
