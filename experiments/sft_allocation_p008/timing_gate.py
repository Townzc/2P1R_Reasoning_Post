"""Prepared outcome-blind timing proposal, not a run admission or forecast proof.

Inputs contain timings, counts, identities and original caps only. No scores or
answer correctness are accepted. Actual provenance and external acceptance are
required separately before any T8 dispatch. No data exists at preparation time.
"""
import math

POLICY = dict(schema='p008_t1_first_timing_gate_v1', margin=1.2,
              soft_margin_seconds=30, mtime_resolution_allowance_seconds=2,
              calibration='all_already_planned_T1_and_base_no_extra_model_job',
              selection='componentwise_maximum_not_mean', outcomes_read=False)


def number(x, *, positive=False):
    if type(x) not in (int, float) or not math.isfinite(x) or x < 0 or (positive and x <= 0):
        raise ValueError('Invalid finite engineering measurement')
    return float(x)


def estimate(samples, base_wall_seconds, candidates, *, expected_t1, expected_t8):
    if not expected_t1 or not expected_t8 or set(samples) != set(expected_t1) or set(candidates) != set(expected_t8):
        raise ValueError('Complete predeclared timing roster required')
    base_wall_seconds = number(base_wall_seconds, positive=True)
    components = {}
    allowed = {'worker_seconds_through_terminal', 'completed_update_mtimes',
               'optimizer_seconds', 'processed_tokens', 'first_eval_intent_mtime',
               'block_boundary_seconds', 'local_step_write_seconds'}
    for run, sample in samples.items():
        if set(sample) != allowed:
            raise ValueError('Only explicit engineering fields allowed; no outcome fields')
        times = [number(x, positive=True) for x in sample['completed_update_mtimes']]
        costs = [number(x) for x in sample['optimizer_seconds']]
        tokens = sample['processed_tokens']
        if len(times) != 256 or len(costs) != 256 or len(tokens) != 256:
            raise ValueError('Exactly 256 ordered original updates required')
        if any(type(x) is not int or x <= 0 for x in tokens) or any(b < a for a,b in zip(times, times[1:])):
            raise ValueError('Invalid tokens or unordered update times')
        wall = number(sample['worker_seconds_through_terminal'], positive=True)
        span = times[-1]-times[0]
        if not 0 < span < wall:
            raise ValueError('Invalid original update span')
        # This span covers updates2..256, not update1. Retain the two-second
        # mtime quantization allowance on both the fixed and variable proxies.
        fixed = wall-span+2
        noncompute = (span-sum(costs[1:])+2)/255
        if noncompute < 0:
            raise ValueError('Timing alignment is inconsistent, do not clamp to pass')
        boundary = number(sample['block_boundary_seconds'])
        local = number(sample['local_step_write_seconds'])
        measured = (boundary+local)/256
        noncompute = max(noncompute, measured)
        # The gap includes checkpoint snapshot/serialization/readback/commit
        # and other setup. It is a checkpoint upper proxy, not pure ck.save.
        endgap = number(sample['first_eval_intent_mtime'], positive=True)-times[-1]+2
        if endgap < 2 or endgap > fixed:
            raise ValueError('Invalid checkpoint/setup gap')
        components[run] = dict(fixed_seconds=fixed,
            compute_seconds_per_processed_token=sum(costs)/sum(tokens),
            noncompute_seconds_per_update=noncompute,
            checkpoint_and_setup_gap_proxy_seconds=endgap,
            measured_journal_seconds_per_update=measured)
    F = max(base_wall_seconds, *(x['fixed_seconds'] for x in components.values()))
    c = max(x['compute_seconds_per_processed_token'] for x in components.values())
    m = max(x['noncompute_seconds_per_update'] for x in components.values())
    K = 2*max(x['checkpoint_and_setup_gap_proxy_seconds'] for x in components.values())
    predictions = {}
    for run, cfg in candidates.items():
        if set(cfg) != {'processed_tokens', 'updates', 'max_seconds'} or cfg['updates'] != 2048 or cfg['max_seconds'] != 9560:
            raise ValueError('Frozen T8 horizon/cap required')
        P = cfg['processed_tokens']
        if type(P) is not int or P <= 0:
            raise ValueError('Positive exact joint-plan processed-token total required')
        point = F+P*c+2048*m+K
        predictions[run] = dict(point_seconds=point, with_margin_seconds=1.2*point,
            allowed_seconds=cfg['max_seconds']-30,
            engineering_criterion_passed=1.2*point <= cfg['max_seconds']-30)
    return dict(policy=POLICY, components=components,
        maxima=dict(F=F,c=c,m=m,K=K), predictions=predictions,
        engineering_criterion_passed=all(x['engineering_criterion_passed'] for x in predictions.values()),
        N2_closed=False, runtime_admission=False, external_numeric_review='required',
        limitations=['Historical T1 host timings are not bounds on future host latency.',
          'Processed-token scaling is a compute proxy; length/attention profiles may differ.',
          'Checkpoint/setup gap is deliberately double-counted via F and K; not isolated checkpoint time.',
          'Failed/missing T1 evidence cannot be replaced with a favorable subset.'])
