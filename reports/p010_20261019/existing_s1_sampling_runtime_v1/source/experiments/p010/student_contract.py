"""Only the frozen P010 1.5B student grid; repeated paths, not extra arms."""
import math
from experiments.p010.common import budget_check

CELLS = {}
for teacher in ('t7', 't72'):
    for p, k in ((400, 1), (3200, 1), (400, 4), (400, 8)):
        CELLS[f'{teacher}_s17_n{p}_k{k}'] = dict(teacher=teacher, seed=17, P=p, K=k, tier=1 if teacher == 't72' else 2)
for k in (4, 8):
    CELLS[f't15_s17_n400_k{k}'] = dict(teacher='t15', seed=17, P=400, K=k, tier=2)
CELLS['t72_s17_e1d_n3200_k1'] = dict(teacher='t72', seed=17, P=3200, K=1, tier=2, E1d=True)
for teacher in ('t15', 't72'):
    for p in (400, 3200):
        CELLS[f'{teacher}_s29_n{p}_k1'] = dict(teacher=teacher, seed=29, P=p, K=1, tier=3)

HARD_SECONDS = 4500
RESERVE_USD = '6.55'
RATE = .001097 + 4 * .0000131 + 32 * .00000222


def evaluation_jobs():
    return [('greedy', 17, 0., 1.)] + [('sample'+str(seed), seed, .6, .95) for seed in range(4)]


def sampling(job):
    label, seed, temperature, top_p = job
    if job not in evaluation_jobs():
        raise ValueError('Only original greedy and four sampled endpoints')
    return dict(n=1, temperature=temperature, top_p=top_p, top_k=-1,
        repetition_penalty=1, max_tokens=1024, seed=seed, stop=None,
        stop_token_ids=[151643], ignore_eos=False, detokenize=True,
        skip_special_tokens=False, include_stop_str_in_output=True)


def forecast(elapsed, train_left, eval_left, train_seconds, eval_seconds, prior_reserved):
    if (type(train_left) is not int or not 0 <= train_left <= 64
            or type(eval_left) is not int or not 0 <= eval_left <= 10
            or not math.isfinite(elapsed) or elapsed < 0
            or not train_seconds or not eval_seconds
            or any(not math.isfinite(x) or x <= 0 for x in train_seconds+eval_seconds)):
        raise ValueError('Invalid complete-batch observation or remainder')
    future = 1.2 * (max(train_seconds)*train_left + max(eval_seconds)*eval_left + 600)
    total = elapsed + future
    if total > HARD_SECONDS-30:
        raise TimeoutError('Observed full train/evaluation remainder exceeds original 4500s')
    # Startup is paid too; this is a scenario, never a host guarantee.
    budget = budget_check('T', prior_reserved, RESERVE_USD, (total+700)*RATE)
    return dict(elapsed_seconds=elapsed, train_blocks_left=train_left,
        eval_batches_left=eval_left, train_max=max(train_seconds), eval_max=max(eval_seconds),
        training_observations=len(train_seconds), endpoint_observations=len(eval_seconds),
        remaining_seconds=future, allowance_seconds=600, margin=1.2,
        forecast_total_seconds=total, calibrated_bound=False,
        greedy_to_sampling_transfer_not_guaranteed=True, budget=budget)
