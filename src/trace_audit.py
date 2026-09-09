"""Conservative post-hoc audit of arithmetic traces; never an official metric.

The full derivation grammar is the four frozen pilot frames, one binary
operation on displayed integer/rational values per line, then one Answer.
Locally true equations alone do not establish legal input use or a connected
solution. Parsing uses a bounded AST whitelist and exact Fraction arithmetic.
"""
from __future__ import annotations

import ast
from collections import Counter
from fractions import Fraction
import re

_OPERATORS = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/'}
_FRAMES = (
    re.compile(r'Step (\d+): (.+)\.'),
    re.compile(r'We now calculate: (.+)\.'),
    re.compile(r'Next, we obtain (.+)\.'),
    re.compile(r'This calculation gives us (.+)\.'),
)


def parse_expression(text, *, final=False):
    """Return a bounded whitelist tree. Unary signs are local-trace syntax only."""
    if len(text) > 2048:
        raise ValueError('expression_too_long')
    root = ast.parse(text.strip(), mode='eval')
    if sum(1 for _ in ast.walk(root)) > 256:
        raise ValueError('too_many_ast_nodes')

    def visit(node, depth=0):
        if depth > 32:
            raise ValueError('expression_too_deep')
        if isinstance(node, ast.Constant) and type(node.value) is int:
            if not 0 <= node.value <= (10000 if final else 10**9):
                raise ValueError('literal_out_of_bounds')
            return ('n', node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
            return (_OPERATORS[type(node.op)], visit(node.left, depth+1), visit(node.right, depth+1))
        if not final and isinstance(node, ast.UnaryOp) and type(node.op) in (ast.UAdd, ast.USub):
            return ('u+' if isinstance(node.op, ast.UAdd) else 'u-', visit(node.operand, depth+1))
        raise ValueError('unsupported_ast')
    return visit(root.body)


def exact_value(tree):
    op = tree[0]
    if op == 'n':
        return Fraction(tree[1])
    if op in ('u+', 'u-'):
        value = exact_value(tree[1]) * (1 if op == 'u+' else -1)
    else:
        a, b = exact_value(tree[1]), exact_value(tree[2])
        if op == '+': value = a+b
        elif op == '-': value = a-b
        elif op == '*': value = a*b
        elif op == '/': value = a/b
        else: raise ValueError('unsupported_operator')
    if max(value.numerator.bit_length(), value.denominator.bit_length()) > 4096:
        raise ValueError('rational_too_large')
    return value


def _is_integer_scalar(tree):
    return tree[0] == 'n' or (tree[0] in ('u+', 'u-') and tree[1][0] == 'n')


def _is_scalar(tree):
    return (_is_integer_scalar(tree) or
            (tree[0] == '/' and _is_integer_scalar(tree[1]) and _is_integer_scalar(tree[2])))


def _leaves(tree):
    return [tree[1]] if tree[0] == 'n' else _leaves(tree[1]) + _leaves(tree[2])


def _ac(tree):
    """Numeric-leaf AC proxy; this does not assert general algebraic equivalence."""
    op = tree[0]
    if op == 'n': return str(tree[1])
    if op in ('+', '*'):
        def flatten(node):
            return flatten(node[1])+flatten(node[2]) if node[0] == op else [_ac(node)]
        return op+'('+','.join(sorted(flatten(tree)))+')'
    return op+'('+_ac(tree[1])+','+_ac(tree[2])+')'


def _answer(text, numbers, target):
    matches = list(re.finditer(r'(?m)^\s*Answer:\s*([^\n]+)', text))
    result = {'parsed': False, 'correct': False, 'expression': None,
              'uses_input_multiset': None, 'reaches_target': None, 'value': None}
    if len(matches) != 1:
        result['reason'] = 'answer_count_not_one'
        return result, None
    candidate = matches[0][1].strip()
    try:
        tree = parse_expression(candidate, final=True)
    except (ValueError, SyntaxError, RecursionError):
        result['reason'] = 'unsupported_answer_expression'
        return result, None
    result.update(parsed=True, expression=candidate,
                  uses_input_multiset=Counter(_leaves(tree)) == Counter(numbers))
    try:
        value = exact_value(tree)
        result.update(value=str(value), reaches_target=value == target)
    except ZeroDivisionError:
        result.update(reaches_target=False, reason='answer_division_by_zero')
    except (ValueError, RecursionError):
        result['reason'] = 'answer_value_unverifiable'
    result['correct'] = result['uses_input_multiset'] and result['reaches_target'] is True
    return result, tree


def _resource_derivations(operations, numbers):
    """Enumerate equal-value provenance alternatives rather than guess a binding."""
    # A token contains its exact value, ordered expression tree and input-ID mask.
    initial = tuple((Fraction(n), ('n', n), 1 << i) for i, n in enumerate(numbers))
    states = {initial}
    for index, (op, a, b, value) in enumerate(operations, 1):
        following = set()
        for pool in states:
            for i, left in enumerate(pool):
                if left[0] != a: continue
                for j, right in enumerate(pool):
                    if i == j or right[0] != b: continue
                    token = (value, (op, left[1], right[1]), left[2] | right[2])
                    rest = [x for k, x in enumerate(pool) if k not in (i, j)] + [token]
                    following.add(tuple(sorted(rest, key=repr)))
        if not following:
            return 'inconsistent', [], f'unavailable_or_reused_operand_at_step_{index}'
        if len(following) > 4096:
            return 'unverifiable', [], 'provenance_state_limit'
        states = following
    mask = (1 << len(numbers))-1
    roots = [pool[0] for pool in states if len(pool) == 1 and pool[0][2] == mask]
    if not roots:
        return 'inconsistent', [], 'inputs_not_reduced_to_one_result'
    return 'verified', roots, None


def audit_trace(text, numbers, target):
    """Separate final answer, local equations, resource validity, and connection.

    Unknown grammar never receives verified status. An observed contradiction
    remains inconsistent even if some other lines cannot be parsed. A same-value
    exact-tree mismatch is unverifiable: another equivalent expression can still
    represent a valid answer. Different derivation/answer values are inconsistent.
    """
    if not numbers or len(numbers) > 8 or any(type(n) is not int for n in numbers):
        raise ValueError('Expected 1..8 integer inputs')
    final, answer_tree = _answer(text, numbers, target)
    result = {'final_expression': final, 'equations': [], 'unknown_lines': [],
              'local_equations_status': 'unverifiable',
              'resource_derivation_status': 'unverifiable',
              'answer_connection_status': 'unavailable',
              'complete_trace_status': 'unverifiable', 'reasons': []}
    # A definite final-answer contradiction does not depend on whether the
    # preceding trace can be parsed or linked. Preserve it even for unknown
    # grammar and size-limited traces; unknown evidence cannot erase it.
    if final['uses_input_multiset'] is False or final['reaches_target'] is False:
        result['complete_trace_status'] = 'inconsistent'
        result['reasons'].append('final_answer_violates_inputs_or_target')
    if len(text) > 32768 or len(text.splitlines()) > 64:
        result['reasons'].append('trace_size_limit')
        return result
    operations, wrong, unknown, grammar_issue = [], False, False, False
    seen_answer, answer_lines = False, 0
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line: continue
        if line.startswith('Answer:'):
            seen_answer = True
            answer_lines += 1
            continue
        frame_match, numbered = None, False
        for frame_index, frame in enumerate(_FRAMES):
            match = frame.fullmatch(line)
            if match:
                frame_match, numbered = match, frame_index == 0
                break
        if frame_match is None:
            result['unknown_lines'].append({'line': line_number, 'text': raw, 'reason': 'unsupported_frame'})
            unknown = True
            continue
        equation = frame_match[2 if numbered else 1]
        entry = {'line': line_number, 'text': raw, 'status': 'unverifiable'}
        result['equations'].append(entry)
        if seen_answer:
            grammar_issue = True
            result['reasons'].append('calculation_after_answer')
        if numbered and frame_match[1] != str(len(result['equations'])):
            grammar_issue = True
            result['reasons'].append('nonsequential_step_labels')
        if equation.count('=') != 1:
            entry['reason'] = 'equation_must_have_one_equality'
            unknown = True
            continue
        lhs, rhs = (part.strip() for part in equation.split('='))
        try:
            left, right = parse_expression(lhs), parse_expression(rhs)
            left_value, right_value = exact_value(left), exact_value(right)
            entry.update(lhs_value=str(left_value), rhs_value=str(right_value),
                         status='consistent' if left_value == right_value else 'inconsistent')
            if left_value != right_value:
                wrong = True
                entry['reason'] = 'false_equality'
            if left[0] in '+-*/' and _is_scalar(left[1]) and _is_scalar(left[2]) and _is_scalar(right):
                operations.append((left[0], exact_value(left[1]), exact_value(left[2]), right_value))
                entry['resource_step_supported'] = True
            else:
                entry['resource_step_supported'] = False
                grammar_issue = True
                result['reasons'].append('equation_outside_single_operation_scalar_grammar')
        except ZeroDivisionError:
            entry.update(status='inconsistent', reason='division_by_zero')
            wrong = True
        except (ValueError, SyntaxError, RecursionError):
            entry['reason'] = 'unsupported_arithmetic_syntax_or_bound'
            unknown = True
    if answer_lines != 1:
        grammar_issue = True
        result['reasons'].append('answer_line_count_not_one')
    if wrong:
        result['local_equations_status'] = 'inconsistent'
        result['resource_derivation_status'] = 'inconsistent'
        result['complete_trace_status'] = 'inconsistent'
        result['reasons'].append('false_or_undefined_local_equation')
    elif result['equations'] and not unknown:
        result['local_equations_status'] = 'consistent'
    if not wrong and not unknown and not grammar_issue and result['equations']:
        status, roots, reason = _resource_derivations(operations, numbers)
        result['resource_derivation_status'] = status
        if reason: result['reasons'].append(reason)
        if status == 'inconsistent': result['complete_trace_status'] = 'inconsistent'
        if status == 'verified':
            result['derivation_values'] = sorted({str(root[0]) for root in roots})
            if not any(root[0] == target for root in roots):
                result['complete_trace_status'] = 'inconsistent'
                result['reasons'].append('derivation_does_not_reach_target')
            if answer_tree is not None:
                if any(root[1] == answer_tree for root in roots):
                    result['answer_connection_status'] = 'exact_ordered_tree_match'
                elif any(_ac(root[1]) == _ac(answer_tree) for root in roots):
                    result['answer_connection_status'] = 'ac_equivalent_only'
                else:
                    result['answer_connection_status'] = 'no_exact_or_ac_tree_match'
                if (final['value'] is not None and
                        not any(root[0] == Fraction(final['value']) for root in roots)):
                    result['complete_trace_status'] = 'inconsistent'
                    result['reasons'].append('derivation_answer_value_mismatch')
                if (result['complete_trace_status'] != 'inconsistent' and
                        final['correct'] and
                        result['answer_connection_status'] == 'exact_ordered_tree_match'):
                    result['complete_trace_status'] = 'verified'
                elif result['complete_trace_status'] != 'inconsistent':
                    result['reasons'].append('full_connection_not_verified_under_exact_tree_rule')
    result['reasons'] = sorted(set(result['reasons']))
    return result
