"""Proposed narrow C6 grouping repair; primary task scoring is unchanged."""
import math
from experiments.p010.cue_answer_key import extracted_tail


def answer_key(text, parse):
    answer = extracted_tail(text)
    if answer is None:
        return None
    parsed = parse('\\boxed{'+answer+'}')
    if not parsed:
        return None
    value, normalized = (list(parsed)+[None, None])[:2]
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 'text:'+str(normalized if normalized is not None else value)
    if math.isinf(number):
        # Infinity is an extracted symbolic answer, not a transport/parser
        # failure or missing answer. Its sign is retained, never mapped to0.
        return 'symbolic:+infinity' if number > 0 else 'symbolic:-infinity'
    if not math.isfinite(number):
        raise ValueError('NaN parser output is not a valid entropy key')
    number = round(number, 6)
    if number == 0:
        number = 0.0
    return 'number:'+repr(number)
