"""Prospective endpoint-only repair of the two completed E4 training states.

No training, changed prompts, new arms or implicit retry authority.
"""
import math
from experiments.p010.common import budget_check

HARD_SECONDS = 1200
RESERVED_USD = '2.52'
RATE = .001097 + 4*.0000131 + 32*.00000222
ORIGINAL_BATCH_PROXY = 20.412141323


def endpoint_rows(wrapper):
    if (not isinstance(wrapper, dict) or wrapper.get('n') != 1319
            or wrapper.get('max_context') != 2048 or wrapper.get('max_new_tokens') != 512
            or wrapper.get('eos_token_id') != 100257):
        raise ValueError('Exact original OLMo GSM endpoint wrapper required')
    rows = wrapper.get('prompts')
    if (not isinstance(rows, list) or len(rows) != 1319
            or len({r['problem_id'] for r in rows}) != 1319
            or any(set(r) != {'problem_id', 'input_ids'} or not r['input_ids']
                   or len(r['input_ids'])+512 > 2048
                   or any(type(x) is not int or x < 0 for x in r['input_ids']) for r in rows)):
        raise ValueError('Original full prompt IDs, order and token bytes required')
    return rows


def sampling():
    return dict(n=1, temperature=0, top_p=1, top_k=-1, repetition_penalty=1,
        max_tokens=512, seed=17, stop=None, stop_token_ids=[100257], ignore_eos=False,
        detokenize=True, skip_special_tokens=False, include_stop_str_in_output=True)


def forecast(elapsed, completed_batches, seconds, prior):
    if (type(completed_batches) is not int or not 0 <= completed_batches < 6
            or len(seconds) != completed_batches or not math.isfinite(elapsed) or elapsed < 0
            or any(not math.isfinite(t) or t <= 0 for t in seconds)):
        raise ValueError('All completed original endpoint batch times required')
    maximum = max([ORIGINAL_BATCH_PROXY]+seconds)
    remaining = 1.2*(maximum*(6-completed_batches)+600)
    total = elapsed+remaining
    if total > HARD_SECONDS-30:
        raise TimeoutError('Original1200-second endpoint-only window does not fit')
    budget = budget_check('T', prior, RESERVED_USD, (total+700)*RATE)
    return dict(elapsed_seconds=elapsed, completed_batches=completed_batches,
        observed_batch_seconds=list(seconds), maximum_seconds=maximum,
        remaining_seconds=remaining, total_seconds=total, original_proxy_seconds=ORIGINAL_BATCH_PROXY,
        allowance_seconds=600, margin=1.2, calibrated_bound=False,
        no_new_paid_measurement_exception=True, budget=budget)


def validate_parent(proof, run, claim, terminal, intents, raw_files):
    if (run not in ('e4_s17_n400', 'e4_s17_n3200') or proof.get('passed') is not True
            or proof.get('run') != run or proof.get('updates_verified') != 1024
            or proof.get('targets_verified') != 2097148
            or proof.get('full_state_loaded_once') is not True
            or proof.get('no_endpoint_intent_or_raw') is not True
            or proof.get('original_run_stays_failed') is not True
            or proof.get('new_training') != 0 or proof.get('new_generations') != 0
            or proof.get('original_claim') != claim or proof.get('original_failed_terminal') != terminal
            or terminal.get('status') != 'failed' or raw_files
            or len(intents) != 12 or any(v is not None for v in intents)):
        raise ValueError('Original complete training and zero original endpoint work required')
    return True
