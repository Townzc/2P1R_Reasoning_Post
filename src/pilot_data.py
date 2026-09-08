"""Frozen arithmetic pilot data and paired schedules; no model evaluation."""
from collections import Counter
import hashlib
import itertools
import json
import random
import re

from .countdown_smoke import canonical, safe_parse, verify_expression, render_trace
from .sft_data import encode_row, budget_report

ARMS = ('repeat', 'surface', 'paths', 'gcm')
SURFACE_FRAMES = ('Step {i}: {eq}.', 'We now calculate: {eq}.',
                  'Next, we obtain {eq}.', 'This calculation gives us {eq}.')


def allocate_groups(seed, counts, max_number=40):
    """Assign raw number groups before solving or selecting any path/target."""
    if any(n <= 0 for n in counts.values()):
        raise ValueError('Positive allocation counts required')
    groups = list(itertools.combinations(range(1, max_number + 1), 4))
    if sum(counts.values()) > len(groups):
        raise ValueError('Requested splits exceed the finite domain')
    random.Random(seed).shuffle(groups)
    result, start = {}, 0
    for name, count in counts.items():
        result[name] = groups[start:start + count]
        start += count
    return result


def surface_response(response, variant):
    if variant not in range(4):
        raise ValueError('Four fixed surface variants only')
    lines = response.splitlines()
    if len(lines) != 4 or not lines[-1].startswith('Answer: '):
        raise ValueError('Expected three canonical calculations and one answer')
    result = []
    for i, line in enumerate(lines[:3], 1):
        match = re.fullmatch(r'Step (\d+): (.+)\.', line)
        if not match or int(match[1]) != i:
            raise ValueError('Unexpected canonical trace')
        result.append(SURFACE_FRAMES[variant].format(i=i, eq=match[2]))
    return '\n'.join(result + [lines[-1]])


def verify_row(row):
    tree = safe_parse(row['expression'])
    if (not verify_expression(row['expression'], row['numbers'], row['target'])
            or canonical(tree) != row['path_id']
            or canonical(tree, structure_only=True) != row['structure_id']
            or row['response'].splitlines()[-1] != 'Answer: ' + row['expression']):
        raise ValueError('Invalid expression or path identity')
    if row['response'] not in {surface_response(render_trace(tree), v) for v in range(4)}:
        raise ValueError('Trace calculations or surface frame do not match the program')


def make_arms(blocks, seed):
    rng = random.Random(seed)
    rows = {arm: [] for arm in ARMS}
    for block_id, block in enumerate(blocks):
        if len(block['problems']) != 4 or len(set(block['structures'])) != 4:
            raise ValueError('Four problems and four structures per block required')
        assignment = list(range(4))
        rng.shuffle(assignment)
        anchor_index = rng.randrange(4)
        for round_id in range(4):
            for i, problem in enumerate(block['problems']):
                paths = problem['paths']
                if [p['structure_id'] for p in paths] != block['structures']:
                    raise ValueError('Inconsistent shared structure order')
                anchor = paths[anchor_index]
                choices = {'repeat': anchor, 'surface': dict(anchor, response=surface_response(anchor['response'], round_id)),
                           'paths': paths[(assignment[i] + round_id) % 4], 'gcm': paths[assignment[i]]}
                for arm, row in choices.items():
                    verify_row(row)
                    rows[arm].append(dict(row, block_id=block_id, round_id=round_id,
                                          rendering_id=round_id if arm == 'surface' else 0))
    return rows


def paired_schedule(block_count, cycles, seed):
    if min(block_count, cycles) <= 0:
        raise ValueError('Positive block count and cycles required')
    rng, schedule = random.Random(seed), []
    for _ in range(cycles):
        blocks = list(range(block_count))
        rng.shuffle(blocks)
        # Interleave rounds to avoid presenting a block four times consecutively.
        rounds = list(range(4))
        rng.shuffle(rounds)
        for round_id in rounds:
            for block in blocks:
                batch = list(range(16 * block + 4 * round_id, 16 * block + 4 * round_id + 4))
                rng.shuffle(batch)
                schedule.append(batch)
    return schedule


def audit_arms(rows, schedule, tokenizer, max_length=384):
    if set(rows) != set(ARMS) or not schedule:
        raise ValueError('All four arms and a nonempty schedule required')
    encoded, reports = {}, {}
    for arm in ARMS:
        for row in rows[arm]:
            verify_row(row)
        encoded[arm] = [encode_row(row, tokenizer, max_length) for row in rows[arm]]
        reports[arm] = budget_report(encoded[arm], schedule, 2)
    for update in schedule:
        problem_ids = [[rows[a][i]['problem_id'] for i in update] for a in ARMS]
        token_counts = [[encoded[a][i]['n_supervised'] for i in update] for a in ARMS]
        if any(x != problem_ids[0] for x in problem_ids) or any(x != token_counts[0] for x in token_counts):
            raise ValueError('Per-example exposure/token mismatch')
        if Counter(rows['paths'][i]['structure_id'] for i in update) != Counter(rows['gcm'][i]['structure_id'] for i in update):
            raise ValueError('Per-update global structure mismatch')
    exposure = {}
    for arm in ARMS:
        paths, texts = {}, {}
        for update in schedule:
            for i in update:
                r = rows[arm][i]
                paths.setdefault(r['problem_id'], set()).add(r['path_id'])
                texts.setdefault(r['problem_id'], set()).add(r['response'])
        expected_paths = 4 if arm == 'paths' else 1
        expected_texts = 4 if arm in ('paths', 'surface') else 1
        if set(map(len, paths.values())) != {expected_paths} or set(map(len, texts.values())) != {expected_texts}:
            raise ValueError('Wrong within-problem path/rendering diversity')
        exposure[arm] = {'paths_per_problem': expected_paths, 'texts_per_problem': expected_texts}
    return {'all_per_example_tokens_equal': True, 'all_per_update_structures_paths_gcm_equal': True,
            'paths_gcm_structure_tv': 0.0, 'diversity': exposure, 'arms': reports,
            'max_sequence_tokens': max(r['n_processed'] for values in encoded.values() for r in values)}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
