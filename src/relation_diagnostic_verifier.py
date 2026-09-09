"""C016 exposed-prompt checks and semantic metrics. No construction imports.

Teacher-forced token statistics require externally supplied loss/correctness
arrays. This module never loads a model or changes the SFT objective.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
import re

from src.relation_verifier import parse_prompt, check_certificate, STEP, FINAL
from src.sft_data import prefix

ROUTE_MARKER = '\nRequired route (follow these edges in this order):\n'
ROUTE_LINE = re.compile(r'R E (\d{3}) : N (\d{3}) > N (\d{3})')
FIELDS = ('edge_id', 'from_node', 'before_state', 'to_node', 'after_state',
          'final_state', 'eos', 'other_response')


def required_route(prompt):
    """Return a legal oriented route from instructions, without gold metadata."""
    q = parse_prompt(prompt)
    header = prompt.split('\nEdges:\n')[0]
    if header.count(ROUTE_MARKER) != 1:
        raise ValueError('Exactly one required-route instruction is necessary')
    lines = header.split(ROUTE_MARKER)[1].splitlines()
    if len(lines) != 4:
        raise ValueError('Required route must contain four steps')
    edges = {e['id']: e for e in q['edges']}
    node, seen, out = q['source'], {q['source']}, []
    for line in lines:
        match = ROUTE_LINE.fullmatch(line)
        if match is None:
            raise ValueError('Malformed route instruction')
        edge_id, u, v = map(int, match.groups())
        e = edges.get(edge_id)
        if e is None or {u, v} != {e['u'], e['v']} or u != node or v in seen:
            raise ValueError('Absent, disconnected or cyclic required route')
        out.append((edge_id, u, v)); seen.add(v); node = v
    if node != q['target']:
        raise ValueError('Required route misses query target')
    return out


def check_diagnostic(prompt, response, arm):
    if arm not in ('single_step', 'given_route', 'fixed_reference'):
        raise ValueError('Unknown diagnostic arm')
    try:
        q = parse_prompt(prompt)
        route = required_route(prompt) if arm == 'given_route' else None
        if arm != 'given_route' and ROUTE_MARKER in prompt:
            raise ValueError('Unexpected route hint')
        if len(q['edges']) != (1 if arm == 'single_step' else 32):
            raise ValueError('Wrong edge count for diagnostic')
    except ValueError:
        return {'valid': False, 'reason': 'invalid_diagnostic_prompt'}
    proof = check_certificate(prompt, response)
    if not proof['valid']:
        return proof
    if route is not None:
        steps = [tuple(map(int, STEP.fullmatch(line).groups()))
                 for line in response.splitlines()[:-1]]
        if [(s[0], s[1], s[3]) for s in steps] != route:
            return {'valid': False, 'reason': 'wrong_required_route'}
    return proof


def line_diagnostics(prompt, text):
    """Inspect every parseable line even when the final answer/EOS is absent.

    Local correctness is conditional on the line's own input state; it is not
    correctness under the original query, route continuity, or complete proof.
    """
    q = parse_prompt(prompt); edges = {e['id']: e for e in q['edges']}
    parsed, values = [], Counter()
    for line_no, line in enumerate(text.strip(' \t\r\n').splitlines(), 1):
        match = STEP.fullmatch(line)
        if match is None:
            continue
        edge_id, u, before, v, after = map(int, match.groups())
        e = edges.get(edge_id); grounded = False; correct = False
        if e and (u, v) == (e['u'], e['v']):
            grounded = True; correct = e['table'][before] == after
        elif e and (u, v) == (e['v'], e['u']):
            grounded = True; correct = e['table'][after] == before
        values[str(after)] += 1
        parsed.append({'line': line_no, 'grounded': grounded,
                       'local_lookup_correct': correct, 'after_state': after})
    return {'parseable_lines': len(parsed), 'grounded_lines': sum(p['grounded'] for p in parsed),
            'locally_correct_lines': sum(p['local_lookup_correct'] for p in parsed),
            'after_state_counts': dict(values), 'lines': parsed}


def score(row, text, eos, truncated):
    clean = text.strip(' \t\r\n')
    proof = check_diagnostic(row['prompt'], clean, row['arm'])
    lines = clean.splitlines(); final = FINAL.fullmatch(lines[-1]) if lines else None
    return {'certificate': proof,
            'answer_correct': bool(final and int(final.group(1)) == row['answer']),
            'complete_correct': bool(proof['valid'] and eos and not truncated),
            'reference_exact': clean == row['response'],
            'ended_with_eos': bool(eos), 'truncated': bool(truncated),
            'local_steps': line_diagnostics(row['prompt'], clean),
            'normalization': 'outer_ascii_whitespace_only'}


def summarize(rows, scores):
    if not rows or len(rows) != len(scores) or len({r['problem_id'] for r in rows}) != len(rows):
        raise ValueError('Require each scheduled evaluation row exactly once')
    if len({(r['arm'], r['split']) for r in rows}) != 1:
        raise ValueError('Summarize each arm and split separately')
    groups = defaultdict(list)
    for row, result in zip(rows, scores):
        groups[row['parent_world_id']].append(result)
    expected = 4 if rows[0]['arm'] == 'single_step' else 1
    if any(len(g) != expected for g in groups.values()):
        raise ValueError('Missing or duplicated parent subproblem')
    values = Counter()
    for result in scores:
        values.update(result['local_steps']['after_state_counts'])
    return {'rows': len(rows), 'parents': len(groups),
            'all_correct_parents': sum(all(x['complete_correct'] for x in g) for g in groups.values()),
            **{k: sum(x[k] for x in scores) for k in
               ('complete_correct', 'answer_correct', 'reference_exact', 'ended_with_eos', 'truncated')},
            'first_failure_reasons': dict(Counter(x['certificate']['reason'] for x in scores)),
            'after_state_counts_all_parseable_lines': dict(values),
            **{k: sum(x['local_steps'][k] for x in scores) for k in
               ('parseable_lines', 'grounded_lines', 'locally_correct_lines')}}


def token_fields(row, tokenizer, encoded):
    """Disjoint exact full-serialization target positions, including terminal EOS."""
    pre = prefix(row['prompt']); text = pre + row['response']
    tok = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    if list(tok['input_ids']) + [tokenizer.eos_token_id] != encoded['input_ids']:
        raise ValueError('Semantic mask tokenization differs from training')
    offsets = tok['offset_mapping']; result = {k: [] for k in FIELDS}
    cursor = len(pre); lines = row['response'].splitlines()
    for line_i, line in enumerate(lines):
        final = line_i == len(lines)-1
        match = (FINAL if final else STEP).fullmatch(line)
        if match is None:
            raise ValueError('Malformed reference for semantic mask')
        names = ('final_state',) if final else FIELDS[:5]
        for group, name in enumerate(names, 1):
            a, b = match.span(group); a += cursor; b += cursor
            positions = [i for i, (s, t) in enumerate(offsets) if s < b and t > a]
            if not positions or offsets[positions[0]][0] != a or offsets[positions[-1]][1] != b:
                raise ValueError('Semantic value has a boundary-straddling token')
            result[name].extend(positions)
        cursor += len(line) + 1
    result['eos'] = [len(encoded['input_ids'])-1]
    assigned = [i for v in result.values() for i in v]
    target = {i for i, label in enumerate(encoded['labels']) if i and label != -100}
    if len(set(assigned)) != len(assigned) or not set(assigned) <= target:
        raise ValueError('Overlapping or unsupervised semantic mask')
    result['other_response'] = sorted(target - set(assigned))
    return result


def teacher_forced_metrics(encoded, fields, losses, correct):
    """Arrays are indexed by target position j; losses come from logits[j-1].

    Prompt positions must be None. These are measurements only, with unchanged
    token-normalized training. Greedy correctness here has a gold prefix.
    """
    n = len(encoded['input_ids'])
    if len(losses) != n or len(correct) != n or set(fields) != set(FIELDS):
        raise ValueError('Wrong per-token metric shape or fields')
    target = {i for i, x in enumerate(encoded['labels']) if i and x != -100}
    flattened = [i for positions in fields.values() for i in positions]
    if len(set(flattened)) != len(flattened) or set(flattened) != target:
        raise ValueError('Fields must partition supervised shifted targets')
    for i in range(n):
        if i in target:
            if type(losses[i]) not in (float, int) or not math.isfinite(losses[i]) or losses[i] < 0 or type(correct[i]) is not bool:
                raise ValueError('Invalid supervised token statistic')
        elif losses[i] is not None or correct[i] is not None:
            raise ValueError('Prompt statistics must be masked')
    def stats(indices):
        size = len(indices); total = math.fsum(losses[i] for i in indices)
        return {'tokens': size, 'loss_sum': total, 'nll': total/size if size else None,
                'correct': sum(correct[i] for i in indices),
                'accuracy': sum(correct[i] for i in indices)/size if size else None}
    return {'all_response': stats(sorted(target)),
            'by_field': {k: stats(v) for k, v in fields.items()},
            'after_state_by_step': [stats([i]) for i in fields['after_state']],
            'conditioning': 'teacher_forced_gold_prefix_not_free_generation'}
