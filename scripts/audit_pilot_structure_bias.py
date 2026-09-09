"""Post-hoc seed-17 structure diagnostics from saved CPU-readable artifacts only.

This entry point never reads reserved holdout groups, runs a model, or changes
the frozen pilot. Identity labels concern the four selected reference paths,
not the complete set of mathematically possible solutions for a problem.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from src.countdown_smoke import canonical, safe_parse, verify_expression
from src.evaluation import score_text


ARMS = ('repeat', 'surface', 'paths', 'gcm')
DATA = Path('runs/pilot_v1_20260908_r3')
DEFINITIONS = {
    'identity_operation': 'A multiplication with either evaluated operand equal to 1; division with evaluated denominator 1; addition with either evaluated operand 0; subtraction with evaluated right operand 0. Operands are evaluated exactly as rational numbers, including intermediate expressions.',
    'excluded_examples': '0 - x, 1 / x, multiplication by 0, and x / x with x != 1 are not themselves identity operations under this definition. A neutral operation nested inside them is still recorded.',
    'has_input_one': 'The original input-number list contains the literal integer 1; distinct from evaluated intermediate identity operands.',
    'any_reference_identity': 'At least one of the four frozen selected reference paths contains an identity operation.',
    'all_reference_identity': 'All four frozen selected reference paths contain an identity operation.',
    'block': 'One frozen four-problem shared-structure selection block; the matched development set has 16 blocks.',
    'sample_success_count': 'Number of final-expression-correct outputs among the four saved stochastic generations for a problem; sample indices must be exactly 0, 1, 2, 3.',
}
LIMITATIONS = [
    'This is a post-hoc diagnostic of seed 17, not a confirmatory result, new primary endpoint, or hypothesis test.',
    'Identity strata describe selected reference paths, not all solutions; absence of a selected identity path does not prove the problem admits no identity-based solution.',
    'Strata were inspected after model outcomes. They do not identify a causal effect of identity operations, and can differ in difficulty, targets and structure support.',
    'Problems belong to 16 matched-development selection blocks and share one trained model per arm. Counts do not measure training-seed uncertainty or population significance.',
    'Broader development uses one stored reference per problem and cannot be labeled using four-path identity strata.',
    'Correctness is independently rescored from final expressions. Intermediate generated calculation steps are not audited by this script.',
    'No GPU inference, reserved holdout reading, data selection, training change or main-endpoint change is performed.',
]


def identity_operations(tree):
    """Return exact value and identity events; subtraction/division are ordered."""
    from fractions import Fraction

    def walk(node, address):
        if node[0] == 'n':
            return Fraction(node[1]), []
        op, left, right = node
        a, left_events = walk(left, address + 'L')
        b, right_events = walk(right, address + 'R')
        if op == '+':
            result, identity = a + b, a == 0 or b == 0
        elif op == '-':
            result, identity = a - b, b == 0
        elif op == '*':
            result, identity = a * b, a == 1 or b == 1
        elif op == '/':
            result, identity = a / b, b == 1
        else:
            raise ValueError('Unknown arithmetic operator')
        events = left_events + right_events
        if identity:
            events.append({'node_address': address or 'root', 'operator': op,
                           'left_value': str(a), 'right_value': str(b)})
        return result, events

    return walk(tree, '')


def path_features(row):
    tree = safe_parse(row['expression'])
    if not verify_expression(row['expression'], row['numbers'], row['target']):
        raise ValueError('Invalid reference expression')
    if canonical(tree) != row['path_id'] or canonical(tree, structure_only=True) != row['structure_id']:
        raise ValueError('Reference path/structure identity differs from expression')
    _, events = identity_operations(tree)
    return {'path_id': row['path_id'], 'structure_id': row['structure_id'],
            'expression': row['expression'], 'has_identity_operation': bool(events),
            'identity_operations': events}


def block_records(blocks, split):
    records = []
    for block_id, block in enumerate(blocks):
        if len(block['problems']) != 4 or len(set(block['structures'])) != 4:
            raise ValueError('Expected four problems and four structures per block')
        for item in block['problems']:
            problem, paths = item['problem'], item['paths']
            if [p['structure_id'] for p in paths] != block['structures']:
                raise ValueError('Reference structures do not match the selection block')
            if any(any(p[k] != problem[k] for k in ('problem_id', 'numbers', 'target', 'prompt')) for p in paths):
                raise ValueError('Reference does not match its problem')
            features = [path_features(p) for p in paths]
            count = sum(p['has_identity_operation'] for p in features)
            records.append({**{k: problem[k] for k in ('problem_id', 'numbers', 'target', 'prompt')},
                            'split': split, 'block_id': block_id,
                            'has_input_one': 1 in problem['numbers'],
                            'reference_identity_path_count': count,
                            'any_reference_identity': count > 0,
                            'all_reference_identity': count == 4, 'paths': features})
    if len({r['problem_id'] for r in records}) != len(records):
        raise ValueError('Duplicate problem identity across selection blocks')
    return records


def checked_predictions(predictions, references, samples):
    """Reject corrupted IDs/scores rather than trusting saved booleans."""
    grouped = {r['problem_id']: [] for r in references}
    refs = {r['problem_id']: r for r in references}
    if len(refs) != len(references):
        raise ValueError('Duplicate reference identity')
    for prediction in predictions:
        pid = prediction['problem_id']
        if pid not in refs:
            raise ValueError('Prediction has unknown problem identity')
        ref = refs[pid]
        if any(prediction[k] != ref[k] for k in ('numbers', 'target', 'prompt')):
            raise ValueError('Prediction prompt does not match frozen reference')
        rescored = score_text(prediction['text'], ref['numbers'], ref['target'])
        if any(type(prediction[k]) is not type(v) or prediction[k] != v for k, v in rescored.items()):
            raise ValueError('Saved correctness differs from rescored text')
        grouped[pid].append(prediction)
    for values in grouped.values():
        indices = [p['sample_index'] for p in values]
        if any(type(i) is not int for i in indices) or sorted(indices) != list(range(samples)):
            raise ValueError('Missing or duplicated sample indices')
        values.sort(key=lambda p: p['sample_index'])
    return grouped


def summarize_stratum(records):
    result = {'problems': len(records), 'arms': {}}
    for arm in ARMS:
        values = [r['predictions'][arm] for r in records]
        correct = sum(v['greedy_correct'] for v in values)
        histogram = Counter(v['sample_success_count'] for v in values)
        result['arms'][arm] = {
            'greedy_correct': correct,
            'greedy_accuracy': correct / len(records) if records else None,
            'sample_success_count_histogram': {str(c): histogram[c] for c in range(5)},
            'sample_correct_generations': sum(v['sample_success_count'] for v in values),
            'sample_problems_with_any_success': sum(v['sample_success_count'] > 0 for v in values),
        }
    paired = Counter((r['predictions']['paths']['greedy_correct'],
                      r['predictions']['gcm']['greedy_correct']) for r in records)
    result['paths_minus_gcm'] = {
        'greedy_correct_count_difference': result['arms']['paths']['greedy_correct'] - result['arms']['gcm']['greedy_correct'],
        'both_correct': paired[True, True], 'paths_only': paired[True, False],
        'gcm_only': paired[False, True], 'both_wrong': paired[False, False],
        'sample_any_success_count_difference': result['arms']['paths']['sample_problems_with_any_success'] - result['arms']['gcm']['sample_problems_with_any_success'],
    }
    return result


def selection_summary(records):
    structure_sets = Counter(tuple(p['structure_id'] for p in r['paths']) for r in records)
    # Four records share a selection block and its structure set.
    return {'problems': len(records), 'blocks': len({r['block_id'] for r in records}),
            'contains_input_one': sum(r['has_input_one'] for r in records),
            'any_reference_identity': sum(r['any_reference_identity'] for r in records),
            'all_reference_identity': sum(r['all_reference_identity'] for r in records),
            'identity_reference_paths': sum(r['reference_identity_path_count'] for r in records),
            'total_reference_paths': 4 * len(records),
            'distinct_structure_sets': len(structure_sets),
            'structure_set_histogram': [{'structures': list(k), 'blocks': v // 4}
                                        for k, v in sorted(structure_sets.items())]}


def build_audit(repo):
    repo = Path(repo)
    sources = {}

    def read(path, jsonl=False):
        raw = (repo / path).read_bytes()
        sources[str(path)] = hashlib.sha256(raw).hexdigest()
        return [json.loads(line) for line in raw.splitlines()] if jsonl else json.loads(raw)

    train = block_records(read(DATA / 'train_blocks.json'), 'train')
    matched = block_records(read(DATA / 'dev_blocks.json'), 'dev_matched')
    matched_references = read(DATA / 'dev_matched.jsonl', jsonl=True)
    broad = read(DATA / 'dev_broad.jsonl', jsonl=True)
    if {r['problem_id'] for r in matched} != {r['problem_id'] for r in matched_references}:
        raise ValueError('Matched prediction reference set differs from selected blocks')
    if len(train) != 256 or len(matched) != 64 or len(broad) != 64:
        raise ValueError('This diagnostic is frozen to the seed-17 pilot sizes')
    if any({tuple(r['numbers']) for r in a} & {tuple(r['numbers']) for r in b}
           for a, b in ((train, matched), (train, broad), (matched, broad))):
        raise ValueError('Overlapping problem-number groups')
    broad_records = [{**{k: r[k] for k in ('problem_id', 'numbers', 'target', 'prompt')},
                      'split': 'dev_broad', 'has_input_one': 1 in r['numbers'],
                      'single_reference_features': path_features(r), 'predictions': {}}
                     for r in broad]
    for r in matched:
        r['predictions'] = {}
    training_commits = set()
    for arm in ARMS:
        run = Path(f'runs/pilot_v1_{arm}_seed17_r1')
        manifest = read(run / 'run_manifest.json')
        cfg = manifest['config']
        if (manifest['status'] != 'completed' or cfg['seed'] != 17 or cfg['arm'] != arm
                or cfg['data_dir'] != str(DATA) or cfg['samples_per_problem'] != 4):
            raise ValueError('Expected the completed frozen seed-17 arm')
        training_commits.add(manifest['git_commit'])
        greedy = checked_predictions(read(run / 'final_dev_greedy.jsonl', jsonl=True), matched, 1)
        sampled = checked_predictions(read(run / 'final_dev_sampled.jsonl', jsonl=True), matched, 4)
        broader = checked_predictions(read(run / 'final_dev_broad_greedy.jsonl', jsonl=True), broad, 1)
        for r in matched:
            pid = r['problem_id']
            g, s = greedy[pid][0], sampled[pid]
            r['predictions'][arm] = {
                'greedy_correct': g['correct'], 'greedy_parsed': g['parsed'],
                'sample_success_count': sum(p['correct'] for p in s),
                'sample_correct_flags': [p['correct'] for p in s],
                'sample_distinct_correct_structures': len({p['structure_id'] for p in s if p['correct']}),
            }
        for r in broad_records:
            g = broader[r['problem_id']][0]
            r['predictions'][arm] = {'greedy_correct': g['correct'], 'greedy_parsed': g['parsed']}
    if len(training_commits) != 1:
        raise ValueError('Comparison arms have different training-source commits')
    for path in ('scripts/audit_pilot_structure_bias.py', 'src/countdown_smoke.py',
                 'src/evaluation.py', 'src/metrics.py'):
        sources[path] = hashlib.sha256((repo / path).read_bytes()).hexdigest()
    strata = {}
    for key in ('has_input_one', 'any_reference_identity', 'all_reference_identity'):
        strata[key] = {str(v).lower(): summarize_stratum([r for r in matched if r[key] is v])
                       for v in (False, True)}
    blocks = []
    for block_id in sorted({r['block_id'] for r in matched}):
        blocks.append({'block_id': block_id,
                       **summarize_stratum([r for r in matched if r['block_id'] == block_id])})
    summary = {
        'status': 'POST_HOC_SEED17_CPU_DIAGNOSTIC', 'training_seed': 17,
        'training_source_commit': next(iter(training_commits)),
        'definitions': DEFINITIONS, 'limitations': LIMITATIONS,
        'selection': {'train': selection_summary(train), 'dev_matched': selection_summary(matched),
                      'dev_broad': {'problems': len(broad), 'contains_input_one': sum(r['has_input_one'] for r in broad_records),
                                    'four_path_identity_strata_available': False}},
        'matched_overall': summarize_stratum(matched), 'matched_strata': strata,
        'matched_selection_blocks': blocks,
        'broader_greedy_correct': {a: sum(r['predictions'][a]['greedy_correct'] for r in broad_records) for a in ARMS},
        'sources_sha256': dict(sorted(sources.items())),
        'predictions_independently_rescored': True,
    }
    return summary, train + matched + broad_records


def write_audit(out, summary, records):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'summary.json').open('x') as stream:
        stream.write(json.dumps(summary, indent=2) + '\n')
    with (out / 'per_problem.jsonl').open('x') as stream:
        for record in records:
            stream.write(json.dumps(record, separators=(',', ':')) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Diagnostic output is immutable: ' + str(args.out))
    summary, records = build_audit(Path('.'))
    write_audit(args.out, summary, records)
    print(json.dumps({'status': summary['status'], 'problems': len(records),
                      'matched': summary['matched_overall']}))


if __name__ == '__main__':
    main()
