"""Candidate for only the unattempted high-throughput P0 suffix, never a retry."""
import math
from pathlib import Path
from experiments.sft_allocation_midpoint.common import read, sha, digest, verify
from experiments.learning_regime_p009.p0_contract import cost_cents, prompts_checked
from experiments.learning_regime_p009.p0_stop_metadata import raw_checked
from experiments.learning_regime_p009.high_throughput_v1 import engine_kwargs, validate_observed_engine
from experiments.learning_regime_p009.p0_fast_contract import validate_release as validate_parent_release

CAMPAIGN = 'p009-p0-fast-remaining-20261014-r1'
RUN = 'p0_fast_remaining'
PARENT_CAMPAIGN = 'p009-p0-fast-20261014-r1'
PARENT_RUN = 'p0_fast_pair'
ANCESTOR_CAMPAIGN = 'p009-p0-parity-20261014-r1'
ANCESTOR_RUN = 'p0_parity_pair'
RETIRED_CAMPAIGN = 'p009-p0-suffix-20261014-r1'
SCOPE = 'p009-p0-fast-unattempted-remainder-runtime-and-numeric'
WORKER_SECONDS = 1200
PLATFORM_SECONDS = 1260
STARTUP_SECONDS = 600
FULL_WINDOW = 1900
RESERVED_CENTS = 252
PARENT_RESERVED_CENTS = 500
OFFSETS = {'base_638': 256, 'correct_969': 0}
ROLES = tuple(OFFSETS)
BATCH_SIZE = 256


def remaining_forecast(elapsed, observations, remaining_batches):
    if (not math.isfinite(elapsed) or elapsed < 0 or not observations
            or any(not math.isfinite(x) or x <= 0 for x in observations)
            or type(remaining_batches) is not int or not 0 <= remaining_batches <= 11):
        raise ValueError('Finite parent proxy plus all new complete timings required')
    remaining = 1.2*(max(observations)*remaining_batches+300)
    total = elapsed+remaining
    cents = cost_cents(total+STARTUP_SECONDS+100)+20
    return dict(elapsed_worker_seconds=elapsed, observed_intervals=len(observations),
        parent_failed_batch_proxy_seconds=observations[0], max_interval_seconds=max(observations),
        future_batches=remaining_batches, remaining_seconds=remaining,
        predicted_worker_seconds=total, predicted_cents=cents,
        admitted=(total <= WORKER_SECONDS-30 and cents <= .8*(1000-PARENT_RESERVED_CENTS)
                  and RESERVED_CENTS+PARENT_RESERVED_CENTS <= 1000),
        parent_proxy_is_completed_batch=False, calibrated_bound=False,
        bootstrap_exception=False, old_eager_timings_used=False)


def validate_release(spec, plan, release):
    exact = dict(scope=SCOPE, campaign=CAMPAIGN, run_id=RUN, offsets=OFFSETS,
        worker_seconds=WORKER_SECONDS, platform_seconds=PLATFORM_SECONDS,
        startup_seconds=STARTUP_SECONDS, full_window_seconds=FULL_WINDOW,
        reserved_cents=RESERVED_CENTS, parent_reserved_cents=PARENT_RESERVED_CENTS,
        new_training_updates=0, suffix_outputs=2382, inherited_outputs=256,
        batch_size=BATCH_SIZE, suffix_batches=11, bootstrap_batches_total=0,
        engine_kwargs=engine_kwargs(), stage0_cap_cents=1000, experiment_cap_cents=10000,
        project_cap_cents=45000, protected_original_cents=5000)
    if any(spec.get(k) != v for k, v in exact.items()):
        raise ValueError('Exact suffix scope/dose/configuration/cap changed')
    if (digest(plan) != spec['plan_sha256'] or plan['campaign_id'] != CAMPAIGN
            or plan['slots'] != {RUN: dict(stage='p0_fast_remaining', reserved_cents=RESERVED_CENTS)}
            or plan['stage_caps_cents'] != {'p0_fast_remaining': RESERVED_CENTS}
            or plan['total_cap_cents'] != RESERVED_CENTS
            or release['source_files'] != spec['source_files']
            or digest(spec['parent_spec']) != spec['parent_spec_sha256']
            or spec['parent_terminal']['status'] != 'failed'
            or spec['parent_terminal']['claim_sha256'] != digest(spec['parent_claim'])):
        raise ValueError('Plan/source or original failed lineage changed')
    review = release['runtime_review']
    if (review['scope'] != SCOPE or review['decision'] not in ('PASS', 'PASS-WITH-NOTES')
            or review['target_commit'] != release['review_target']
            or len(review['report_commit']) != 40 or len(review['report_sha256']) != 64
            or review['source_files'] != spec['source_files'] or review['spec_sha256'] != digest(spec)
            or review['parent_preservation_sha256'] != spec['parent_preservation_sha256']
            or review['bounded_suffix_only'] is not True
            or review['native_eos_cap_metadata_accepted'] is not True
            or review['same_frozen_logical_stop'] is not True):
        raise ValueError('Real exact suffix/source/prefix/numeric/EOS review required')
    budget = release['budget']
    if (budget['p009_stage0_used_and_pending_cents'] != PARENT_RESERVED_CENTS
            or budget['slot_reserved_cents'] != RESERVED_CENTS
            or budget['new_experiment_cap_cents'] != 10000
            or type(budget['project_prior_upper_cents']) is not int
            or budget['project_prior_upper_cents'] < 0
            or budget['project_prior_upper_cents']+10000 > 45000
            or release['input_readback'] != spec['parent_spec']['inputs']):
        raise ValueError('Failed reserves, Stage0/project cap or existing input readback changed')


def check_parent(spec, evidence, ledger, inputs):
    """Exact structural reconciliation of every attempted row; no answer scoring."""
    root = Path(evidence)
    verify(root, spec['parent_files'])
    if (sha(root/'failure_manifest.json') != spec['parent_failure_manifest_file_sha256']
            or digest(read(root/'failure_manifest.json')) != spec['parent_terminal']['evidence_sha256']
            or digest(ledger) != spec['parent_ledger_digest']):
        raise ValueError('Original files, failure manifest or complete ledger differ')
    prefix = 'midpoint/'+PARENT_CAMPAIGN+'/'
    ancestor = 'midpoint/'+ANCESTOR_CAMPAIGN+'/'
    original = spec['parent_spec']
    if (ledger[prefix+'claim/'+PARENT_RUN] != spec['parent_claim']
            or ledger[prefix+'terminal/'+PARENT_RUN] != spec['parent_terminal']
            or ledger[ancestor+'claim/'+ANCESTOR_RUN] != original['parent_claim']
            or ledger[ancestor+'terminal/'+ANCESTOR_RUN] != original['parent_terminal']
            or ledger[ancestor+'continuation/'+ANCESTOR_RUN] != read(root/'FRESH_CONFIGURATION_MARKER.json')):
        raise ValueError('Both failed ancestors and original successor marker must remain')
    if ({k.removeprefix(prefix+PARENT_RUN+'/unit/') for k in ledger
            if k.startswith(prefix+PARENT_RUN+'/unit/')} != {'base_638_0000'}
            or any(k.startswith(prefix+PARENT_RUN+'/done/') for k in ledger)
            or {p.relative_to(root).as_posix() for p in root.glob('*/raw/*.json')}
                != {'base_638/raw/0000.json'}):
        raise ValueError('Unknown/extra attempted output; never regenerate it')
    prompts = prompts_checked(read(Path(inputs)/'qwen_gsm_zero_parity.json'))[:256]
    raw = raw_checked(prompts, read(root/'base_638/raw/0000.json'))
    unit = ledger[prefix+PARENT_RUN+'/unit/base_638_0000']
    if (len(raw) != 256 or unit != read(root/'intents/base_638_0000.json')
            or unit['problem_ids'] != [r['problem_id'] for r in prompts]
            or unit['prompt_sha256'] != digest(prompts)
            or sha(root/'base_638/raw/0000.json') != spec['parent_raw_sha256']):
        raise ValueError('Every original unacknowledged row must be saved and bound')
    intent = read(root/'intent.json')
    validate_parent_release(original, intent['plan'], intent['release'])
    if intent['spec'] != original:
        raise ValueError('Original real reviewed execution differs')
    environment = read(root/'base_638/environment.json')
    if environment['requested_engine'] != engine_kwargs():
        raise ValueError('Inherited raw used a different engine setting')
    validate_observed_engine(environment['actual_engine'])
    interval = spec['parent_terminal']['finished_epoch']-unit['started_epoch']
    if interval <= 0 or abs(interval-spec['parent_failed_batch_proxy_seconds']) > 1e-9:
        raise ValueError('All failed-batch interval, including failure closeout, must be retained')
    return dict(parent_status='failed', inherited_outputs=256, acknowledged_parent_outputs=0,
        saved_unacknowledged_outputs=256, unknown_attempts=0, offsets=OFFSETS,
        raw_sha256=spec['parent_raw_sha256'], scored_outputs=0, original_bytes_unchanged=True,
        parent_failed_batch_proxy_seconds=interval, proxy_is_completed_batch=False,
        frozen_completion_source_sha256=spec['source_files']['analyses/completion_contract.py'])


def fence_parent(store, spec, claim):
    key = 'midpoint/'+PARENT_CAMPAIGN+'/continuation/'+PARENT_RUN
    marker = dict(child_campaign=CAMPAIGN, child_run=RUN, child_claim_sha256=claim.claim_sha256,
        spec_sha256=digest(spec), parent_terminal=spec['parent_terminal'],
        inherited_outputs=256, suffix_outputs=2382, parent_stays_failed=True)
    if not store.put(key, marker, skip_if_exists=True):
        raise ValueError('Existing/ambiguous successor marker permanently blocks replay')
    return marker
