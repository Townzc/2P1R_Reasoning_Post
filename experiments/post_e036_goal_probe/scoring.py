"""Strict, CPU-only scoring for the frozen F/H/C goal-switch diagnostic.

F retains the original construction score; H adds ordered-AST template
adherence; C retains exact computation-value scoring. No AC canonicalization
is used to decide whether H obeyed its template.
"""
from collections import Counter
from fractions import Fraction
from functools import lru_cache
import json

from experiments.thursday_probe.arithmetic_eval import score as original_score
from experiments.thursday_probe_v2.resume_diagnostics import construction_error_breakdown
from src.trace_audit import audit_trace, exact_value, parse_expression

OPERATORS = ('+', '-', '*', '/')


def _leaves(tree):
    return [tree[1]] if tree[0] == 'n' else _leaves(tree[1])+_leaves(tree[2])


def ordered_expression_key(expression):
    """Ignore spaces/outer parentheses, retaining operand order and association."""
    return json.dumps(parse_expression(expression, final=True), separators=(',', ':'))


@lru_cache(maxsize=256)
def _hole_candidates(template, numbers, target, correct_operator):
    if template.count('?') != 1 or correct_operator not in OPERATORS:
        raise ValueError('H requires one template hole and one registered correct operator')
    candidates, correct = {}, []
    for operator in OPERATORS:
        tree = parse_expression(template.replace('?', operator), final=True)
        if Counter(_leaves(tree)) != Counter(numbers):
            raise ValueError('H template differs from the registered number multiset')
        candidates[operator] = tree
        try:
            if exact_value(tree) == Fraction(target):
                correct.append(operator)
        except ZeroDivisionError:
            pass  # An undefined distractor is not a legal completion.
    if correct != [correct_operator]:
        raise ValueError('H target must have exactly its registered unique completion')
    return candidates


def score(row, stop, forced_prefix=''):
    """Drop-in ``score(row, stop, forced_prefix='')`` for the generation journal.

Rows use interface F/H/C; H also supplies template and correct_operator
(``expected_operator`` is accepted for independently constructed test rows).
Unknown resource/arithmetic evidence remains None/NA. Supplemental free_correct
still requires a completed answer and never replaces the strict H score.
"""
    interface = row['interface']
    if interface not in ('F', 'H', 'C'):
        raise ValueError('Unknown diagnostic interface')
    adapted = dict(row, task='compute' if interface == 'C' else 'construct')
    if interface == 'C':
        adapted['answer'] = row.get('answer', row['target'])
    else:
        adapted['target'] = Fraction(row['target'])
    result = original_score(adapted, stop, forced_prefix)
    result.update(interface=interface, free_correct=None, unconstrained_target_achieved=None,
                  scaffold_followed=None, selected_operator=None, operator_correct=None,
                  uses_input_multiset=None, reaches_target=None, exact_value=None,
                  ordered_expression=None, resource_target_category='not_applicable',
                  intermediate_arithmetic_status='NA')
    text = forced_prefix+stop['answer_segment']
    if interface == 'C':
        if result['parsed']:
            result['exact_value'] = str(exact_value(parse_expression(result['expression'])))
            result['reaches_target'] = result['answer_correct_ignoring_stop']
        trace = audit_trace(text, row['numbers'], Fraction(adapted['answer']))
        result['intermediate_arithmetic_status'] = {
            'consistent': 'consistent', 'inconsistent': 'inconsistent'
        }.get(trace['local_equations_status'], 'NA')
        return result

    breakdown = construction_error_breakdown(adapted, text, stop_reason=stop['stop_reason'])
    for key in ('uses_input_multiset', 'reaches_target', 'exact_value',
                'resource_target_category', 'intermediate_arithmetic_status'):
        result[key] = breakdown[key]
    result['free_correct'] = bool(result['correct'])
    result['unconstrained_target_achieved'] = bool(result['correct'])
    if result['parsed']:
        result['ordered_expression'] = ordered_expression_key(result['expression'])
    if interface == 'H':
        correct_operator = row.get('correct_operator', row.get('expected_operator'))
        candidates = _hole_candidates(row['template'], tuple(row['numbers']),
                                      str(row['target']), correct_operator)
        tree = parse_expression(result['expression'], final=True) if result['parsed'] else None
        matches = [operator for operator, candidate in candidates.items() if candidate == tree]
        result['scaffold_followed'] = len(matches) == 1
        result['selected_operator'] = matches[0] if matches else None
        result['operator_correct'] = bool(matches and matches[0] == correct_operator)
        result['correct'] = bool(result['free_correct'] and result['scaffold_followed']
                                 and result['operator_correct'])
        result['answer_correct_ignoring_stop'] = bool(
            result['answer_correct_ignoring_stop'] and result['scaffold_followed']
            and result['operator_correct'])
        result['unconstrained_correct_off_template'] = bool(
            result['free_correct'] and not result['scaffold_followed'])
        if result['completed'] and result['parsed'] and not result['scaffold_followed']:
            result['failure'] = 'template_violation'
        elif result['correct']:
            result['failure'] = 'none'
    return result
