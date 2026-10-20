"""Unattempted, gold-free C6 answer-key adapter from the cited paper's decider.

The paper uses the last2000 completion characters and first80 extracted-answer
characters, then rounds numeric keys to6decimals. These are entropy grouping
rules, not semantic-equivalence or primary-scoring claims. Primary scoring is
unchanged. The future local process must impose the frozen outer timeout and
retain failures/unknowns; it may not silently turn a tool exception into NONE.
"""
import math
import re


def extracted_tail(text):
    if not isinstance(text, str):
        raise ValueError('Original decoded completion text required')
    tail = text[-2000:]
    start = tail.rfind('\\boxed{')
    while start >= 0:
        i = start+len('\\boxed{')
        depth = 1
        while i < len(tail) and depth:
            if tail[i] == '{':
                depth += 1
            elif tail[i] == '}':
                depth -= 1
                if depth == 0:
                    return tail[start+len('\\boxed{'):i][:80]
            i += 1
        start = tail.rfind('\\boxed{', 0, start)
    final = re.findall(r'[Ff]inal answer:?\s*(.+)', tail)
    return final[-1].strip()[:80] if final else None


def answer_key(text, parse):
    """parse is the pinned math-verify parser supplied by a bounded subprocess.

    No gold/score argument is accepted. Missing extraction or an empty parser
    result returns None; raised errors propagate as technical failures. Tagged
    keys keep textual '0.5' separate from numeric0.5 when the parser did not
    actually produce a numeric value. Numeric0 and negative0 coalesce.
    """
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
    if not math.isfinite(number):
        raise ValueError('Nonfinite parser numeric output is not a valid entropy key')
    number = round(number, 6)
    if number == 0:
        number = 0.0
    return 'number:'+repr(number)
