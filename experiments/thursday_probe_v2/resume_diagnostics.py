"""CPU-only frozen training diagnostics and supplemental construction audits.

This module neither runs models nor changes the frozen primary scorer. Its
sixteen training questions are a descriptive diagnostic, not held-out evidence.
Unknown arithmetic/trace evidence is represented by None and the status "NA".
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
import re

from experiments.thursday_probe.common import (
    SEEDS, digest, dump, jsonl, response, stamp, verify_manifest)
from experiments.thursday_probe_v2.config import DATA, RELEASE, ROOT
from src.countdown_smoke import canonical, safe_parse, verify_expression
from src.sft_data import read_jsonl, sha256_file
from src.trace_audit import audit_trace, exact_value, parse_expression


RESUME_RELEASE = ROOT / 'release_resume_r1'
SELECTION_PURPOSE = 'post_e030_train_diagnostic_v1'
STRATA = tuple((anchor, label) for anchor in ('A', 'B')
               for label in ('target_degenerate', 'target_nondegenerate'))


def select_training_questions(problems, assignment, labels, *, seed=SEEDS['assignment']):
    """Choose four per anchor × B-target stratum; fill shortages by sorted ID.

    Degeneracy always refers to the existing B reference's target interface:
    A references have no such edge, so their absence is not nondegeneracy.
    """
    by_id = {r['problem_id']: r for r in problems}
    if len(by_id) != len(problems) or len(by_id) < 16:
        raise ValueError('Need at least sixteen distinct training questions')
    if set(assignment) != set(by_id) or set(assignment.values()) - {'A', 'B'}:
        raise ValueError('Assignment must cover the exact common training pool')
    train_labels = [r for r in labels if r['split'] == 'train']
    by_label = {(r['problem_id'], r['family']): r for r in train_labels}
    if len(by_label) != len(train_labels) or set(by_label) != {
            (pid, family) for pid in by_id for family in ('A', 'B')}:
        raise ValueError('Need both frozen reference labels for each training question')
    groups = {stratum: [] for stratum in STRATA}
    strata_by_id = {}
    for pid, problem in by_id.items():
        if problem['task'] != 'construct' or set(problem['paths']) != {'A', 'B'}:
            raise ValueError('Expected unchanged two-reference construction problems')
        a, b = by_label[pid, 'A'], by_label[pid, 'B']
        if (a['target_present'] or not b['target_present'] or
                b['identity_at_target'] == b['target_nondegenerate']):
            raise ValueError('Frozen target-label partition is invalid')
        for family, label in (('A', a), ('B', b)):
            if label['expression'] != problem['paths'][family]['expression']:
                raise ValueError('Frozen reference expression and label differ')
        label = 'target_degenerate' if b['identity_at_target'] else 'target_nondegenerate'
        stratum = assignment[pid], label
        groups[stratum].append(pid)
        strata_by_id[pid] = stratum
    selected, strata = [], []
    for anchor, label in STRATA:
        candidates = sorted(groups[anchor, label], key=lambda pid: (
            digest([SELECTION_PURPOSE + '/' + anchor + '/' + label, seed, pid]), pid))
        chosen = candidates[:4]
        selected.extend(chosen)
        strata.append(dict(anchor_family=anchor, target_label=label,
                           support=len(candidates), requested=4,
                           initial_selected_ids=chosen, shortage=max(0, 4-len(chosen))))
    selected_set = set(selected)
    fallback = sorted(set(by_id) - selected_set)[:16-len(selected)]
    selected.extend(fallback)
    for group in strata:
        key = group['anchor_family'], group['target_label']
        group['final_selected_ids'] = [pid for pid in selected if strata_by_id[pid] == key]
        group['final_selected_count'] = len(group['final_selected_ids'])
    rows = []
    for pid in selected:
        anchor, label = strata_by_id[pid]
        rows.append(dict(by_id[pid], diagnostic_anchor_family=anchor,
                         diagnostic_target_label=label))
    return rows, dict(
        purpose=SELECTION_PURPOSE, assignment_seed=seed,
        algorithm='Four per stratum, ordered by SHA256 compact sorted-key JSON '
                  '[purpose/anchor/label, assignment_seed, problem_id], ID tie-break. '
                  'If a stratum has fewer than four, select its full support and '
                  'fill remaining places using lexicographically sorted unselected '
                  'problem IDs. Output preserves stratum order then fallback ID order.',
        strata_order=[list(s) for s in STRATA], strata=strata,
        target_label_basis='Existing family B target-edge labels, irrespective of anchor; '
                           'family A has no target edge and is not labeled nondegenerate.',
        population_questions=len(problems), selected_questions=16,
        fallback_selected_ids=fallback, selected_ids=selected,
        selected_ids_sha256=digest(selected), model_results_used=False,
        interpretation='Fixed small training diagnostic; accepts any legal correct program; '
                       'not whole-training accuracy, literal memorization, or unseen generalization.')


def _reference_rows(rows, family):
    references = []
    for problem in rows:
        path = problem['paths'][family]
        if not verify_expression(path['expression'], problem['numbers'], problem['target']):
            raise ValueError('Invalid frozen A/B reference')
        row = {k: v for k, v in problem.items() if k != 'paths'}
        row.update(path, coarse_path=family, rendering_id=0,
                   response=response(safe_parse(path['expression']), 0),
                   template_family=path['structure_id'])
        if audit_trace(row['response'], row['numbers'], row['target'])['complete_trace_status'] != 'verified':
            raise ValueError('Reference trace is not verified')
        references.append(row)
    return references


def prepare_release(output=RESUME_RELEASE, *, data=DATA, release=RELEASE):
    """Freeze the supplemental CPU artifacts once, without touching old releases."""
    output, data, release = Path(output), Path(data), Path(release)
    if output.exists():
        raise FileExistsError('Never overwrite a diagnostic release')
    upstream = verify_manifest(release)
    data_manifest = json.loads((data/'manifest.json').read_text())
    if sha256_file(data/'manifest.json') != upstream['old_manifest_sha256']:
        raise ValueError('Original data manifest differs from the frozen v2 release')
    # Read only the common training pool/assignment and their existing labels;
    # no reserved confirmation or test contents are opened.
    source_files = [data/'manifest.json', data/'train_problems.jsonl',
                    data/'assignment.json', release/'manifest.json',
                    release/'reference_identity_labels.jsonl', release/'registrations.json']
    for name in ('train_problems.jsonl', 'assignment.json'):
        if sha256_file(data/name) != data_manifest['files_sha256'][name]:
            raise ValueError('Original training artifact changed: ' + name)
    problems = read_jsonl(data/'train_problems.jsonl')
    if len(problems) != 256:
        raise ValueError('The unchanged common training pool must contain 256 questions')
    selected, selection = select_training_questions(
        problems, json.loads((data/'assignment.json').read_text()),
        read_jsonl(release/'reference_identity_labels.jsonl'))
    references = {family: _reference_rows(selected, family) for family in ('A', 'B')}
    registrations = json.loads((release/'registrations.json').read_text())['entries']
    endpoints = [r for r in registrations if r['updates'] == 256]
    if [r['state'] for r in endpoints] != ['C-S', 'C-P', 'B-S', 'B-P']:
        raise ValueError('Frozen main endpoint registrations changed')
    events = [dict(name=r['state']+'_train_diagnostic', state=r['state'],
                   experiment_id=r['experiment_id'], view='train_diagnostic',
                   checkpoint_step=256, questions=16, samples=1, sampling=False,
                   generations=16, batch_size=8, seed=SEEDS['evaluation'], max_new_tokens=512)
              for r in endpoints]
    output.mkdir(parents=True, exist_ok=False)
    jsonl(output/'train_diagnostic.jsonl', selected)
    for family in ('A', 'B'):
        jsonl(output/('reference_'+family+'.jsonl'), references[family])
    dump(output/'selection.json', selection)
    dump(output/'evaluation_queue.json', events)
    manifest = dict(
        created_at_utc=stamp(), status='frozen_cpu_only_before_main_training',
        source_files_sha256={str(p): sha256_file(p) for p in source_files},
        original_release_manifest_sha256=sha256_file(release/'manifest.json'),
        files_sha256={p.name: sha256_file(p) for p in sorted(output.iterdir())},
        selection_ids_sha256=selection['selected_ids_sha256'],
        selected_questions=16, endpoint_generations=64,
        generation_accounting=dict(historical_attempts=592, original_remaining=4128,
                                   additional_diagnostic=64, planned_new=4192,
                                   planned_cumulative=4784, unchanged_cap=4864,
                                   remaining_fault_reserve=80),
        reference_nll=dict(status='not_measured', references_per_family=16,
                           families=['A', 'B'], autoregressive_generations=0,
                           note='Optional bounded teacher-forced measurement must charge '
                                'actual runtime; reference availability is not a result.'),
        reserved_confirmation_or_test_contents_read=False,
        model_calls=0, training_modified=False, primary_scorer_modified=False)
    dump(output/'manifest.json', manifest)
    return manifest


def load_generation_rows(release=RESUME_RELEASE):
    """Read the sixteen fixed prompts in their frozen generation/batch order."""
    verify_manifest(release)
    return read_jsonl(Path(release)/'train_diagnostic.jsonl')


def load_reference_rows(family, release=RESUME_RELEASE):
    """Read sixteen canonical A or B responses for optional bounded NLL only."""
    if family not in ('A', 'B'):
        raise ValueError('Reference family must be A or B')
    verify_manifest(release)
    return read_jsonl(Path(release)/('reference_'+family+'.jsonl'))


def _leaves(tree):
    return [tree[1]] if tree[0] == 'n' else _leaves(tree[1]) + _leaves(tree[2])


def _status(flag):
    return 'NA' if flag is None else 'consistent' if flag else 'inconsistent'


def construction_error_breakdown(row, text, *, stop_reason=None, output_tokens=None):
    """Supplement the original score without changing it or its denominator.

    Explicit equations are audited independently of the target. Full trace
    status is retained as context and is never used as a local-arithmetic flag.
    A terminal expression whose value is undefined gets NA target satisfaction.
    """
    if row['task'] != 'construct':
        raise ValueError('Construction decomposition requires a construct task')
    matches = list(re.finditer(r'(?m)^\s*Answer:\s*([^\n]+)', text))
    result = dict(answer_extracted=len(matches) == 1, expression=None,
                  ast_syntax_valid=None, allowed_operations=None, parsed=False,
                  safely_executable=False, uses_input_multiset=None,
                  reaches_target=None, exact_value=None,
                  resource_target_category='unparseable', reason=None,
                  normalized_program_class=None, reference_program_class=None,
                  stop_reason=stop_reason, output_tokens=output_tokens,
                  completed=None if stop_reason is None else
                  stop_reason in ('native_eos', 'new_problem_boundary'))
    tree = None
    if len(matches) != 1:
        result['reason'] = 'answer_count_not_one'
    else:
        expression = matches[0][1].strip()
        result['expression'] = expression
        try:
            if len(expression) > 2048:
                raise ValueError('expression_too_long')
            ast.parse(expression, mode='eval')
            result['ast_syntax_valid'] = True
            tree = parse_expression(expression, final=True)
            result.update(allowed_operations=True, parsed=True,
                          uses_input_multiset=Counter(_leaves(tree)) == Counter(row['numbers']),
                          normalized_program_class=canonical(tree))
            result['reference_program_class'] = next(
                (f for f, p in row.get('paths', {}).items()
                 if p['path_id'] == result['normalized_program_class']), 'other')
            try:
                value = exact_value(tree)
                result.update(safely_executable=True, exact_value=str(value),
                              reaches_target=value == Fraction(row['target']))
            except ZeroDivisionError:
                result.update(reason='division_by_zero', resource_target_category='undefined_value')
            except (ValueError, RecursionError, OverflowError):
                result.update(reason='value_unverifiable', resource_target_category='undefined_value')
        except SyntaxError:
            result.update(ast_syntax_valid=False, reason='invalid_expression_syntax')
        except (ValueError, RecursionError, OverflowError):
            if result['ast_syntax_valid']:
                result['allowed_operations'] = False
            result['reason'] = 'unsupported_expression_or_bound'
    if result['safely_executable']:
        result['resource_target_category'] = {
            (True, True): 'both_satisfied', (True, False): 'resource_correct_target_wrong',
            (False, True): 'target_correct_resource_wrong', (False, False): 'both_wrong',
        }[result['uses_input_multiset'], result['reaches_target']]
    trace = audit_trace(text, row['numbers'], Fraction(row['target']))
    local = {'consistent': True, 'inconsistent': False}.get(trace['local_equations_status'])
    derivation = trace.get('derivation_values')
    trace_value = None if not derivation or result['exact_value'] is None else any(
        Fraction(v) == Fraction(result['exact_value']) for v in derivation)
    trace_target = None if not derivation else any(
        Fraction(v) == Fraction(row['target']) for v in derivation)
    connection = trace['answer_connection_status']
    trace_expression = (True if connection in ('exact_ordered_tree_match', 'ac_equivalent_only')
                        else False if trace_value is False else None)
    result.update(intermediate_arithmetic_consistent=local,
                  intermediate_arithmetic_status=_status(local),
                  explicit_equations=trace['equations'],
                  trace_final_value_consistent=trace_value,
                  trace_final_expression_consistent=trace_expression,
                  trace_target_consistent=trace_target,
                  trace_expression_connection=connection,
                  complete_trace_status=trace['complete_trace_status'],
                  trace_reasons=trace['reasons'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=RESUME_RELEASE)
    args = parser.parse_args()
    print(json.dumps(prepare_release(args.output), indent=2, sort_keys=True))
