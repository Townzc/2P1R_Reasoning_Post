"""CPU-only feasibility harness, NOT a completed scientific benchmark.

Enumerates 4-number arithmetic programs exactly using rational arithmetic.
AC canonicalization removes associative/commutative +/* variants only.
It does not establish semantic equivalence or identify human reasoning skills.
No network calls, model downloads, GPU training, or arbitrary eval are used.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import random
import statistics
import time
import math
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

Expr = tuple

def canonical(expr: Expr, *, structure_only: bool = False) -> str:
    if expr[0] == 'n':
        return 'N' if structure_only else str(expr[1])
    op, left, right = expr
    if op in ('+', '*'):
        def flatten(node: Expr) -> list[str]:
            if node[0] == op:
                return flatten(node[1]) + flatten(node[2])
            return [canonical(node, structure_only=structure_only)]
        return op + '(' + ','.join(sorted(flatten(left) + flatten(right))) + ')'
    return op + '(' + canonical(left, structure_only=structure_only) + ',' + canonical(right, structure_only=structure_only) + ')'

def format_fraction(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f'{x.numerator}/{x.denominator}'

def value(expr: Expr) -> Fraction:
    if expr[0] == 'n':
        return Fraction(expr[1])
    op, a, b = expr
    x, y = value(a), value(b)
    if op == '+': return x+y
    if op == '-': return x-y
    if op == '*': return x*y
    if op == '/': return x/y
    raise ValueError('Invalid operator')

def expression(expr: Expr) -> str:
    if expr[0] == 'n': return str(expr[1])
    return f'({expression(expr[1])} {expr[0]} {expression(expr[2])})'

def safe_parse(text: str) -> Expr:
    if len(text) > 2048: raise ValueError('Expression too long')
    root = ast.parse(text.strip(), mode='eval')
    operators = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*', ast.Div: '/'}
    def visit(node: ast.AST, depth: int = 0) -> Expr:
        if depth > 32: raise ValueError('Expression too deep')
        if isinstance(node, ast.Constant) and type(node.value) is int and 0 <= node.value <= 10000:
            return ('n', node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            return (operators[type(node.op)], visit(node.left, depth+1), visit(node.right, depth+1))
        raise ValueError('Only integer literals and + - * / binary operators are permitted')
    return visit(root.body)

def verify_expression(text: str, numbers: list[int], target: int) -> bool:
    try:
        tree = safe_parse(text)
        def leaves(node: Expr) -> list[int]:
            return [node[1]] if node[0] == 'n' else leaves(node[1]) + leaves(node[2])
        return Counter(leaves(tree)) == Counter(numbers) and value(tree) == target
    except (ValueError, SyntaxError, ZeroDivisionError, RecursionError):
        return False

def solve_all(numbers: list[int]) -> dict[int, list[Expr]]:
    if len(numbers) != 4: raise ValueError('The smoke solver supports exactly four numbers')
    dp: dict[int, dict[str, tuple[Fraction, Expr]]] = {}
    for i, n in enumerate(numbers):
        tree = ('n', n)
        dp[1 << i] = {canonical(tree): (Fraction(n), tree)}
    for size in range(2, 5):
        for mask in range(1, 16):
            if mask.bit_count() != size: continue
            found: dict[str, tuple[Fraction, Expr]] = {}
            sub = (mask-1) & mask
            while sub:
                other = mask ^ sub
                if other and sub < other:
                    for x, a in dp[sub].values():
                        for y, b in dp[other].values():
                            choices = [('+', a, b, x+y), ('*', a, b, x*y), ('-', a, b, x-y), ('-', b, a, y-x)]
                            if y: choices.append(('/', a, b, x/y))
                            if x: choices.append(('/', b, a, y/x))
                            for op, left, right, v in choices:
                                tree = (op, left, right)
                                found.setdefault(canonical(tree), (v, tree))
                sub = (sub-1) & mask
            dp[mask] = found
    out: dict[int, list[Expr]] = defaultdict(list)
    for v, tree in dp[15].values():
        if v.denominator == 1 and 10 <= v <= 100:
            out[int(v)].append(tree)
    return dict(out)

def render_trace(tree: Expr, variant: int = 0) -> str:
    steps: list[str] = []
    def walk(node: Expr) -> Fraction:
        if node[0] == 'n': return Fraction(node[1])
        x, y = walk(node[1]), walk(node[2])
        z = value(node)
        def operand(v: Fraction) -> str:
            text = format_fraction(v)
            return f'({text})' if v.denominator != 1 or v < 0 else text
        eq = f'{operand(x)} {node[0]} {operand(y)} = {format_fraction(z)}'
        frames = [f'Step {len(steps)+1}: {eq}.', f'Compute {eq}.', f'The next calculation is {eq}.', f'We obtain {eq}.']
        steps.append(frames[variant])
        return z
    walk(tree)
    return '\n'.join(steps + ['Answer: ' + expression(tree)])

def make_pool(count: int, seed: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not 0 < count <= math.comb(20, 4):
        raise ValueError('The 1..20 unique-number domain contains at most 4845 groups, before eligibility filtering')
    rng = random.Random(seed)
    pool: list[dict[str, Any]] = []
    seen_multisets: set[tuple[int, ...]] = set()
    attempts = 0
    while len(pool) < count:
        attempts += 1
        if attempts > count*100: raise RuntimeError('Insufficient eligible problems; inspect eligibility rather than silently changing it')
        nums = tuple(sorted(rng.sample(range(1, 21), 4)))
        if nums in seen_multisets: continue
        seen_multisets.add(nums)
        answers = solve_all(list(nums))
        eligible = []
        for target, trees in answers.items():
            by_structure: dict[str, list[Expr]] = defaultdict(list)
            for tree in trees: by_structure[canonical(tree, structure_only=True)].append(tree)
            if len(by_structure) >= 4: eligible.append((target, by_structure))
        if not eligible: continue
        target, groups = rng.choice(eligible)
        structures = sorted(groups)
        rng.shuffle(structures)
        selected = [rng.choice(groups[s]) for s in structures[:4]]
        key = json.dumps([nums, target], separators=(',', ':'))
        pool.append({'problem_id': hashlib.sha256(key.encode()).hexdigest()[:20], 'numbers': list(nums), 'target': target,
                     'prompt': f'Use the numbers {", ".join(map(str, nums))} exactly once each with +, -, *, / and parentheses to make {target}. Show calculations, then write Answer: followed by one expression.',
                     'paths': [{'path_id': canonical(t), 'structure_id': canonical(t, structure_only=True), 'program': t, 'expression': expression(t)} for t in selected],
                     'eligible_structure_count': len(groups)})
    return pool, {'candidate_multisets_seen': len(seen_multisets), 'sampling_attempts': attempts, 'eligible_problems': len(pool)}

def make_arms(train: list[dict[str, Any]], seed: int) -> dict[str, list[dict[str, Any]]]:
    if len(train) % 4: raise ValueError('train count must be divisible by four')
    small = train[:len(train)//4]
    specs = {'repeat': (small, 1, 4, False), 'paths': (small, 4, 1, False), 'surface': (small, 1, 4, True), 'balanced': (small, 2, 2, False), 'breadth': (train, 1, 1, False)}
    arms = {}
    for name, (problems, paths, reps, surface) in specs.items():
        rows = []
        for p in problems:
            for j in range(paths):
                path = p['paths'][j]
                for r in range(reps):
                    rows.append({'problem_id': p['problem_id'], 'prompt': p['prompt'], 'response': render_trace(path['program'], r if surface else 0),
                                 'path_id': path['path_id'], 'structure_id': path['structure_id'], 'render_id': r if surface else 0,
                                 'exposure_index': 1 if surface else r+1, 'numbers': p['numbers'], 'target': p['target'], 'expression': path['expression']})
        random.Random(seed).shuffle(rows)
        arms[name] = rows
    return arms

def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open('w', encoding='utf-8') as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False) + '\n')

def build(out: Path, n_train: int, n_dev: int, n_test: int, seed: int) -> dict[str, Any]:
    if n_train <= 0 or n_dev <= 0 or n_test <= 0: raise ValueError('All split sizes must be positive')
    if out.exists(): raise FileExistsError('Refusing to overwrite an existing dataset directory; choose a new output directory')
    if n_train % 4: raise ValueError('train count must be divisible by four')
    if n_train+n_dev+n_test > math.comb(20, 4): raise ValueError('Requested groups exceed the finite 1..20 domain')
    out.mkdir(parents=True)
    start = time.perf_counter()
    pool, generation = make_pool(n_train+n_dev+n_test, seed)
    train, dev, test = pool[:n_train], pool[n_train:n_train+n_dev], pool[n_train+n_dev:]
    for name, rows in [('train_pool', train), ('dev', dev), ('test_iid', test)]: write_jsonl(out/f'{name}.jsonl', rows)
    arms = make_arms(train, seed+1)
    stats = {}
    for name, rows in arms.items():
        write_jsonl(out/f'arm_{name}.jsonl', rows)
        stats[name] = {'presentations': len(rows), 'unique_problems': len({r['problem_id'] for r in rows}),
                       'unique_problem_path_pairs': len({(r['problem_id'], r['path_id']) for r in rows}),
                       'unique_problem_response_pairs': len({(r['problem_id'], r['response']) for r in rows}),
                       'mean_response_characters': round(statistics.mean(len(r['response']) for r in rows), 2),
                       'valid_expressions': sum(verify_expression(r['expression'], r['numbers'], r['target']) for r in rows)}
    split_sets = [set(tuple(x['numbers']) for x in s) for s in (train, dev, test)]
    no_overlap = not any(split_sets[i] & split_sets[j] for i in range(3) for j in range(i+1, 3))
    all_paths = [path for p in pool for path in p['paths']]
    all_verified = all(verify_expression(path['expression'], p['numbers'], p['target']) for p in pool for path in p['paths'])
    distinct4 = all(len({p['structure_id'] for p in item['paths']}) == 4 for item in pool)
    audit = {'status': 'CPU_DATA_FEASIBILITY_ONLY', 'seed': seed, 'generation': generation,
             'split_counts': {'train_pool': n_train, 'dev': n_dev, 'test_iid': n_test},
             'selected_program_count': len(all_paths), 'all_programs_independently_ast_verified': all_verified,
             'four_distinct_ac_structure_signatures_per_problem': distinct4,
             'number_multiset_disjoint_splits': no_overlap, 'arms': stats,
             'elapsed_seconds': round(time.perf_counter()-start, 3),
             'not_yet_implemented': ['model-token budget matching', 'GPU training or inference', 'held-out composition split', 'global program-distribution matching', 'real mathematics validation', 'step-trace evaluation for model-generated output'],
             'limitations': ['Selected problems require at least four syntactic program structures; selection bias must be measured.', 'Only +/* associativity and commutativity are canonicalized; algebraic equivalence and cognitive strategy are NOT established.', 'All five arms match presentation counts ONLY, not BPE tokens or FLOPs.', 'New numerical instances are not a guarantee of absence from model pretraining data.', 'Four distinct input numbers and targets 10..100 define a limited task domain.']}
    assert no_overlap and all_verified and distinct4
    (out/'audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding='utf-8')
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.jsonl')}
    (out/'sha256.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return audit

if __name__ == '__main__':
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--out', type=Path, required=True)
    a.add_argument('--train', type=int, default=128)
    a.add_argument('--dev', type=int, default=16)
    a.add_argument('--test', type=int, default=32)
    a.add_argument('--seed', type=int, default=20260904)
    x = a.parse_args()
    print(json.dumps(build(x.out, x.train, x.dev, x.test, x.seed), indent=2, ensure_ascii=False))
