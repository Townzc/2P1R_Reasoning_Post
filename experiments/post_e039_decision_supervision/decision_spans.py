"""Exact first semantic commitment in the unchanged arithmetic renderers.

Character provenance is derived from the ordered AST and then checked against
the original response bytes. No model outcome or loss chooses a position.
"""
from __future__ import annotations

from experiments.post_e036_goal_probe.data import at, replace_op, OPS, digest
from experiments.thursday_probe.common import response
from src.countdown_smoke import safe_parse, value, expression, format_fraction
from src.pilot_data import SURFACE_FRAMES, verify_row
from src.sft_data import encode_row, prefix


def _contains(node_path, hole_path):
    return hole_path is not None and tuple(hole_path[:len(node_path)]) == tuple(node_path)


def render_with_provenance(tree, style, hole_path=None):
    """Return exact historical rendering and auditable semantic character atoms."""
    if style not in (0, 1):
        raise ValueError('Only the two frozen historical response styles are admitted')
    text = ''; atoms = []; steps = 0

    def add(fragment, kind=None, path=(), dependent=False):
        nonlocal text
        start = len(text); text += fragment
        if kind:
            atoms.append(dict(kind=kind, response_char_span=[start, len(text)],
                              ast_path=list(path), depends_on_hole=bool(dependent), text=fragment))

    def operand(node, path):
        number = value(node); s = format_fraction(number)
        if number.denominator != 1 or number < 0: s = '(' + s + ')'
        add(s, 'input_copy' if node[0] == 'n' else 'computed_numeric', path, _contains(path, hole_path))

    def walk(node, path=()):
        nonlocal steps
        if node[0] == 'n': return
        walk(node[1], path+(1,)); walk(node[2], path+(2,)); steps += 1
        before, after = SURFACE_FRAMES[style].split('{eq}')
        add(before.format(i=steps)); operand(node[1], path+(1,)); add(' ')
        add(node[0], 'program_operator', path, hole_path is not None and tuple(path) == tuple(hole_path))
        add(' '); operand(node[2], path+(2,)); add(' = ')
        add(format_fraction(value(node)), 'computed_numeric', path, _contains(path, hole_path))
        add(after + '\n')

    def final(node, path=()):
        if node[0] == 'n':
            add(str(node[1]), 'input_copy', path); return
        add('('); final(node[1], path+(1,)); add(' ')
        add(node[0], 'program_operator', path, hole_path is not None and tuple(path) == tuple(hole_path))
        add(' '); final(node[2], path+(2,)); add(')')

    walk(tree); add('Answer: '); final(tree)
    if text != response(tree, style):
        raise ValueError('Provenance renderer differs from the frozen original renderer')
    return text, atoms


def _token_mask(offsets, spans, size):
    mask = [False] * size
    for i, (start, end) in enumerate(offsets):
        mask[i] = end > start and any(start < b and end > a for a, b in spans)
    return mask


def annotate(row, tokenizer, max_length=1024):
    """H: first unknown-dependent token mask; F: descriptive masks only.

All token coordinates refer to encode_row input_ids INCLUDING normal EOS.
The causal logit for token j is j-1. Masks never include prompt or EOS.
"""
    verify_row(row)
    interface = row.get('interface', 'F')
    if interface not in ('F', 'H'):
        raise ValueError('Only fixed H/F references can be annotated')
    hole = tuple(row['hole_path']) if interface == 'H' else None
    tree = safe_parse(row['expression']); style = row['rendering_id']
    rendered, atoms = render_with_provenance(tree, style, hole)
    if rendered != row['response']:
        raise ValueError('Original response must match its frozen style and ordered AST exactly')
    serialized = prefix(row['prompt']); full = serialized + rendered
    tokens = tokenizer(full, add_special_tokens=False, return_offsets_mapping=True)
    encoded = encode_row(row, tokenizer, max_length)
    if list(tokens['input_ids']) + [tokenizer.eos_token_id] != encoded['input_ids']:
        raise ValueError('Offset encoding differs from exact SFT serialization')
    offsets = list(tokens['offset_mapping']); size = len(encoded['input_ids'])
    shift = len(serialized)
    parts = {}
    for kind in ('program_operator', 'input_copy', 'computed_numeric'):
        spans = [[shift+a['response_char_span'][0], shift+a['response_char_span'][1]]
                 for a in atoms if a['kind'] == kind]
        parts[kind+'_mask'] = _token_mask(offsets, spans, size)
    # Tokenizer may merge whitespace with an atom; each category is descriptive,
    # so category masks need not partition generic punctuation or frame words.
    record = dict(interface=interface, problem_id=row['problem_id'],
        dataset_row_id=row.get('dataset_row_id'), source_row_sha256=digest(row),
        response_sha256=encoded['response_hash'], encoded_row_sha256=digest(encoded),
        input_length=size, supervised_tokens=encoded['n_supervised'],
        decision_mask=[False]*size, decision_token_indices=[], causal_logit_indices=[],
        semantic_atoms=atoms, **parts)
    if interface == 'F':
        record.update(status='F_decomposition_only', decision_weighting_enabled=False,
                      semantic_prefix_dead_end='unknown_without_strict_completion_certificate',
                      note='Input-copy/program-operator/computed-number masks describe the original valid reference; alternative legal programs are accepted.')
        return record
    if (row['template'].count('?') != 1 or
            safe_parse(row['template'].replace('?', row['correct_operator'])) != tree or
            expression(replace_op(tree, hole, '?')) != row['template'] or
            at(tree, hole)[0] != row['correct_operator']):
        raise ValueError('Hole path/operator/template does not identify this original reference')
    dependent = [atom for atom in atoms if atom['depends_on_hole']]
    if not dependent:
        raise ValueError('No unknown-dependent semantic commitment')
    first = dependent[0]
    if first['kind'] != 'program_operator' or tuple(first['ast_path']) != hole:
        raise ValueError('Unsupported earlier numerical/lexical commitment: intervention not implementable')
    start, end = first['response_char_span']
    if first['text'] != row['correct_operator'] or end-start != 1:
        raise ValueError('Decision is not the unknown hole operation')
    full_span = [start+shift, end+shift]
    mask = _token_mask(offsets, [full_span], size)
    indices = [i for i, flag in enumerate(mask) if flag]
    if not indices or indices != list(range(indices[0], indices[-1]+1)):
        raise ValueError('Decision token range is empty or discontinuous')
    first_token, stop_token = indices[0], indices[-1]+1
    cover = full[offsets[first_token][0]:offsets[stop_token-1][1]]
    if cover.strip() != row['correct_operator']:
        raise ValueError('Tokenizer merges decision with another semantic commitment')
    if any(encoded['labels'][i] == -100 for i in indices) or mask[-1] or first_token == 0:
        raise ValueError('Decision overlaps prompt/EOS or lacks a causal prediction position')
    candidates = {}
    for operator in OPS:
        alternate = response(replace_op(tree, hole, operator), style)
        if alternate[:start] != rendered[:start] or alternate[start:end] != operator:
            raise ValueError('Earlier reference prefix leaks the hole choice')
        candidate = tokenizer(serialized+alternate, add_special_tokens=False, return_offsets_mapping=True)
        alt_indices = [i for i, (a,b) in enumerate(candidate['offset_mapping']) if a<end+shift and b>start+shift]
        if not alt_indices or alt_indices[0] != first_token or list(candidate['input_ids'][:first_token]) != encoded['input_ids'][:first_token]:
            raise ValueError('Four decisions do not share the same exact causal token prefix')
        alt_ids = list(candidate['input_ids'][alt_indices[0]:alt_indices[-1]+1])
        candidates[operator] = dict(token_ids=alt_ids,
            surface=alternate[start:end], token_span=[alt_indices[0], alt_indices[-1]+1])
    if len({tuple(c['token_ids']) for c in candidates.values()}) != 4:
        raise ValueError('Candidate decision token sequences are not distinct')
    prefix_ids = encoded['input_ids'][:first_token]
    prefix_text = full[:offsets[first_token][0]]
    if tokenizer(prefix_text, add_special_tokens=False)['input_ids'] != prefix_ids:
        raise ValueError('Standalone forced prefix does not preserve exact token identity')
    record.update(status='valid_first_semantic_decision', decision_weighting_enabled=True,
        decision_mask=mask, decision_token_indices=indices, causal_logit_indices=[i-1 for i in indices],
        response_char_span=[start,end], full_char_span=full_span,
        token_span=[first_token,stop_token], span_type='hole_operator_at_first_postorder_calculation',
        decision_token_count=len(indices), correct_operator=row['correct_operator'],
        hole_path=list(hole), rendering_id=style, earlier_hole_dependent_atoms=0,
        dependency='The hole operator is emitted before its result; earlier operands/calculations contain no hole-dependent subtree.',
        prefix_input_ids=prefix_ids, prefix_text=prefix_text, prefix_sha256=digest(prefix_ids),
        candidates=candidates, all_candidate_prefixes_identical=True,
        character_prefix_before_decision_identical_for_all_four_operations=True,
        multi_token=len(indices)>1, prompt_masked=True, EOS_decision_mask=False,
        prior_leakage=False, reference_decision_ids=[encoded['input_ids'][i] for i in indices])
    return record


annotate_h = annotate


def validate_mask(encoded, record):
    if record['encoded_row_sha256'] != digest(encoded) or len(record['decision_mask']) != len(encoded['input_ids']):
        raise ValueError('Decision mask/data serialization identity differs')
    indices = [i for i, flag in enumerate(record['decision_mask']) if flag]
    if indices != record['decision_token_indices'] or any(encoded['labels'][i] == -100 for i in indices) or record['decision_mask'][-1]:
        raise ValueError('Decision mask overlaps forbidden labels or changed indices')
    if record['causal_logit_indices'] != [i-1 for i in indices]:
        raise ValueError('Causal decision mask is shifted incorrectly')
    return True
