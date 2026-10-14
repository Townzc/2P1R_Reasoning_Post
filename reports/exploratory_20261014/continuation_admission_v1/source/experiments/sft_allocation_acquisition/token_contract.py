"""Fixed hypothetical tariff on saved policy traces; no new teacher execution.

Whole actions are reserved using known prompts and maximum completion length
before reading their outcomes. This estimates a specified tariff policy, not
actual cloud spending or an optimal allocation. Original collection costs remain.
"""
from fractions import Fraction
from .policy_contract import Policy

TARGETS = 524287
CAP = 211257
PILOT_MEAN = Fraction(191151, 512)  # 373.341796875 prompt+completion units
PRICES = {0: Fraction(0), 4: 4 * PILOT_MEAN}
MAX_NEW_TOKENS = 1024


def replay(ordered_ids, prompt_lengths, batches, target_usable, price_level):
    if price_level not in PRICES:
        raise ValueError('Unapproved price scenario')
    policy = Policy(ordered_ids, target_usable)
    price = PRICES[price_level]
    spent = Fraction(0); selected = []; settlements = []
    stop = 'tape_exhausted'
    for index, batch in enumerate(batches):
        proposal = policy.propose()
        if len(proposal['items']) != 16:
            stop = 'no_full16_action'; break
        reserve = (price * len(proposal['new_problem_ids']) +
                   sum(prompt_lengths[x['problem_id']] for x in proposal['items']) +
                   16 * MAX_NEW_TOKENS)
        if spent + reserve > CAP:
            stop = 'cannot_reserve_full16_action'; break
        if proposal['items'] != [dict(problem_id=x['problem_id'], attempt=x['attempt']) for x in batch]:
            raise ValueError('Saved trace is not a prefix of the admitted policy')
        for row in batch:
            if (type(row['usable']) is not bool or type(row['stop']['token_count']) is not int
                    or not 0 <= row['stop']['token_count'] <= MAX_NEW_TOKENS
                    or row['prompt_tokens'] != prompt_lengths[row['problem_id']]):
                raise ValueError('Unknown outcome, token count, or prompt mismatch')
        charge = (price * len(proposal['new_problem_ids']) +
                  sum(x['prompt_tokens'] + x['stop']['token_count'] for x in batch))
        if charge > reserve:
            raise ValueError('Actual charge exceeds reserved action')
        name = f'batch_{index:04d}'
        policy.begin(name, proposal); policy.complete(name, batch)
        spent += charge; selected.extend(batch)
        settlements.append(dict(batch=name, reserved_units=float(reserve), charged_units=float(charge),
            cumulative_units=float(spent), new_problem_ids=proposal['new_problem_ids']))
    ids = ordered_ids[:policy.cursor]
    return dict(acquired=len(ids), acquired_ids=ids,
        covered=len({x['problem_id'] for x in selected if x['usable']}),
        usable=sum(x['usable'] for x in selected), attempts=len(selected), batches=len(settlements),
        charge=float(spent), cap=CAP, unused=float((CAP-spent)/CAP), stop_reason=stop,
        accepted_candidates=[x['candidate_id'] for x in selected], settlements=settlements)
