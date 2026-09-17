"""CPU-only, outcome-blind paired-goal release and training-support audit.

Run from the repository root. Protected splits are excluded by public allocation
identities; their question files are never opened. All writes are exclusive.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import random

from src.countdown_smoke import expression, safe_parse, value, verify_expression
from src.sft_data import prefix, read_jsonl, sha256_file

RELEASE = Path('experiments/post_e036_goal_probe/release_v1')
OLD_DATA = Path('experiments/thursday_probe/data_r1')
V2_DATA = Path('experiments/thursday_probe_v2/release_r2')
SEED = 20260917
OPS = ('+', '-', '*', '/')
# Five ordered binary-tree shapes, leaves are positions in the displayed order.
SHAPES = (((0, 1), (2, 3)), (((0, 1), 2), 3), ((0, (1, 2)), 3),
          (0, ((1, 2), 3)), (0, (1, (2, 3))))


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def dump(path, obj):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def write_rows(path, rows):
    with Path(path).open('x', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n')


def load_rows(interface, release=RELEASE):
    if interface not in ('F', 'H', 'C'):
        raise ValueError('Unknown interface')
    return read_jsonl(Path(release) / (interface + '.jsonl'))


def load_operator_rows(release=RELEASE):
    return read_jsonl(Path(release) / 'operator_contexts.jsonl')


def node_paths(tree, path=()):
    if tree[0] == 'n':
        return []
    return [path] + node_paths(tree[1], path + (1,)) + node_paths(tree[2], path + (2,))


def at(tree, path):
    for child in path:
        tree = tree[child]
    return tree


def replace_op(tree, path, op):
    if not path:
        return (op, tree[1], tree[2])
    result = list(tree)
    result[path[0]] = replace_op(tree[path[0]], path[1:], op)
    return tuple(result)


def family(tree):
    """Ordered operator skeleton, deliberately no AC canonicalization."""
    return 'N' if tree[0] == 'n' else [tree[0], family(tree[1]), family(tree[2])]


def degeneracy(op, left, right):
    if op == '+':
        return left == 0 or right == 0
    if op == '-':
        return right == 0
    if op == '*':
        return left in (0, 1) or right in (0, 1)
    if op == '/':
        return left == 0 or right in (0, 1)
    raise ValueError(op)


def path_labels(tree, hole_path):
    labels = []
    for path in node_paths(tree):
        node = at(tree, path)
        left, right = value(node[1]), value(node[2])
        labels.append(dict(path=list(path), at_hole=tuple(path) == tuple(hole_path),
                           operator=node[0], left=str(left), right=str(right), result=str(value(node)),
                           identity_or_absorbing=degeneracy(node[0], left, right)))
    return labels


def protected_identities():
    """Read only released training/development rows and allocation metadata."""
    historical_path = Path('runs/pilot_v1_20260908_r3/manifest.json')
    historical = json.loads(historical_path.read_text())
    allocation_path = historical_path.parent / 'split_allocation.json'
    if sha256_file(allocation_path) != historical['files_sha256']['split_allocation.json']:
        raise ValueError('Historical public split-identity manifest changed')
    public_allocation = json.loads(allocation_path.read_text())
    if public_allocation['seed'] != historical['seed']:
        raise ValueError('Historical allocation seed changed')
    counts = {'train': historical['splits']['train']['allocated_groups'],
              'dev': historical['splits']['dev_matched']['allocated_groups'],
              'holdout_reserved': historical['splits']['holdout']['reserved_raw_groups']}
    groups = list(itertools.combinations(range(1, 41), 4))
    random.Random(historical['seed']).shuffle(groups)
    excluded, sources, allocations = set(), {}, {}
    start = 0
    for name, count in counts.items():
        selected = groups[start:start + count]
        if [list(g) for g in selected] != public_allocation['groups'][name]:
            raise ValueError('Reconstructed protected identities differ from published allocation')
        excluded.update(selected)
        allocations[name] = {'count': count, 'identities_sha256': digest(selected)}
        start += count
    sources[str(historical_path)] = sha256_file(historical_path)
    sources[str(allocation_path)] = sha256_file(allocation_path)
    old_train_path = Path('runs/pilot_v1_20260908_r3/train_blocks.json')
    old_train = json.loads(old_train_path.read_text())
    if sha256_file(old_train_path) != historical['files_sha256']['train_blocks.json']:
        raise ValueError('Historical public training records changed')
    for block in old_train:
        for item in block['problems']:
            excluded.add(tuple(sorted(item['problem']['numbers'])))
    sources[str(old_train_path)] = sha256_file(old_train_path)
    # Exclude the complete earlier candidate pool, not only selected examples.
    exclusions_path = OLD_DATA / 'DATA_EXCLUSIONS.csv'
    with exclusions_path.open(newline='') as f:
        earlier_candidates = list(csv.DictReader(f))
    excluded.update(tuple(sorted(json.loads(r['numbers']))) for r in earlier_candidates)
    sources[str(exclusions_path)] = sha256_file(exclusions_path)
    known_files = [OLD_DATA / (name + '.jsonl') for name in (
        'surface', 'paths', 'train_problems', 'calibration', 'calibration_problems',
        'prep_control', 'prep_bridge', 'probes', 'discovery_problems')]
    known_files += [V2_DATA / 'calibration.jsonl', V2_DATA / 'calibration_fit.jsonl']
    known_counts = {}
    public_manifests = {folder: json.loads((folder / 'manifest.json').read_text())
                        for folder in (OLD_DATA, V2_DATA)}
    for folder in public_manifests:
        sources[str(folder / 'manifest.json')] = sha256_file(folder / 'manifest.json')
    if sha256_file(exclusions_path) != public_manifests[OLD_DATA]['files_sha256'][exclusions_path.name]:
        raise ValueError('Original candidate exclusion identities changed')
    for path in known_files:
        if sha256_file(path) != public_manifests[path.parent]['files_sha256'][path.name]:
            raise ValueError('Released training/development source changed: ' + str(path))
        rows = read_jsonl(path)
        identities = {tuple(sorted(row['numbers'])) for row in rows if row.get('numbers')}
        excluded.update(identities)
        known_counts[str(path)] = {'rows': len(rows), 'number_multisets': len(identities)}
        sources[str(path)] = sha256_file(path)
    return excluded, dict(allocation=allocations, known_public_sources=known_counts,
        old_candidate_pool_count=len(earlier_candidates), excluded_number_multisets=len(excluded),
        source_files_sha256=sources, reserved_question_contents_read=False,
        protected_identity_method='Published seed/allocation counts, identical combinations/shuffle algorithm; no solving or rendering of protected groups.',
        numerical_family_definition='Sorted exact input-number multiset, matching original number_group_hash.',
        structural_ood_claim=False)


def make_groups(excluded=(), seed=SEED, attempts_per_slot=100000):
    """Finite deterministic random proposal stream, quotas fixed before outcomes."""
    rng = random.Random(seed)
    forbidden = {tuple(sorted(g)) for g in excluded}
    selected, seen_families, rejects, attempts = [], set(), Counter(), 0
    for pair in itertools.combinations(OPS, 2):
        for slot in range(4):
            want_root = slot % 2 == 0
            for _ in range(attempts_per_slot):
                attempts += 1
                nums = rng.sample(range(1, 41), 4)
                key = tuple(sorted(nums))
                if key in forbidden:
                    rejects['excluded_or_duplicate_numbers'] += 1
                    continue
                def build(shape):
                    return ('n', nums[shape]) if isinstance(shape, int) else (rng.choice(OPS), build(shape[0]), build(shape[1]))
                tree = build(rng.choice(SHAPES))
                hole = () if want_root else rng.choice(node_paths(tree)[1:])
                skeleton = replace_op(tree, hole, '?')
                skeleton_family_id = digest(family(skeleton))
                if len(seen_families) < 8 and skeleton_family_id in seen_families:
                    rejects['initial_family_diversity'] += 1
                    continue
                values, trees = {}, {}
                for op in OPS:
                    filled = replace_op(skeleton, hole, op)
                    try:
                        values[op] = value(filled)
                        trees[op] = filled
                    except ZeroDivisionError:
                        values[op] = None
                chosen = [values[op] for op in pair]
                if any(v is None or v.denominator != 1 or not 10 <= v <= 100 for v in chosen):
                    rejects['target_domain'] += 1
                    continue
                if chosen[0] == chosen[1] or any(sum(v == target for v in values.values()) != 1 for target in chosen):
                    rejects['not_unique_switch'] += 1
                    continue
                node = at(tree, hole)
                left, right = value(node[1]), value(node[2])
                if any(degeneracy(op, left, right) for op in pair):
                    rejects['selected_hole_degenerate'] += 1
                    continue
                # Per pair, each operator is target_index0 twice and index1 twice.
                order = pair if slot % 2 == 0 else tuple(reversed(pair))
                group_id = f'goal_v1_g{len(selected):02d}'
                targets = [dict(target_index=i, target=int(values[op]), expected_operator=op,
                    correct_operator=op, expression=expression(trees[op]),
                    path_labels=path_labels(trees[op], hole)) for i, op in enumerate(order)]
                selected.append(dict(group_id=group_id, split='exploratory_development', numbers=nums,
                    number_group_hash=digest(list(key)), template=expression(skeleton), skeleton=expression(skeleton),
                    skeleton_ast=skeleton, hole_path=list(hole), hole_depth=len(hole),
                    skeleton_family=family(skeleton), skeleton_family_id=skeleton_family_id,
                    operator_pair=list(pair), targets=targets,
                    candidate_values={op: None if v is None else str(v) for op, v in values.items()}))
                forbidden.add(key)
                seen_families.add(skeleton_family_id)
                break
            else:
                raise RuntimeError(f'Finite proposal quota exhausted for pair={pair}, slot={slot}; no release written')
    audit = dict(seed=seed, attempts_per_slot=attempts_per_slot, total_attempts=attempts,
        rejections=dict(rejects), group_count=len(selected), target_count=2 * len(selected),
        operator_pair_counts=dict(Counter(''.join(r['operator_pair']) for r in selected)),
        correct_operator_counts=dict(Counter(t['expected_operator'] for r in selected for t in r['targets'])),
        operator_by_target_index={str(i): dict(Counter(r['targets'][i]['expected_operator'] for r in selected)) for i in (0, 1)},
        target_numeric_order=dict(Counter('ascending' if r['targets'][0]['target'] < r['targets'][1]['target'] else 'descending' for r in selected)),
        skeleton_families=len(seen_families), hole_depth_counts=dict(Counter(str(r['hole_depth']) for r in selected)),
        number_domain='Four distinct integers 1..40; ordered numeric leaves and displayed input order frozen.',
        target_domain='Exact integers 10..100, unchanged from src.countdown_smoke.solve_all.',
        domain_changed=False, selection_uses_model_outputs=False,
        target_order_rule='For each fixed unordered operator pair: forward, reverse, forward, reverse; each operator occurs six times at each target index. Numeric direction is audited, not silently selected.',
        degeneracy_rule='At selected hole: + excludes either operand0; - excludes right0; * excludes either operand0/1; / excludes numerator0 or denominator0/1. Other nodes labelled, not excluded.',
        structural_ood_claim=False)
    validate_groups(selected)
    return selected, audit


def validate_groups(groups):
    if len(groups) != 24 or len({tuple(sorted(g['numbers'])) for g in groups}) != 24:
        raise ValueError('Expected24 independent number groups')
    if Counter(tuple(g['operator_pair']) for g in groups) != Counter({p: 4 for p in itertools.combinations(OPS, 2)}):
        raise ValueError('Operator pair quotas differ')
    if len({g['skeleton_family_id'] for g in groups}) < 8:
        raise ValueError('Insufficient skeleton families')
    for group in groups:
        if group['template'].count('?') != 1 or len(set(group['numbers'])) != 4:
            raise ValueError('Malformed group')
        for target in group['targets']:
            if not verify_expression(target['expression'], group['numbers'], target['target']):
                raise ValueError('Invalid reference')
            hits = []
            for op in OPS:
                try:
                    if value(safe_parse(group['template'].replace('?', op))) == target['target']:
                        hits.append(op)
                except ZeroDivisionError:
                    pass
            if hits != [target['expected_operator']]:
                raise ValueError('Nonunique target')
            tree = safe_parse(target['expression'])
            node = at(tree, group['hole_path'])
            if degeneracy(node[0], value(node[1]), value(node[2])):
                raise ValueError('Degenerate hole')


def interface_rows(groups, interface):
    if interface not in ('F', 'H', 'C'):
        raise ValueError(interface)
    rows = []
    for group in groups:
        for target in group['targets']:
            row = {k: v for k, v in group.items() if k not in ('targets', 'candidate_values')}
            row.update(target)
            row.update(interface=interface, task='compute' if interface == 'C' else 'construct',
                problem_id=f"{group['group_id']}_t{target['target_index']}_{interface}")
            stem = (f'Use the numbers {", ".join(map(str, group["numbers"]))} exactly once each with +, -, *, / '
                    f'and parentheses to make {target["target"]}.')
            if interface == 'F':
                row['prompt'] = stem + ' Show calculations, then write Answer: followed by one expression.'
            elif interface == 'H':
                row['prompt'] = (stem + f' Template: {group["template"]}. Replace ? with one of +, -, *, /; '
                    'keep every number, its order, the parentheses, and all other operators unchanged. '
                    'Show calculations, then write Answer: followed by the completed full expression.')
            else:
                row['prompt'] = f'Evaluate {target["expression"]}. Show calculations, then write Answer: followed by the exact value.'
                row['answer'] = str(target['target'])
            rows.append(row)
    return rows


def operator_context(row, tokenizer):
    """Score exact full-encoding suffixes after the four-candidate token LCP."""
    answer_prefix = 'Answer: ' + row['template'].split('?', 1)[0]
    context = prefix(row['prompt']) + answer_prefix
    texts = {op: context + op for op in OPS}
    full = {op: list(tokenizer.encode(text, add_special_tokens=False)) for op, text in texts.items()}
    common = 0
    while common < min(map(len, full.values())) and len({ids[common] for ids in full.values()}) == 1:
        common += 1
    context_ids = full[OPS[0]][:common]
    candidates = {op: ids[common:] for op, ids in full.items()}
    context_only = list(tokenizer.encode(context, add_special_tokens=False))
    reason = None
    if not context_ids or any(not ids for ids in candidates.values()):
        reason = 'No nonempty common context and candidate suffix'
    elif len({tuple(ids) for ids in candidates.values()}) != 4:
        reason = 'Candidate encodings collide'
    elif any(len(a) < len(b) and b[:len(a)] == a
             for a, b in itertools.permutations(candidates.values(), 2)):
        reason = 'Candidate suffix events overlap: one token sequence prefixes another'
    elif any(tokenizer.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False) != texts[op]
             for op, ids in full.items()):
        reason = 'Full candidate tokenization is not losslessly reversible'
    record = {k: row[k] for k in ('problem_id', 'group_id', 'target_index', 'target', 'numbers',
        'template', 'skeleton', 'skeleton_family_id', 'hole_path', 'expected_operator', 'correct_operator', 'prompt')}
    record.update(answer_prefix=answer_prefix, full_context_text=context, prefix_text=answer_prefix,
        context_ids=context_ids, candidates=candidates, candidate_full_ids=full, candidate_texts=texts,
        context_only_ids=context_only, boundary_retokenized=context_ids != context_only,
        available=reason is None, reason=reason,
        prefix_audit=dict(expression_prefix_is_exact_text_before_hole=True, includes_filled_hole=False,
            includes_intermediate_result=False, includes_target_copied_as_answer=False,
            preceding_numerals_are_only_given_expression_leaves=True,
            continuation_ends_immediately_after_operator=True, includes_eos_or_explanation=False,
            tokens_reconstruct_full_candidates=all(context_ids + candidates[op] == full[op] for op in OPS)),
        scoring_note='Chain logprob of the entire differential token suffix from the common full-encoding prefix; raw and candidate-normalized probabilities must both be reported.')
    return record


def training_support(rows):
    number_targets, partial_targets, programs, ac_programs = defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set)
    joint = Counter()
    for row in rows:
        numbers = tuple(sorted(row['numbers']))
        target = str(row.get('target', row.get('answer')))
        tree = safe_parse(row['expression'])
        tree_id = digest(tree)
        number_targets[numbers].add(target)
        programs[(numbers, target)].add(tree_id)
        ac_programs[(numbers, target)].add(row.get('path_id', tree_id))
        for path in node_paths(tree):
            skeleton = replace_op(tree, path, '?')
            partial_targets[(numbers, expression(skeleton))].add(target)
        ops = ''.join(at(tree, path)[0] for path in node_paths(tree))
        style = str(row.get('rendering_id', row.get('template_family', 'unlabelled')))
        joint[(target, ops, digest(family(tree)), style)] += 1
    hist = lambda values: dict(sorted(Counter(str(len(x)) for x in values).items()))
    return dict(rows=len(rows), number_multisets=len(number_targets),
        distinct_targets_per_multiset_histogram=hist(number_targets.values()),
        distinct_targets_per_multiset=[dict(numbers=list(n), targets=sorted(ts), count=len(ts)) for n, ts in sorted(number_targets.items())],
        partial_skeleton_definition='Replace each binary node operator individually with ?; preserve ordered tree and all leaf numerals. Each observed row contributes all its operator holes.',
        distinct_targets_per_number_partial_skeleton_histogram=hist(partial_targets.values()),
        number_partial_skeletons=len(partial_targets),
        distinct_targets_per_number_partial_skeleton=[dict(numbers=list(n), skeleton=s, targets=sorted(ts), count=len(ts)) for (n, s), ts in sorted(partial_targets.items())],
        different_ordered_programs_per_number_target_histogram=hist(programs.values()),
        different_ac_path_ids_per_number_target_histogram=hist(ac_programs.values()),
        programs_per_number_target=[dict(numbers=list(n), target=t, ordered_programs=len(ps), ac_path_ids=len(ac_programs[(n,t)])) for (n,t), ps in sorted(programs.items())],
        joint_target_operator_skeleton_surface=[dict(target=t, operators_preorder=ops,
            ordered_skeleton_id=s, surface_template=style, rows=count) for (t,ops,s,style),count in sorted(joint.items())])


def train_target_support_audit():
    sources = {'surface': OLD_DATA / 'surface.jsonl', 'paths': OLD_DATA / 'paths.jsonl',
        'prep_control': OLD_DATA / 'prep_control.jsonl', 'prep_bridge': OLD_DATA / 'prep_bridge.jsonl',
        'C0_calibration_fit': V2_DATA / 'calibration_fit.jsonl'}
    raw = {name: read_jsonl(path) for name, path in sources.items()}
    scopes = {name: training_support(rows) for name, rows in raw.items()}
    for name, prep, main in (('E033','prep_control','surface'), ('E034','prep_control','paths'),
                            ('E035','prep_bridge','surface'), ('E036','prep_bridge','paths')):
        scopes[name + '_training_support_union'] = training_support(raw['C0_calibration_fit'] + raw[prep] + raw[main])
    return dict(status='CPU_EXACT_RELEASED_TRAINING_SUPPORT_AUDIT', scopes=scopes,
        source_files_sha256={str(p): sha256_file(p) for p in sources.values()},
        interpretation='Observed target/program support describes these released training records. It does not establish that any model ignores targets or identify a neural mechanism.',
        union_definition='One copy of each actual calibration-fit/prep/main source row; epoch repetition does not alter unique support. Separate scopes preserve the compute/construct distinction.',
        no_model_calls=True, no_reserved_contents_read=True)


def prepare(tokenizer_dir, output=RELEASE):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Refusing to overwrite frozen release')
    from scripts.audit_family_matching import verified_tokenizer
    tokenizer, token_identity = verified_tokenizer(Path(tokenizer_dir))
    excluded, leakage = protected_identities()
    groups, selection = make_groups(excluded)
    rows = {interface: interface_rows(groups, interface) for interface in ('F', 'H', 'C')}
    operator_rows = [operator_context(row, tokenizer) for row in rows['H']]
    for a, b in zip(operator_rows[::2], operator_rows[1::2]):
        if a['answer_prefix'] != b['answer_prefix']:
            raise ValueError('Paired targets have different forced answer prefixes')
    overlap = {tuple(sorted(g['numbers'])) for g in groups} & excluded
    if overlap:
        raise ValueError('Protected number-family overlap')
    leakage.update(selected_overlap=0, selected_number_group_hashes=[g['number_group_hash'] for g in groups])
    support = train_target_support_audit()
    output.mkdir(parents=True)
    write_rows(output / 'groups.jsonl', groups)
    for interface, data in rows.items():
        write_rows(output / (interface + '.jsonl'), data)
    write_rows(output / 'operator_contexts.jsonl', operator_rows)
    dump(output / 'TRAIN_TARGET_SUPPORT_AUDIT.json', support)
    dump(output / 'LEAKAGE_AUDIT.json', leakage)
    dump(output / 'DATA_AUDIT.json', selection)
    manifest = dict(status='FROZEN_BEFORE_MODEL_OUTPUTS_CPU_ONLY', seed=SEED,
        split='exploratory_development', group_count=24, interface_rows={k: len(v) for k,v in rows.items()},
        operator_contexts=len(operator_rows), operator_contexts_available=sum(r['available'] for r in operator_rows),
        operator_boundary_retokenized=sum(r['boundary_retokenized'] for r in operator_rows),
        tokenizer=token_identity, source_files_sha256={str(p): sha256_file(p) for p in (
            Path(__file__).relative_to(Path.cwd()), Path('src/countdown_smoke.py'), Path('src/sft_data.py'),
            Path('configs/models.lock.json'), Path('scripts/audit_family_matching.py'))},
        files_sha256={p.name: sha256_file(p) for p in sorted(output.iterdir()) if p.is_file()},
        prior_artifacts_modified=False, new_training=False, new_model_calls=0,
        limits='Numerical-instance separation only, no structural OOD or pretraining contamination claim; exploratory24 paired groups.')
    dump(output / 'manifest.json', manifest)
    return manifest


prepare_release = prepare

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=RELEASE)
    args = parser.parse_args()
    result = prepare(args.tokenizer_dir, args.output)
    print(json.dumps({k: result[k] for k in ('status', 'group_count', 'interface_rows', 'operator_contexts_available')}))
