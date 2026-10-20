"""Gold-blind marked-answer extraction; never replaces historical E013 scores.

This conservative diagnostic is not the lm-evaluation-harness GSM8K scorer.
Only explicit boxes, hash markers, and line-anchored answer statements count.
Unmarked numbers in reasoning are never searched for the reference answer.
"""
from collections import Counter
from fractions import Fraction
import re

from src.real_math_audit import scalar


VERSION = "marked_answer_v1"
BOUNDARY = re.compile(r"(?im)^[ \t]*(?:\[(?:Problem|Question)\]|(?:Problem|Question|Q)[ \t]*:)")
MARKER = re.compile(r"\\(?:boxed|fbox)\s*\{|####")
ANSWER = re.compile(r"(?im)^[ \t]*(?:(?:the|so the)\s+answer\s+is\s*:?|answer\s*:)[ \t]*(.*)$")
NUMBER = re.compile(r"(?<![\w.,])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:/[-+]?\d+)?(?![\w.,])")


def canonical(value):
    number = scalar(value)
    return str(Fraction(number)) if number is not None else None


def prose_scalar(payload):
    # A sentence-ending period is presentation; internal decimal dots remain.
    payload = payload.strip().rstrip(".! ")
    matches = list(NUMBER.finditer(payload))
    if len(matches) != 1:
        return None
    m = matches[0]
    rest = payload[:m.start()] + payload[m.end():]
    # No equations, ranges, alternatives, scientific notation or malformed
    # adjacent numerals. Units and surrounding natural-language prose are OK.
    if re.search(r"[\d=<>+*/^~]|\b(?:or|approximately|about)\b", rest, re.I):
        return None
    if re.search(r"[-.,]", rest):
        return None
    return canonical(m[0])


def extract(text):
    """Does not accept a gold label. All marked claims must resolve and agree."""
    boundary = BOUNDARY.search(text)
    segment = text[:boundary.start()] if boundary else text
    claims = []
    covered = []
    for m in MARKER.finditer(segment):
        if m[0] == "####":
            payload = segment[m.end():].split("\n", 1)[0].strip()
            end = m.end() + len(segment[m.end():].split("\n", 1)[0])
        else:
            depth, end = 1, m.end()
            while end < len(segment) and depth:
                depth += (segment[end] == "{") - (segment[end] == "}")
                end += 1
            payload = segment[m.end():end-1] if depth == 0 else None
        covered.append((m.start(), end))
        # Preserve the historical defense against joining two numbers.
        value = canonical(payload) if payload is not None and not re.search(r"\d\s+\d", payload) else None
        claims.append({"offset": m.start(), "kind": "hash" if m[0] == "####" else "box",
                       "payload": payload, "value": value})
    for m in ANSWER.finditer(segment):
        # "The answer is \\boxed{...}" is the same explicit claim, not prose.
        if any(m.start() <= start < m.end() or start <= m.start() < end for start, end in covered):
            continue
        claims.append({"offset": m.start(), "kind": "answer_statement",
                       "payload": m[1], "value": prose_scalar(m[1])})
    claims.sort(key=lambda c: c["offset"])
    values = {c["value"] for c in claims}
    if re.search(r"<\|[^<>]*\|>", text):
        status = "embedded_special_token"
    elif not claims:
        status = "missing_marked_answer"
    elif None in values:
        status = "unresolved_marked_answer"
    elif len(values) != 1:
        status = "conflicting_marked_answers"
    else:
        status = "parsed"
    return {"version": VERSION, "status": status,
            "value": next(iter(values)) if status == "parsed" else None,
            "claims": claims, "new_problem_boundary": boundary.start() if boundary else None,
            "segment_characters": len(segment)}


def score(row, text, eos, truncated):
    parsed = extract(text)
    gold = canonical(row["answer"])
    if gold is None:
        raise ValueError("Unresolved reference scalar")
    correct = parsed["status"] == "parsed" and parsed["value"] == gold
    return {**parsed, "answer_correct": correct,
            "correct_with_eos": bool(correct and eos and not truncated),
            "clean_correct": bool(correct and eos and not truncated and parsed["new_problem_boundary"] is None),
            "ended_with_eos": bool(eos), "truncated": bool(truncated),
            "reasoning_validated": False}


def summarize(scores):
    return {"n": len(scores), "parse_status": dict(Counter(s["status"] for s in scores)),
            **{k: sum(bool(s[k]) for s in scores) for k in
               ("answer_correct", "correct_with_eos", "clean_correct", "ended_with_eos", "truncated")},
            "new_problem_continuations": sum(s["new_problem_boundary"] is not None for s in scores)}
