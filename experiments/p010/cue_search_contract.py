"""Original C6 development search only; no benchmark, labels or training."""
import math
from experiments.p010.common import budget_check, digest
from experiments.p010.cue_probability import validate_rows

HARD_SECONDS = 1800
RESERVE_USD = '3.26'
RATE = .001097 + 4*.0000131 + 32*.00000222
RESPONSES = 21*30*16
BATCHES = (RESPONSES+255)//256


def sampling(seed):
    if type(seed) is not int or not 0 <= seed < 16:
        raise ValueError('Only the sixteen fixed development rollout seeds')
    return dict(n=1, temperature=.6, top_p=.95, top_k=-1,
        repetition_penalty=1, max_tokens=1024, seed=seed, stop=None,
        stop_token_ids=[151643], ignore_eos=False, detokenize=True,
        skip_special_tokens=False, include_stop_str_in_output=True)


def screen_rows(dev, proposal, allowed_tokens):
    validate_rows(dev, 151936)
    if (proposal.get('problem_ids') != [r['problem_id'] for r in dev]
            or proposal.get('beam_width') != 20 or proposal.get('maximum_depth') != 2
            or proposal.get('gold_used') is not False
            or proposal.get('correctness_used') is not False):
        raise ValueError('Exact original label-free proposal required')
    candidates = [()] + [tuple(x['token_ids']) for x in proposal['candidates']]
    allowed = set(allowed_tokens)
    if (len(candidates) != 21 or len(set(candidates)) != 21
            or any(not 1 <= len(c) <= 2 for c in candidates[1:])
            or any(type(t) is not int or t not in allowed for c in candidates for t in c)):
        raise ValueError('Twenty distinct supported openings plus no cue')
    rows = []
    for candidate, cue in enumerate(candidates):
        for rollout in range(16):
            for position, original in enumerate(dev):
                ids = original['input_ids'] + list(cue)
                if len(ids)+1024 > 2048:
                    raise ValueError('No truncation of full development prompts or cues')
                rows.append(dict(candidate_id=f'cue{candidate:02d}/sample{rollout:02d}/dev{position:02d}',
                    problem_id=original['problem_id'], source_row_sha256=digest(original),
                    input_ids=ids, candidate=candidate, rollout=rollout, cue_token_ids=list(cue)))
    if len(rows) != RESPONSES or len({r['candidate_id'] for r in rows}) != RESPONSES:
        raise ValueError('Full original search roster must be unique')
    return rows


def forecast(elapsed, completed_batches, times, observed_seconds, prior, *, proposal_complete):
    if (type(completed_batches) is not int or not 0 <= completed_batches < BATCHES
            or len(times) != completed_batches or type(proposal_complete) is not bool
            or not math.isfinite(elapsed) or elapsed < 0 or not observed_seconds
            or any(not math.isfinite(t) or t <= 0 for t in list(observed_seconds)+list(times))):
        raise ValueError('Every original completed batch time and elapsed duration required')
    maximum = max(list(observed_seconds)+list(times))
    proposal_allowance = 0 if proposal_complete else 300
    remaining = 1.2*(maximum*(BATCHES-completed_batches)+600+proposal_allowance)
    total = elapsed+remaining
    if total > HARD_SECONDS-30:
        raise TimeoutError('Original C6 search window cannot contain the remainder')
    budget = budget_check('I', prior, RESERVE_USD, (total+700)*RATE)
    return dict(elapsed_seconds=elapsed, completed_batches=completed_batches,
        full_batches=BATCHES, original_observed_seconds=list(observed_seconds),
        actual_completed_seconds=list(times), maximum_seconds=maximum,
        proposal_complete=proposal_complete, proposal_allowance_seconds=proposal_allowance,
        other_allowance_seconds=600, margin=1.2, remaining_seconds=remaining,
        total_seconds=total, calibrated_bound=False, first_paid_measurement_exceptions=0,
        budget=budget)
