"""CPU reference for a proposed task-boundary completion contract.

This is not a GPU stopping implementation and never alters historical records.
Boundaries come from the frozen marked-answer parser; gold never controls stops.
"""
from analyses.gsm8k_answer_audit import BOUNDARY, score


VERSION = 'task_boundary_proposal_v1'


def first_stop(ids, decode, eos_id, max_new_tokens, other_special_ids=()):
    """Return the first complete boundary/EOS, or a genuine length/incomplete stop.

    decode receives only generated tokens, with no prompt or batch padding.
    Boundary trigger tokens are retained in the recorded prefix, not relabeled
    as EOS. The rendered answer segment excludes the next-question header.
    """
    if not ids or len(ids) > max_new_tokens:
        raise ValueError('Nonempty generation within the declared cap required')
    special = set(other_special_ids) - {eos_id}
    terminal = next(((i, 'native_eos' if token == eos_id else 'invalid_special_token')
                     for i, token in enumerate(ids) if token == eos_id or token in special), None)
    stop_index, reason = terminal if terminal else (len(ids), 'length_cap')
    visible_ids = ids[:stop_index]
    whole = decode(visible_ids)
    if BOUNDARY.search(whole):
        # A complete decoded prefix is the correctness oracle. Do not assume
        # a delimiter is one token, or search for a boundary in the prompt.
        for count in range(1, len(visible_ids) + 1):
            text = decode(visible_ids[:count])
            boundary = BOUNDARY.search(text)
            if boundary:
                return {'stop_reason': 'new_problem_boundary', 'retained_tokens': count,
                        'actual_eos_at_stop': False, 'answer_segment': text[:boundary.start()],
                        'boundary_offset': boundary.start(), 'trigger_text': boundary.group()}
        raise AssertionError('Full boundary had no triggering token prefix')
    if terminal:
        return {'stop_reason': reason, 'retained_tokens': stop_index + 1,
                'actual_eos_at_stop': reason == 'native_eos', 'answer_segment': whole,
                'boundary_offset': None, 'trigger_text': None}
    if len(ids) != max_new_tokens:
        raise ValueError('Incomplete stream is not a completed or length-capped answer')
    return {'stop_reason': 'length_cap', 'retained_tokens': len(ids),
            'actual_eos_at_stop': False, 'answer_segment': whole,
            'boundary_offset': None, 'trigger_text': None}


def completion_score(row, event):
    marked = score(row, event['answer_segment'], event['actual_eos_at_stop'],
                   event['stop_reason'] == 'length_cap')
    completed = event['stop_reason'] in ('native_eos', 'new_problem_boundary')
    return {'version': VERSION, 'marked': marked, 'task_completed': completed,
            'task_answer_correct': bool(completed and marked['answer_correct']),
            'native_eos_correct': bool(event['actual_eos_at_stop'] and marked['answer_correct']),
            'reasoning_validated': False}
