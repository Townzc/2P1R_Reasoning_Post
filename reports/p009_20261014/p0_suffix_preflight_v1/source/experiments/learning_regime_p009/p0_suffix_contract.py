"""Candidate contract for only P0's never-attempted suffix; not admission itself."""
import math
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read, sha, digest, verify
from experiments.learning_regime_p009.p0_contract import cost_cents, prompts_checked, raw_checked

PARENT_CAMPAIGN = 'p009-p0-parity-20261014-r1'
PARENT_RUN = 'p0_parity_pair'
CAMPAIGN = 'p009-p0-suffix-20261014-r1'
RUN = 'p0_parity_remaining'
SCOPE = 'p009-p0-unattempted-suffix-runtime-and-numeric'
WORKER_SECONDS = 1800
PLATFORM_SECONDS = 1860
STARTUP_SECONDS = 600
FULL_WINDOW = 2500
RESERVED_CENTS = 326
PARENT_RESERVED_CENTS = 248
OFFSETS = {'base_638': 128, 'correct_969': 0}


def remaining_forecast(elapsed, observed, remaining_batches):
    if (not math.isfinite(elapsed) or elapsed < 0 or not observed or
            any(not math.isfinite(x) or x <= 0 for x in observed) or
            type(remaining_batches) is not int or not 0 <= remaining_batches <= 80):
        raise ValueError('All actual full-batch timing and finite remaining count required')
    remaining = 1.2*(max(observed)*remaining_batches+300)
    predicted = elapsed+remaining
    predicted_cents = cost_cents(predicted+STARTUP_SECONDS)+20
    return dict(full_batch_max_seconds=max(observed), future_batches=remaining_batches,
        remaining_seconds=remaining, predicted_worker_seconds=predicted,
        predicted_cents=predicted_cents, original_failed_gate_retained=True,
        calibrated_bound=False, admitted=(predicted <= WORKER_SECONDS-30 and
            predicted_cents <= .8*(1000-PARENT_RESERVED_CENTS) and
            RESERVED_CENTS <= 1000-PARENT_RESERVED_CENTS))


def validate_release(spec, plan, release):
    for key, value in dict(scope=SCOPE, campaign=CAMPAIGN, run_id=RUN,
            worker_seconds=WORKER_SECONDS, platform_seconds=PLATFORM_SECONDS,
            startup_seconds=STARTUP_SECONDS, full_window_seconds=FULL_WINDOW,
            reserved_cents=RESERVED_CENTS, parent_reserved_cents=PARENT_RESERVED_CENTS,
            offsets=OFFSETS, suffix_outputs=2510, reused_outputs=128,
            new_training_updates=0).items():
        if spec.get(key) != value:
            raise ValueError('Exact suffix specification differs: '+key)
    if (digest(plan) != spec['plan_sha256'] or plan['campaign_id'] != CAMPAIGN or
            plan['slots'] != {RUN: {'stage': 'p0_suffix', 'reserved_cents': RESERVED_CENTS}} or
            release['source_files'] != spec['source_files'] or
            spec['parent_terminal']['status'] != 'failed' or
            spec['parent_terminal']['claim_sha256'] != digest(spec['parent_claim']) or
            digest(spec['parent_spec']) != spec['parent_spec_sha256']):
        raise ValueError('Plan/source/original failed lineage differs')
    review = release['runtime_review']
    if (review['scope'] != SCOPE or review['decision'] not in ('PASS', 'PASS-WITH-NOTES') or
            review['target_commit'] != release['review_target'] or
            len(review['report_commit']) != 40 or len(review['report_sha256']) != 64 or
            review['spec_sha256'] != digest(spec) or review['source_files'] != spec['source_files'] or
            review['parent_preservation_sha256'] != spec['parent_preservation_sha256'] or
            review['bounded_suffix_only'] is not True):
        raise ValueError('Real exact suffix/runtime/numeric review required')
    budget = release['budget']
    if (budget['new_experiment_cap_cents'] != 10000 or
            budget['p009_stage0_used_and_pending_cents'] != PARENT_RESERVED_CENTS or
            budget['slot_reserved_cents'] != RESERVED_CENTS or
            budget['project_prior_upper_cents']+10000 > 45000):
        raise ValueError('Preserve original reserve and stage/project limits')
    if release['input_readback'] != spec['parent_spec']['inputs']:
        raise ValueError('Reuse exact original three input readbacks')


def check_parent(spec, evidence, parent_ledger, inputs):
    """Only structural/hash replay of the stopped prefix, never compute scores."""
    root = Path(evidence)
    verify(root, spec['parent_files'])
    if (sha(root/'failure_manifest.json') != spec['parent_failure_manifest_file_sha256'] or
            digest(read(root/'failure_manifest.json')) != spec['parent_terminal']['evidence_sha256'] or
            digest(parent_ledger) != spec['parent_ledger_digest']):
        raise ValueError('Original raw/failed manifest/ledger changed')
    pre = 'midpoint/'+PARENT_CAMPAIGN+'/'
    if (parent_ledger[pre+'claim/'+PARENT_RUN] != spec['parent_claim'] or
            parent_ledger[pre+'terminal/'+PARENT_RUN] != spec['parent_terminal']):
        raise ValueError('Failed parent must stay failed')
    p = prompts_checked(read(Path(inputs)/'qwen_gsm_zero_parity.json'))
    names = [f'base_638_{offset:04d}' for offset in range(0,128,32)]
    units = {k.removeprefix(pre+PARENT_RUN+'/unit/') for k in parent_ledger
             if k.startswith(pre+PARENT_RUN+'/unit/')}
    dones = {k.removeprefix(pre+PARENT_RUN+'/done/') for k in parent_ledger
             if k.startswith(pre+PARENT_RUN+'/done/')}
    if units != set(names) or dones != set(names):
        raise ValueError('Unknown/unacknowledged attempt cannot be regenerated')
    raw_names = {x.relative_to(root).as_posix() for x in root.glob('*/raw/*.json')}
    if raw_names != {f'base_638/raw/{i:04d}.json' for i in range(0,128,32)}:
        raise ValueError('Unexpected attempted/saved prefix')
    for offset, name in zip(range(0,128,32), names):
        path = root/'base_638/raw'/f'{offset:04d}.json'
        raw = raw_checked(p[offset:offset+32], read(path))
        unit = parent_ledger[pre+PARENT_RUN+'/unit/'+name]
        done = parent_ledger[pre+PARENT_RUN+'/done/'+name]
        if (unit != read(root/'intents'/f'{name}.json') or
                done != read(root/'completed'/f'{name}.json') or
                done['raw_sha256'] != sha(path) or done['count'] != len(raw) or
                unit['problem_ids'] != [x['problem_id'] for x in p[offset:offset+32]] or
                unit['prompt_sha256'] != digest(p[offset:offset+32])):
            raise ValueError('Original completed raw/ack provenance differs')
    f = read(root/'forecasts/004.json')
    if (f != spec['failed_forecast'] or f['admitted'] is not False or
            f['observed_batches'] != 4 or f['future_batches'] != 80):
        raise ValueError('Preserve the actual failed original timing gate')
    return dict(parent_failed=True, saved_outputs=128, unknown_attempts=0,
        original_full_batch_max_seconds=f['full_batch_max_seconds'], offsets=OFFSETS,
        parent_files_digest=digest(spec['parent_files']), scored_outputs=0)
