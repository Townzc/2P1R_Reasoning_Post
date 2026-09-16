"""Bounded training-only census, disjoint arithmetic construction and token audit."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import itertools
import json
from pathlib import Path
import random
import subprocess
import time

from experiments.thursday_probe.common import (ROOT, SEEDS, dump, jsonl, digest, stamp,
    motifs, path_record, response, operations, leaves, learning_rates, epoch_schedule)
from scripts.audit_family_matching import CENSUS_SHA, STREAM_SHA, verified_tokenizer
from src.countdown_smoke import (canonical, expression, safe_parse, value, solve_all,
    verify_expression, format_fraction, render_trace)
from src.sft_data import encode_row, budget_report, sha256_file
from src.trace_audit import audit_trace


def census(archive):
    raw_bytes = Path(archive).read_bytes()
    if sha256_file(archive) != CENSUS_SHA:
        raise ValueError('Original complete training inventory changed')
    raw = gzip.decompress(raw_bytes)
    import hashlib
    if hashlib.sha256(raw).hexdigest() != STREAM_SHA:
        raise ValueError('Original decompressed inventory changed')
    grouped = defaultdict(list)
    for line in raw.splitlines():
        r = json.loads(line)
        t = safe_parse(r['expression'])
        if not verify_expression(r['expression'], r['numbers'], r['target']):
            raise ValueError('Invalid census solution')
        grouped[r['problem_id']].append((canonical(t), canonical(t, structure_only=True), motifs(t)))
    scores = []
    for child, parent in itertools.permutations('+-*/', 2):
        m = child+'->'+parent
        eligible = []
        for pid, rows in grouped.items():
            yes = [x for x in rows if m in x[2]]
            no = [x for x in rows if m not in x[2]]
            if any(a[0] != b[0] and a[1] != b[1] for a in no for b in yes):
                eligible.append(pid)
        scores.append({'motif': m, 'control_motif': parent+'->'+child,
                       'eligible_questions': len(eligible), 'problem_ids': sorted(eligible)})
    scores.sort(key=lambda r: (-r['eligible_questions'], r['motif']))
    return {'source_sha256': CENSUS_SHA, 'source_questions': len(grouped),
            'ranking': scores, 'candidate_limit': 3, 'candidate_motifs': [x['motif'] for x in scores[:3]]}


def pair_from_solutions(numbers, solved, motif, tokenizer):
    """Target chosen by hash before lengths; no question filtering for token equality."""
    targets = sorted(solved, key=lambda t: digest([SEEDS['data'], numbers, t]))
    for target in targets:
        candidates = {'A': [], 'B': []}
        for tree in solved[target]:
            candidates['B' if motif in motifs(tree) else 'A'].append(tree)
        # One representative per AC structure, chosen by short serialization then hash.
        buckets = {}
        for family, trees in candidates.items():
            by_structure = defaultdict(list)
            for t in trees:
                by_structure[canonical(t, structure_only=True)].append(t)
            buckets[family] = [min(ts, key=lambda t: (len(tokenizer.encode(response(t), add_special_tokens=False)),
                                 digest(expression(t)))) for ts in by_structure.values()]
        if not buckets['A'] or not buckets['B']:
            continue
        lengths = {expression(t): len(tokenizer.encode(response(t), add_special_tokens=False))
                   for ts in buckets.values() for t in ts}
        pairs = [(a, b) for a in buckets['A'] for b in buckets['B']
                 if canonical(a, structure_only=True) != canonical(b, structure_only=True)]
        if not pairs:
            continue
        a, b = min(pairs, key=lambda pair: (abs(lengths[expression(pair[0])]-lengths[expression(pair[1])]),
                   lengths[expression(pair[0])]+lengths[expression(pair[1])], digest([expression(t) for t in pair])))
        pid = 'thu/'+digest([numbers, target])[:20]
        prompt = (f'Use the numbers {", ".join(map(str, numbers))} exactly once each with +, -, *, / '
                  f'and parentheses to make {target}. Show calculations, then write Answer: followed by one expression.')
        p = {'problem_id': pid, 'numbers': list(numbers), 'target': target, 'prompt': prompt,
             'task': 'construct', 'target_motif': motif, 'number_group_hash': digest(sorted(numbers)),
             'eligible_programs': len(solved[target]), 'eligible_structures': len({canonical(t, structure_only=True) for t in solved[target]}),
             'paths': {'A': path_record(a), 'B': path_record(b)}}
        for f, t in [('A', a), ('B', b)]:
            r = dict(p, **p['paths'][f], response=response(t), coarse_path=f, rendering_id=0)
            p['paths'][f]['supervised_tokens_v0'] = encode_row(r, tokenizer, 1024)['n_supervised']
            if audit_trace(r['response'], numbers, target)['complete_trace_status'] != 'verified':
                raise ValueError('New program failed independent trace/resource verifier')
        return p
    return None


def stratum(p):
    return (p['target']//20, p['paths']['A']['structure_id'], p['paths']['B']['structure_id'],
            (p['paths']['A']['supervised_tokens_v0']+p['paths']['B']['supervised_tokens_v0'])//32)


def build_arms(problems):
    if len(problems) % 4:
        raise ValueError('Balanced assignment needs N divisible by four')
    rng = random.Random(SEEDS['assignment'])
    ordered = sorted(problems, key=lambda p: (stratum(p), digest([SEEDS['assignment'], p['problem_id']])))
    assignment = {}
    # Adjacent pairs in the prespecified ordering; half A and half B exactly.
    for i in range(0, len(ordered), 2):
        fs = ['A', 'B']; rng.shuffle(fs)
        for p, f in zip(ordered[i:i+2], fs):
            assignment[p['problem_id']] = f
    variant = {p['problem_id']: i % 2 for i, p in enumerate(ordered)}
    arms = {a: [] for a in ('surface', 'paths', 'repeat')}
    for p in problems:
        anchor = assignment[p['problem_id']]
        for slot in (0, 1):
            choices = {'surface': (anchor, slot), 'paths': ('AB'[slot], slot ^ variant[p['problem_id']]),
                       'repeat': (anchor, variant[p['problem_id']])}
            for arm, (family, v) in choices.items():
                path = p['paths'][family]; t = safe_parse(path['expression'])
                r = {k: v0 for k, v0 in p.items() if k != 'paths'}
                r.update(path, response=response(t, v), coarse_path=family, rendering_id=v,
                         anchor_family=anchor, slot=slot, template_family=path['structure_id'])
                arms[arm].append(r)
    for arm, rows in arms.items():
        if Counter(r['coarse_path'] for r in rows) != {'A': len(problems), 'B': len(problems)}:
            raise ValueError('Global A/B imbalance')
        if Counter(r['rendering_id'] for r in rows) != {0: len(problems), 1: len(problems)}:
            raise ValueError('Global surface imbalance')
    return arms, assignment


def compute_row(tree, category, namespace):
    nums = sorted(leaves(tree)); target = value(tree)
    text = render_trace(tree).splitlines()
    text[-1] = 'Answer: '+format_fraction(target)
    return {'problem_id': 'thu/'+namespace+'/'+digest(expression(tree))[:20], 'task': 'compute',
            'prompt': f'Evaluate {expression(tree)}. Show calculations, then write Answer: followed by the exact value.',
            'response': '\n'.join(text), 'expression': expression(tree), 'answer': str(target),
            'numbers': nums, 'number_group_hash': digest(nums), 'category': category,
            'path_id': canonical(tree), 'structure_id': canonical(tree, structure_only=True),
            'interfaces': dict(motifs(tree)), 'operators': dict(Counter(x[0] for x in operations(tree))),
            'template_family': category+'/'+canonical(tree, structure_only=True)}


def exercise_sets(motif):
    child, parent = motif.split('->')
    rng = random.Random(SEEDS['prep'])
    triples = list(itertools.combinations(range(2, 41), 3)); rng.shuffle(triples)
    pairs = list(itertools.combinations(range(2, 41), 2)); rng.shuffle(pairs)
    # Allocate complete number groups before constructing examples, never based on model scores.
    atomic = []
    for i, nums in enumerate(pairs[:160]):
        a, b = [ ('n', x) for x in nums ]
        op = '+-*/'[i % 4]
        t = (op, b, a) if op == '-' else (op, a, b)
        atomic.append(compute_row(t, 'atomic', 'atom'))
    groups = {'prep_control': triples[:128], 'prep_bridge': triples[128:256],
              'probe_control': triples[256:288], 'probe_target': triples[288:320],
              'calibration_control': triples[320:336], 'calibration_target': triples[336:352]}
    result = {}
    for name, sets in groups.items():
        inner, outer = (parent, child) if 'control' in name else (child, parent)
        rows = []
        for nums in sets:
            # Rotate deterministically; no filtering on output magnitude/sign.
            a, b, c = [('n', x) for x in nums]
            t = (outer, (inner, c, a), b)
            try:
                rows.append(compute_row(t, 'control' if 'control' in name else 'target', name))
            except ZeroDivisionError:
                raise ValueError('Undefined preregistered exercise; revise before model calls')
        result[name] = rows
    result['prep_control'] = atomic[:128]+result['prep_control']
    result['prep_bridge'] = atomic[:128]+result['prep_bridge']
    result['probes'] = atomic[128:160]+result.pop('probe_target')+result.pop('probe_control')
    # In intended overlap, ONLY common128 atomic exercises are shared between prep arms.
    probes = {r['number_group_hash'] for r in result['probes']}
    for name in ('prep_control', 'prep_bridge'):
        if probes & {r['number_group_hash'] for r in result[name]}:
            raise ValueError('Prep/probe number group leakage')
    return result


def prefixes(problems):
    selected = []
    for p in sorted(problems, key=lambda p: digest(['prefix', p['problem_id']])):
        pair = []
        for f in 'AB':
            t = safe_parse(p['paths'][f]['expression']); ops = operations(t)
            pref = response(t).splitlines()[0]+'\n'
            # The first postorder operation cannot complete a two-operation motif.
            # Neither its value nor an Answer marker may reveal the final answer.
            if ops[0][3] == p['target'] or not any(x[3] != x[1] and x[3] != x[2] for x in ops[1:]):
                break
            pair.append({'problem_id': p['problem_id'], 'family': f, 'prefix': pref,
                         'reference_expression': expression(t), 'completed_steps': 1,
                         'remaining_steps': len(ops)-1, 'final_answer_disclosed': False,
                         'target_interface_completed': False})
        if len(pair) == 2:
            selected.extend(pair)
        if len(selected) == 64:
            break
    return selected


def distributions(problems):
    out = {'count': len(problems), 'target_bins': dict(Counter(str(p['target']//20*20) for p in problems)),
           'input_digits': dict(Counter(str(len(str(n))) for p in problems for n in p['numbers']))}
    for f in 'AB':
        paths = [p['paths'][f] for p in problems]
        out[f] = {'depth': dict(Counter(str(p['depth']) for p in paths)),
                  'structures': dict(Counter(p['structure_id'] for p in paths)),
                  'operators': dict(sum((Counter(p['operators']) for p in paths), Counter())),
                  'interfaces': dict(sum((Counter(p['interfaces']) for p in paths), Counter())),
                  'tokens': [p['supervised_tokens_v0'] for p in paths],
                  'identity_operations': dict(Counter(str(p['identity_operations']) for p in paths))}
    return out


def prepare(archive, tokenizer_dir, out, candidate_index=0):
    out = Path(out)
    if out.exists():
        raise FileExistsError('Never overwrite data release')
    started = time.monotonic(); ranking = census(archive)
    motif = ranking['candidate_motifs'][candidate_index]
    tokenizer, token_record = verified_tokenizer(Path(tokenizer_dir))
    groups = list(itertools.combinations(range(1, 41), 4))
    random.Random(SEEDS['data']).shuffle(groups)
    # Reconstruct historical split number-group hashes, without reading reserved question files.
    # Original pilot allocation is a published deterministic generator.
    from src.pilot_data import allocate_groups
    historical = json.loads(Path('runs/pilot_v1_20260908_r3/manifest.json').read_text())
    historical_groups = allocate_groups(historical['seed'],
        {'train': 4096, 'dev': 2048, 'holdout_reserved': 2048})
    excluded_hashes = {digest(list(g)) for gs in historical_groups.values() for g in gs}
    # Only identities are compared; no reserved group is solved, rendered or evaluated.
    train_blocks = json.loads(Path('runs/pilot_v1_20260908_r3/train_blocks.json').read_text())
    old_train = {tuple(sorted(p['problem']['numbers'])) for b in train_blocks for p in b['problems']}
    groups = [g for g in groups if digest(list(g)) not in excluded_hashes and g not in old_train]
    allocation = {'train': groups[:768], 'calibration': groups[768:912], 'discovery': groups[912:1200]}
    exclusions = []; selected = {}
    for split, candidates in allocation.items():
        want = {'train': 256, 'calibration': 16, 'discovery': 96}[split]
        rows = []
        for i, nums in enumerate(candidates):
            if len(rows) == want:
                exclusions.extend({'split': split, 'numbers': list(ns), 'reason': 'not_solved_after_prespecified_quota',
                                   'number_group_hash': digest(list(ns))} for ns in candidates[i:])
                break
            p = pair_from_solutions(list(nums), solve_all(list(nums)), motif, tokenizer)
            exclusions.append({'split': split, 'numbers': list(nums), 'number_group_hash': digest(list(nums)),
                               'reason': 'included' if p else 'no_supported_pair',
                               'target': p['target'] if p else None})
            if p:
                rows.append(p)
            if i % 32 == 0:
                print(json.dumps({'split': split, 'groups_solved': i+1, 'eligible': len(rows)}), flush=True)
        if len(rows) < want:
            if split == 'train' and len(rows) >= 128:
                rows = rows[:128]
                retained = {r['number_group_hash'] for r in rows}
                for e in exclusions:
                    if e['split'] == split and e['reason'] == 'included' and e['number_group_hash'] not in retained:
                        e['reason'] = 'unused_uniform_N128_fallback'
            else:
                raise ValueError(f'Finite {split} pool insufficient: {len(rows)}')
        selected[split] = rows
    sets = [{p['number_group_hash'] for p in ps} for ps in selected.values()]
    if any(a & b for a, b in itertools.combinations(sets, 2)):
        raise ValueError('Split overlap')
    arms, assignment = build_arms(selected['train']); exercises = exercise_sets(motif)
    dose = {}; n = len(selected['train'])
    schedules = {'main': epoch_schedule(2*n, 8, 16), 'prep': epoch_schedule(256, 2, 16)}
    all_train = {**arms, **{k: exercises[k] for k in ('prep_control', 'prep_bridge')}}
    for name, rows in all_train.items():
        encoded = [encode_row(r, tokenizer, 1024) for r in rows]
        schedule = schedules['prep' if name.startswith('prep') else 'main']
        dose[name] = budget_report(encoded, schedule, 1)
        dose[name]['max_training_sequence'] = max(r['n_processed'] for r in encoded)
    a, b = [dose[k]['supervised_response_tokens'] for k in ('surface', 'paths')]
    residual = abs(a-b)/min(a,b)
    prep_a, prep_b = [dose[k]['supervised_response_tokens'] for k in ('prep_control', 'prep_bridge')]
    audit = {'status': 'CPU_DATA_READY_NO_MODEL_RESULT', 'phase': 'C021', 'created_at_utc': stamp(),
        'target_motif': motif, 'control_motif': ranking['ranking'][candidate_index]['control_motif'],
        'candidate_index': candidate_index, 'candidate_ranking': ranking, 'seeds': SEEDS,
        'split_counts': {k: len(v) for k, v in selected.items()},
        'number_groups_disjoint': True, 'old_training_groups_excluded': len(old_train),
        'historical_reserved_question_contents_read': False,
        'historical_allocation_group_hashes_excluded': len(excluded_hashes),
        'historical_reserved_group_overlap': 0,
        'distributions': {k: distributions(v) for k,v in selected.items()},
        'dose': dose, 'main_token_residual_fraction': residual,
        'prep_token_residual_fraction': abs(prep_a-prep_b)/min(prep_a,prep_b),
        'budget_label': 'close' if residual <= .02 else 'approximate' if residual <= .05 else 'feasibility_only',
        'matching_limits': 'Global A/B and style match; finer program/interface/operator distributions are audited, not assumed equal.',
        'prefix_questions': len(prefixes(selected['discovery']))//2,
        'wall_seconds': time.monotonic()-started, 'new_model_calls': 0}
    out.mkdir(parents=True)
    for name, rows in selected.items():
        jsonl(out/(name+'_problems.jsonl'), rows)
    for name, rows in all_train.items():
        jsonl(out/(name+'.jsonl'), rows)
    jsonl(out/'probes.jsonl', exercises['probes'])
    jsonl(out/'calibration.jsonl', selected['calibration']+exercises['calibration_target']+exercises['calibration_control'])
    jsonl(out/'prefixes.jsonl', prefixes(selected['discovery']))
    dump(out/'assignment.json', assignment); dump(out/'schedules.json', schedules)
    dump(out/'learning_rates.json', {k: learning_rates(len(s)) for k,s in schedules.items()})
    dump(out/'DATA_AUDIT.json', audit)
    with (out/'DATA_EXCLUSIONS.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['split','numbers','number_group_hash','reason','target'])
        w.writeheader(); w.writerows(exclusions)
    dump(out/'manifest.json', {'phase': 'C021', 'created_at_utc': stamp(), 'tokenizer': token_record,
        'source_commit': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
        'files_sha256': {p.name: sha256_file(p) for p in out.iterdir() if p.is_file()},
        'source_files_sha256': {str(p): sha256_file(p) for p in (ROOT/'data.py', ROOT/'common.py', ROOT/'PROTOCOL_v1.md')}})
    return {k: audit[k] for k in ('status','target_motif','split_counts','main_token_residual_fraction','prep_token_residual_fraction','prefix_questions','wall_seconds')}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--archive', required=True); p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--out', required=True); p.add_argument('--candidate-index', type=int, choices=range(3), default=0)
    a = p.parse_args()
    print(json.dumps(prepare(a.archive, a.tokenizer_dir, a.out, a.candidate_index), indent=2))
