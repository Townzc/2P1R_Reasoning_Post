"""Bounded CPU census of all ordered programs for the fixed pilot training pool.

This is a legal-solution/AC-class support census, not the tokenizer, numerical
matching, or semantic-strategy validation proposed for a later intervention.
The CLI reads only the original 256 training problems and their fixed targets.
It never calls solve_all, reads development/holdout files, or runs a model.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import itertools
import json
import multiprocessing
from pathlib import Path
import subprocess
import time

from scripts.audit_pilot_structure_bias import identity_operations
from src.countdown_smoke import canonical, expression, safe_parse, value, verify_expression


TRAIN_BLOCKS = Path('runs/pilot_v1_20260908_r3/train_blocks.json')
TRAIN_SHA256 = 'e15857122ad9148a1a209cce7c8ef4c107ff0de27bcfe11b97ba6fce6b7a2cea'
SOURCES = (TRAIN_BLOCKS, Path('scripts/audit_legal_support.py'),
           Path('scripts/audit_pilot_structure_bias.py'), Path('src/countdown_smoke.py'),
           Path('docs/experiments/P002_legal_support_enumeration_design.md'),
           Path('docs/experiments/C008_complete_ordered_support_census.md'))
FAMILIES = ('identity_present', 'identity_absent')
SCOPE = [
    'Only the fixed 256 original pilot training problems and targets are enumerated.',
    'All 24 input permutations, 5 ordered full binary shapes and 64 operator assignments are examined: 7680 ordered programs per problem.',
    'Fractions are exact; undefined divisions are counted and excluded. Negative and fractional intermediates remain allowed.',
    'Identity is a numerical-trajectory property, not a semantic-strategy label. It includes evaluated intermediate ones and zeros under the existing declared convention.',
    'AC classes use concrete input values and flatten/sort only associative-commutative addition and multiplication. Identity labels are computed BEFORE any AC grouping.',
    'The same AC class can contain both identity-present and identity-absent ordered programs; distinct-class allocations cannot count that class twice.',
    'This is only the full ordered-solution/support census portion of P002. Tokenizer, matched dose, numerical-property matching, difficulty control and the broader semantic taxonomy are not implemented or tested here.',
    'Training-pool outcomes from earlier model runs motivated this census. No new evaluation outcomes, development data, holdout files or model inference are read.',
    'A timeout or failure retains only explicitly completed problem records. Partial denominators must not be reported as a completed 256-problem census.',
]


def json_bytes(record):
    return (json.dumps(record, sort_keys=True, separators=(',', ':')) + '\n').encode()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def ordered_programs(numbers):
    """Yield each ordered four-distinct-input binary program exactly once."""
    if (len(numbers) != 4 or len(set(numbers)) != 4
            or any(type(n) is not int or not 0 <= n <= 10000 for n in numbers)):
        raise ValueError('Four distinct nonnegative integer inputs required')
    for permutation in itertools.permutations(numbers):
        a, b, c, d = (('n', n) for n in permutation)
        for x, y, z in itertools.product(('+', '-', '*', '/'), repeat=3):
            # Operators occupy the three inorder gaps, in each of five shapes.
            yield (z, (y, (x, a, b), c), d)
            yield (z, (x, a, (y, b, c)), d)
            yield (y, (x, a, b), (z, c, d))
            yield (x, a, (z, (y, b, c), d))
            yield (x, a, (y, b, (z, c, d)))


def allocate_distinct_classes(identity_classes, nonidentity_classes, per_family):
    """Find an actual disjoint family/class assignment, using augmenting paths.

    Family counts alone are insufficient when the candidate sets overlap.
    Return class IDs by family, or None if no 2*k-distinct-class matching exists.
    """
    if type(per_family) is not int or per_family < 1:
        raise ValueError('Positive integer family size required')
    candidates = {FAMILIES[0]: sorted(set(identity_classes)),
                  FAMILIES[1]: sorted(set(nonidentity_classes))}
    slots = [(family, i) for family in FAMILIES for i in range(per_family)]
    owner = {}

    def augment(slot, seen):
        for class_id in candidates[slot[0]]:
            if class_id in seen:
                continue
            seen.add(class_id)
            if class_id not in owner or augment(owner[class_id], seen):
                owner[class_id] = slot
                return True
        return False

    for slot in slots:
        if not augment(slot, set()):
            return None
    result = {family: sorted(c for c, slot in owner.items() if slot[0] == family)
              for family in FAMILIES}
    assert all(len(classes) == per_family for classes in result.values())
    assert len(set(result[FAMILIES[0]]) | set(result[FAMILIES[1]])) == 2 * per_family
    return result


def load_training_problems(repo):
    source = Path(repo) / TRAIN_BLOCKS
    if sha256_file(source) != TRAIN_SHA256:
        raise ValueError('Original frozen training-block bytes changed')
    blocks = json.loads(source.read_text())
    if len(blocks) != 64:
        raise ValueError('Expected exactly 64 original training blocks')
    problems = []
    for block_id, block in enumerate(blocks):
        if len(block['problems']) != 4 or len(set(block['structures'])) != 4:
            raise ValueError('Expected four problems and structures per training block')
        for item in block['problems']:
            problem, paths = item['problem'], item['paths']
            if [p['structure_id'] for p in paths] != block['structures']:
                raise ValueError('Stored paths differ from the training block')
            if len({p['path_id'] for p in paths}) != 4:
                raise ValueError('Stored four paths must have distinct AC class IDs')
            if any(any(p[k] != problem[k] for k in ('problem_id', 'numbers', 'target')) for p in paths):
                raise ValueError('Stored path has wrong problem inputs or target')
            problems.append({**{k: problem[k] for k in ('problem_id', 'numbers', 'target')},
                             'block_id': block_id, 'stored_paths': paths})
    if len(problems) != 256 or len({p['problem_id'] for p in problems}) != 256:
        raise ValueError('Expected 256 unique original training problems')
    return sorted(problems, key=lambda p: p['problem_id'])


def audit_problem(problem, retain_solutions=False):
    """Enumerate one problem; no pre-enumeration AC canonicalization or pruning."""
    started = time.monotonic()
    numbers, target = problem['numbers'], problem['target']
    if type(target) is not int:
        raise ValueError('Exact integer target required')
    stored = []
    for row in problem['stored_paths']:
        tree = safe_parse(row['expression'])
        if not verify_expression(row['expression'], numbers, target) or canonical(tree) != row['path_id']:
            raise ValueError('Invalid stored reference or stored AC identity')
        stored.append({'tree': tree, 'path_id': row['path_id'],
                       'expression': expression(tree), 'recovered': False,
                       'identity_family': FAMILIES[0] if identity_operations(tree)[1] else FAMILIES[1]})
    stored_trees = {r['tree'] for r in stored}
    stored_classes = {r['path_id'] for r in stored}
    classes = {family: set() for family in FAMILIES}
    representatives = {}
    ordered_counts, identity_positions = Counter(), Counter()
    attempts = undefined = legal = 0
    stream_hash = hashlib.sha256()
    solutions = [] if retain_solutions else None
    ordered_stored_matches = ac_stored_matches = 0
    for tree in ordered_programs(numbers):
        attempts += 1
        try:
            result = value(tree)
        except ZeroDivisionError:
            undefined += 1
            continue
        if result != target:
            continue
        text = expression(tree)
        # Independent parsing/resource check even though construction uses inputs once.
        if not verify_expression(text, numbers, target):
            raise ValueError('Enumerated solution failed independent input/target verification')
        exact_value, identities = identity_operations(tree)
        if exact_value != target:
            raise ValueError('Identity walker disagrees on exact solution value')
        class_id = canonical(tree)
        family = FAMILIES[0] if identities else FAMILIES[1]
        ordered_counts[family] += 1
        classes[family].add(class_id)
        identity_positions.update(event['node_address'] for event in identities)
        matches_ordered = tree in stored_trees
        matches_class = class_id in stored_classes
        ordered_stored_matches += matches_ordered
        ac_stored_matches += matches_class
        feature = {'problem_id': problem['problem_id'], 'numbers': numbers, 'target': target,
                   'expression': text, 'ac_class': class_id,
                   'canonical_structure': canonical(tree, structure_only=True),
                   'identity_family': family, 'identity_operations': identities,
                   'matches_stored_ordered_expression': matches_ordered,
                   'matches_stored_ac_path': matches_class}
        stream_hash.update(json_bytes(feature))
        if retain_solutions:
            solutions.append(feature)
        representatives.setdefault((class_id, family), feature)
        if matches_ordered:
            for row in stored:
                if row['tree'] == tree:
                    row['recovered'] = True
        legal += 1
    if attempts != 7680 or not all(row['recovered'] for row in stored):
        raise ValueError('Enumeration incomplete or failed to recover a stored ordered reference')

    def witness(k):
        allocation = allocate_distinct_classes(classes[FAMILIES[0]], classes[FAMILIES[1]], k)
        if allocation is None:
            return None
        return {'ac_class_allocation': allocation,
                'ordered_solution_witnesses': [representatives[c, family]
                                              for family in FAMILIES for c in allocation[family]]}

    two = witness(2)
    four = witness(4)
    mixed = sorted(classes[FAMILIES[0]] & classes[FAMILIES[1]])
    summary = {
        'problem_id': problem['problem_id'], 'block_id': problem.get('block_id'),
        'numbers': numbers, 'target': target, 'status': 'completed',
        'ordered_candidates_examined': attempts, 'undefined_division_programs': undefined,
        'defined_programs': attempts - undefined, 'wrong_target_programs': attempts - undefined - legal,
        'legal_ordered_solutions': legal,
        'ordered_solution_counts': {f: ordered_counts[f] for f in FAMILIES},
        'distinct_ac_class_counts': {f: len(classes[f]) for f in FAMILIES},
        'distinct_ac_classes_union': len(classes[FAMILIES[0]] | classes[FAMILIES[1]]),
        'mixed_ac_class_count': len(mixed),
        'identity_node_address_histogram': dict(sorted(identity_positions.items())),
        'ordered_two_plus_two_supported': all(ordered_counts[f] >= 2 for f in FAMILIES),
        'ordered_four_plus_four_supported': all(ordered_counts[f] >= 4 for f in FAMILIES),
        'distinct_ac_two_plus_two_supported': two is not None,
        'each_family_has_four_ac_classes_allowing_overlap': all(len(classes[f]) >= 4 for f in FAMILIES),
        'distinct_ac_four_plus_four_supported': four is not None,
        'two_plus_two_witness': two, 'four_plus_four_witness': four,
        'mixed_ac_examples': [{'ac_class': c,
                               'ordered_solution_witnesses': [representatives[c, f] for f in FAMILIES]}
                              for c in mixed[:2]],
        'stored_ordered_references': [{k: v for k, v in row.items() if k != 'tree'} for row in stored],
        'stored_reference_family_counts': {f: sum(r['identity_family'] == f for r in stored) for f in FAMILIES},
        'stored_ordered_solution_matches': ordered_stored_matches,
        'solutions_matching_any_stored_ac_path': ac_stored_matches,
        'all_stored_ordered_references_recovered': all(row['recovered'] for row in stored),
        'complete_solution_feature_stream_sha256': stream_hash.hexdigest(),
        'elapsed_seconds': time.monotonic() - started,
    }
    return summary, solutions


def aggregate_completed(records):
    flags = ('ordered_two_plus_two_supported', 'ordered_four_plus_four_supported', 'distinct_ac_two_plus_two_supported',
             'each_family_has_four_ac_classes_allowing_overlap', 'distinct_ac_four_plus_four_supported')
    return {'completed_problems': len(records),
            'support_problem_counts': {flag: sum(r[flag] for r in records) for flag in flags},
            'problems_with_mixed_ac_class': sum(r['mixed_ac_class_count'] > 0 for r in records),
            'mixed_ac_classes_total': sum(r['mixed_ac_class_count'] for r in records),
            'ordered_candidates_examined': sum(r['ordered_candidates_examined'] for r in records),
            'undefined_division_programs': sum(r['undefined_division_programs'] for r in records),
            'wrong_target_programs': sum(r['wrong_target_programs'] for r in records),
            'legal_ordered_solutions': sum(r['legal_ordered_solutions'] for r in records),
            'all_completed_stored_references_recovered': all(r['all_stored_ordered_references_recovered'] for r in records) if records else None}


def create_output(out):
    """An existing output directory is immutable, including incomplete attempts."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    return out


def write_summary(out, record):
    # Only the new attempt owns this file; completed directories cannot be reused.
    temporary = Path(out) / 'summary.json.tmp'
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    temporary.replace(Path(out) / 'summary.json')


def run_audit(repo, out, workers=2, max_seconds=600, solutions_out=None):
    if type(workers) is not int or workers not in (1, 2):
        raise ValueError('Use one or two CPU workers')
    if not 0 < max_seconds <= 600:
        raise ValueError('CPU enumeration deadline must be between zero and 600 seconds')
    if solutions_out is not None:
        solutions_out = Path(solutions_out)
        if solutions_out.exists():
            raise FileExistsError('Private solution archive already exists')
        if not str(solutions_out).endswith('.jsonl.gz'):
            raise ValueError('Use a new .jsonl.gz archive path')
    out = create_output(out)
    started = time.monotonic()
    deadline = started + max_seconds
    result = {'status': 'running', 'created_utc': datetime.now(timezone.utc).isoformat(),
              'scope': SCOPE, 'workers': workers, 'maximum_seconds': max_seconds,
              'requested_problems': 256, 'sources_sha256': {},
              'private_solution_archive_requested': solutions_out is not None,
              'solution_archive_records': 0, 'completed': aggregate_completed([])}
    write_summary(out, result)
    records, pending, pool, archive = [], [], None, None
    all_solution_hash = hashlib.sha256()
    try:
        result['sources_sha256'] = {str(p): sha256_file(Path(repo) / p) for p in SOURCES}
        problems = load_training_problems(repo)
        result['execution_source_commit'] = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
        result['tracked_worktree_dirty_at_start'] = bool(subprocess.check_output(
            ['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repo, text=True).strip())
        pending = [p['problem_id'] for p in problems]
        if solutions_out is not None:
            solutions_out.parent.mkdir(parents=True, exist_ok=True)
            archive = gzip.open(solutions_out, 'xb')
        pool = multiprocessing.get_context('spawn').Pool(processes=workers)
        jobs = [pool.apply_async(audit_problem, (p, archive is not None)) for p in problems]
        pool.close()
        with (out / 'per_problem.jsonl').open('xb') as output:
            for job in jobs:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise multiprocessing.TimeoutError()
                record, solutions = job.get(timeout=remaining)
                output.write(json_bytes(record))
                output.flush()
                records.append(record)
                pending.pop(0)
                if solutions is not None:
                    for solution in solutions:
                        raw = json_bytes(solution)
                        archive.write(raw)
                        all_solution_hash.update(raw)
                        result['solution_archive_records'] += 1
                result['completed'] = aggregate_completed(records)
                result['pending_problem_ids'] = list(pending)
                result['elapsed_seconds'] = time.monotonic() - started
                write_summary(out, result)
                print(json.dumps({'completed_problems': len(records), 'requested_problems': 256,
                                  'elapsed_seconds': result['elapsed_seconds']}), flush=True)
        pool.join()
        pool = None
        if time.monotonic() > deadline:
            raise multiprocessing.TimeoutError()
        result['status'] = 'completed'
    except multiprocessing.TimeoutError:
        result['status'] = 'timed_out'
        result['failure'] = {'type': 'TimeoutError', 'message': 'CPU census deadline exceeded; only completed records are usable.'}
    except (Exception, KeyboardInterrupt) as exc:
        result['status'] = 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed'
        message = f'Filesystem error {exc.errno}: {exc.strerror}' if isinstance(exc, OSError) else str(exc)
        for path, label in ((Path(repo), '<repository>'), (out, '<report-directory>')):
            message = message.replace(str(path.resolve()), label).replace(str(path.absolute()), label)
        if solutions_out is not None:
            message = message.replace(str(solutions_out.resolve()), '<private-solution-archive>')
        result['failure'] = {'type': type(exc).__name__, 'message': message,
                             'next_uncollected_problem_id': pending[0] if pending else None}
    finally:
        if pool is not None:
            pool.terminate()
            pool.join()
        if archive is not None:
            try:
                archive.close()
                result['solution_archive_uncompressed_sha256'] = all_solution_hash.hexdigest()
                result['solution_archive_gzip_sha256'] = sha256_file(solutions_out)
            except OSError:
                result['status'] = 'failed'
                result['failure'] = {'type': 'ArchiveWriteFailed', 'message': 'Private solution archive did not finalize; retain compact completed records only.'}
        result['completed'] = aggregate_completed(records)
        result['pending_problem_ids'] = pending
        result['elapsed_seconds'] = time.monotonic() - started
        try:
            unchanged = all(sha256_file(Path(repo) / p) == digest for p, digest in result['sources_sha256'].items())
            result['source_files_unchanged'] = unchanged if result['sources_sha256'] else None
            if not unchanged:
                result['status'] = 'failed'
                result['failure'] = {'type': 'SourceChanged', 'message': 'Input or computation source changed during census.'}
        except OSError:
            result['status'] = 'failed'
            result['source_files_unchanged'] = False
            result['failure'] = {'type': 'SourceUnavailable', 'message': 'A recorded source was unavailable at final verification.'}
        if (out / 'per_problem.jsonl').exists():
            result['per_problem_sha256'] = sha256_file(out / 'per_problem.jsonl')
        write_summary(out, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='New compact report directory; never overwritten')
    parser.add_argument('--workers', type=int, choices=(1, 2), default=2)
    parser.add_argument('--max-seconds', type=float, default=600)
    parser.add_argument('--solutions-out', type=Path,
                        help='Optional new private .jsonl.gz file containing every legal ordered solution; its path is not written to public reports')
    args = parser.parse_args()
    result = run_audit(Path('.'), args.out, args.workers, args.max_seconds, args.solutions_out)
    print(json.dumps({'status': result['status'], 'completed': result['completed'],
                      'elapsed_seconds': result['elapsed_seconds']}), flush=True)
    raise SystemExit(0 if result['status'] == 'completed' else 2)


if __name__ == '__main__':
    main()
