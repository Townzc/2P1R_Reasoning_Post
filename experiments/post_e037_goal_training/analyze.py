"""CPU-only paired recipe analysis for Post-E037 goal training.

Frozen E037 mathematics/stop scoring is replayed unchanged. Statistical units
are new number groups; generated samples, target pairs and repeats are nested.
Training diagnostics and midpoint checks never select scientific endpoints.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import numpy as np
from experiments.post_e036_goal_probe import analyze as frozen
from experiments.post_e036_goal_probe.scoring import OPERATORS, score
from experiments.thursday_probe.common import dump, jsonl, verify_manifest
from experiments.thursday_probe_v2.partial_audit import audit_batch_journal, incomplete_file
from analyses.completion_contract import first_stop
from scripts.audit_family_matching import verified_tokenizer
from src.sft_data import prefix, read_jsonl, sha256_file

STATES = ('E031', 'G-single', 'G-paired')
ARMS = STATES[1:]
INTERFACES = ('F', 'H', 'C')
N_BOOTSTRAP = 10000
BOOTSTRAP_SEED = 2026091708
RELEASE = Path('experiments/post_e037_goal_training/release_v1')
RUN = Path('runs/post_e037_goal_training_v1')
OUTPUT = Path('reports/post_e037_goal_training')
UNCERTAINTY = ('Paired number-group bootstrap and skeleton-family cluster sensitivity, '
    '10000 draws, seed 2026091708; single training seed, no training-seed uncertainty. '
    'Targets and stochastic samples are nested within groups. Exploratory intervals '
    'are not multiple-comparison-adjusted. A zero-event [0,0] interval is not population zero; '
    'a difference interval containing zero does not demonstrate equality.')
_data_index = frozen._data_index
_record_index = frozen._record_index
_operator_context = frozen._operator_context

def group_interval(values, families):
    """Equal-group mean; paired group and size-weighted family cluster bootstrap."""
    ids = sorted(values)
    if not ids:
        return dict(mean=None, groups=0, families=0, group_ci=None, family_ci=None)
    array = np.asarray([values[g] for g in ids], dtype=float)
    if not np.isfinite(array).all():
        raise ValueError('Nonfinite group measurements')
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(0, len(ids), (N_BOOTSTRAP, len(ids)))
    buckets = defaultdict(list)
    for index, group in enumerate(ids):
        buckets[families[group]].append(index)
    family_ci = None
    if len(buckets) > 1:
        keys = sorted(buckets)
        totals = np.array([array[buckets[k]].sum() for k in keys])
        sizes = np.array([len(buckets[k]) for k in keys])
        clusters = rng.integers(0, len(keys), (N_BOOTSTRAP, len(keys)))
        family_ci = np.quantile(totals[clusters].sum(axis=1)/sizes[clusters].sum(axis=1),
                                [.025, .975]).tolist()
    return dict(mean=float(array.mean()), groups=len(ids), families=len(buckets),
                group_ci=np.quantile(array[draws].mean(axis=1), [.025, .975]).tolist(),
                family_ci=family_ci)

def _rate(values, numerator, denominator, families):
    return dict(numerator=int(numerator), denominator=int(denominator),
                raw_fraction=numerator/denominator if denominator else None,
                **group_interval(values, families))

def _view_metrics_base(records, rows, samples):
    indexed, families = _record_index(records, rows, samples)
    groups = sorted(families); interface = rows[0]['interface']
    denominator = len(records)
    result = dict(groups=len(groups), targets=2*len(groups), generations=denominator,
                  samples_per_target=samples)
    for field in ('correct', 'parsed', 'completed', 'free_correct', 'uses_input_multiset',
                  'reaches_target', 'scaffold_followed', 'operator_correct',
                  'unconstrained_correct_off_template'):
        counts = Counter('NA' if r['score'].get(field) is None else
                         'true' if r['score'][field] else 'false' for r in records)
        if counts['NA'] == denominator:
            result[field] = dict(counts=dict(counts), numerator=None, denominator=denominator,
                                 raw_fraction=None, mean=None, group_ci=None, family_ci=None)
        else:
            values = {g: sum(indexed[g, t, s]['score'].get(field) is True
                             for t in (0, 1) for s in range(samples))/(2*samples) for g in groups}
            result[field] = dict(counts=dict(counts),
                                 **_rate(values, counts['true'], denominator, families))
    if samples == 4:
        solved = {g: sum(any(indexed[g, t, s]['score']['correct'] for s in range(samples))
                         for t in (0, 1))/2 for g in groups}
        result['pass_at_4'] = _rate(solved, round(sum(solved.values())*2), len(groups)*2, families)
    pairs, switches, same, assessable = {}, {}, {}, {}
    for group in groups:
        pair_flags, switch_flags, same_flags, available_flags = [], [], [], []
        for sample in range(samples):
            a, b = (indexed[group, target, sample]['score'] for target in (0, 1))
            both = bool(a['correct'] and b['correct'])
            pair_flags.append(both)
            switch_flags.append(bool(both and a.get('operator_correct') and b.get('operator_correct')
                                     and a.get('selected_operator') != b.get('selected_operator')))
            available = a.get('ordered_expression') is not None and b.get('ordered_expression') is not None
            available_flags.append(available)
            same_flags.append(bool(available and a['ordered_expression'] == b['ordered_expression'] and not both))
        pairs[group] = sum(pair_flags)/samples
        switches[group] = sum(switch_flags)/samples
        same[group] = sum(same_flags)/samples
        assessable[group] = sum(available_flags)/samples
    pair_denominator = len(groups)*samples
    result['both_targets_correct'] = _rate(pairs, round(sum(pairs.values())*samples), pair_denominator, families)
    if interface == 'H':
        result['correct_operator_switch'] = _rate(switches, round(sum(switches.values())*samples),
                                                  pair_denominator, families)
    if interface in ('F', 'H'):
        result['same_ordered_expression_failure'] = _rate(same, round(sum(same.values())*samples),
                                                          pair_denominator, families)
        result['same_ordered_expression_failure']['assessable_pairs'] = round(sum(assessable.values())*samples)
        result['same_ordered_expression_failure']['definition'] = (
            'Both answers have the same ordered AST, ignoring spaces/outer parentheses. '
            'Non-parsed pairs are unassessable, not evidence of a successful target switch.')
    result.update(stop_reasons=dict(Counter(r['stop']['stop_reason'] for r in records)),
                  failures=dict(Counter(r['score']['failure'] for r in records)),
                  resource_target_categories=dict(Counter(r['score']['resource_target_category'] for r in records)),
                  intermediate_arithmetic=dict(Counter(r['score']['intermediate_arithmetic_status'] for r in records)),
                  retained_length_quantiles=dict(zip(('min', 'p25', 'p50', 'p75', 'p95', 'max'),
                      np.quantile([len(r['generated_ids']) for r in records], [0, .25, .5, .75, .95, 1]).tolist())),
                  pairing_note='Sample index pairs independent requests; bootstrap unit is the number group.')
    return result

def rescue_loss(free_records, hole_records, free_rows, hole_rows, samples):
    f, families = _record_index(free_records, free_rows, samples)
    h, other_families = _record_index(hole_records, hole_rows, samples)
    if set(f) != set(h) or families != other_families:
        raise ValueError('F/H groups or family identities differ')
    _, free_index, _ = _data_index(free_rows)
    _, hole_index, _ = _data_index(hole_rows)
    if any((free_index[key]['numbers'], free_index[key]['target']) !=
           (hole_index[key]['numbers'], hole_index[key]['target']) for key in free_index):
        raise ValueError('F/H numbers or targets differ')
    rescued, lost = {}, {}
    for group in families:
        pairs = [(f[group, t, s]['score']['correct'], h[group, t, s]['score']['correct'])
                 for t in (0, 1) for s in range(samples)]
        rescued[group] = sum(not a and b for a, b in pairs)/(2*samples)
        lost[group] = sum(a and not b for a, b in pairs)/(2*samples)
    nr, nl = round(sum(rescued.values())*2*samples), round(sum(lost.values())*2*samples)
    return dict(rescued_F_wrong_H_correct=_rate(rescued, nr, len(f), families),
                lost_F_correct_H_wrong=_rate(lost, nl, len(f), families),
                H_minus_F=_rate({g: rescued[g]-lost[g] for g in families}, nr-nl, len(f), families),
                interpretation='Giving a template changes task difficulty and interface as well as search freedom; '
                               'this paired difference does not isolate an internal search/routing mechanism.')

def _operator_metrics_base(records, rows):
    _, registered, families = _data_index(rows)
    checked, unavailable = {}, []
    seen = set()
    for record in records:
        key = record['group_id'], record['target_index']
        if key in seen or key not in registered:
            raise ValueError('Duplicate or unregistered operator context')
        seen.add(key)
        expected = registered[key].get('correct_operator', registered[key].get('expected_operator'))
        if record.get('status') in ('unavailable', 'not_available'):
            if not record.get('reason'):
                raise ValueError('Unavailable operator context requires a reason')
            unavailable.append(dict(group_id=key[0], target_index=key[1], reason=record['reason']))
            continue
        if record['correct_operator'] != expected:
            raise ValueError('Operator context correct-label mismatch')
        checked[key] = _operator_context(record)
    per_group, d_values, switched, ranked = [], {}, {}, {}
    for group in sorted(families):
        if (group, 0) not in checked or (group, 1) not in checked:
            per_group.append(dict(group_id=group, status='not_measured_both_contexts', D_goal=None))
            continue
        a, b = checked[group, 0], checked[group, 1]
        o0, o1 = a['correct_operator'], b['correct_operator']
        la, lb = a['candidate_log_probabilities'], b['candidate_log_probabilities']
        d = (lb[o1]-lb[o0])-(la[o1]-la[o0])
        d_values[group] = d
        switched[group] = int(a['correct_unique_argmax'] and b['correct_unique_argmax'])
        ranked[group] = (int(a['correct_unique_argmax'])+int(b['correct_unique_argmax']))/2
        per_group.append(dict(group_id=group, status='measured', D_goal=d,
                              both_targets_correct_unique_argmax=bool(switched[group])))
    contexts = [checked[k] for k in sorted(checked)]
    paired_probability_means = {}
    for field in ('candidate_probability_mass', 'correct_raw_probability',
                  'correct_candidate_normalized_probability'):
        values = {g: (checked[g, 0][field]+checked[g, 1][field])/2 for g in d_values}
        paired_probability_means[field] = dict(**group_interval(values, families),
            numerator=sum(values.values())*2, denominator=len(values)*2)
    return dict(registered_contexts=len(registered), available_contexts=len(checked),
                recorded_contexts=len(seen), missing_contexts=len(registered)-len(seen),
                unavailable_contexts=unavailable, context_results=contexts, per_group=per_group,
                D_goal=dict(**group_interval(d_values, families), numerator=sum(d_values.values()),
                            denominator=len(d_values), units='natural-log-odds difference'),
                both_targets_correct_unique_argmax=_rate(switched, sum(switched.values()), len(switched), families),
                correct_unique_argmax_on_paired_groups=_rate(ranked, round(sum(ranked.values())*2), len(ranked)*2, families),
                paired_context_probability_means=paired_probability_means,
                available_context_ranking_counts=dict(denominator=len(contexts),
                    correct_unique_argmax=sum(c['correct_unique_argmax'] for c in contexts),
                    correct_in_argmax=sum(c['correct_in_argmax'] for c in contexts),
                    ties=sum(len(c['argmax_operators']) > 1 for c in contexts)),
                raw_candidate_probability_mass=dict(numerator=sum(c['candidate_probability_mass'] for c in contexts),
                    denominator=len(contexts), mean=(sum(c['candidate_probability_mass'] for c in contexts)/len(contexts)
                                                    if contexts else None)),
                interpretation='Raw log probabilities condition on the supplied prefix. Candidate-normalized '
                'probabilities are conditional on the four-candidate set, not full-vocabulary probabilities. '
                'D_goal uses raw log probabilities; positive D_goal alone is not full-path correctness. '
                'Missing contexts are NA; estimates explicitly use available complete target pairs.')


def _group_values(records, rows, samples, metric='correct'):
    indexed, families = _record_index(records, rows, samples)
    values = {}
    for group in families:
        flags = [[bool(indexed[group, t, s]['score']['correct'])
                  for s in range(samples)] for t in (0, 1)]
        if metric == 'both_targets_correct':
            value = sum(a and b for a, b in zip(*flags))/samples
        elif metric == 'independent_target_product':
            value = (sum(flags[0])/samples)*(sum(flags[1])/samples)
        elif metric == 'pass_at_4':
            value = sum(any(f) for f in flags)/2
        elif metric == 'correct':
            value = sum(map(sum, flags))/(2*samples)
        else:
            value = sum(indexed[group, t, s]['score'].get(metric) is True
                        for t in (0, 1) for s in range(samples))/(2*samples)
        values[group] = value
    return values, families


def hole_error_category(record, row):
    """Mutually exclusive interface diagnosis; never modifies strict scoring."""
    s = record['score']
    if s['correct']:
        return 'strict_correct'
    if not s['completed']:
        return 'incomplete_stop'
    if not s['parsed']:
        text = record['stop']['answer_segment']
        answer = text.rsplit('Answer:', 1)[-1] if 'Answer:' in text else ''
        if '?' in answer:
            return 'parse_unfilled_question_mark'
        if answer.count('(') != answer.count(')'):
            return 'parse_unbalanced_parentheses'
        return 'parse_other_or_missing_answer'
    if s['scaffold_followed']:
        return 'template_followed_wrong_hole_operator'
    if not s['uses_input_multiset']:
        return 'template_input_resources_changed'
    from src.trace_audit import parse_expression
    actual = parse_expression(s['expression'], final=True)
    reference = parse_expression(row['template'].replace('?', '+'), final=True)
    def shape(tree):
        return ('n', tree[1]) if tree[0] == 'n' else ('op', shape(tree[1]), shape(tree[2]))
    return ('template_tree_or_leaf_order_changed' if shape(actual) != shape(reference)
            else 'template_fixed_operator_changed')


def view_metrics(records, rows, samples):
    result = _view_metrics_base(records, rows, samples)
    families = _data_index(rows)[2]
    result['family_group_counts'] = dict(Counter(families.values()))
    if samples == 4:
        values, _ = _group_values(records, rows, samples, 'independent_target_product')
        # 16 cross-products per group are a plug-in estimate, not independent observations.
        result['independent_target_product'] = dict(**group_interval(values, families),
            sum_group_products=sum(values.values()), denominator=len(values),
            definition='Mean (c_g0/4)*(c_g1/4); independent target substreams; not pass@k or 16 independent groups.')
    if rows[0]['interface'] == 'H':
        by_id = {r['problem_id']: r for r in rows}
        result['interface_error_categories'] = dict(Counter(
            hole_error_category(r, by_id[r['problem_id']]) for r in records))
        result['interface_error_category_denominator'] = len(records)
        result['error_category_note'] = 'Mutually exclusive; incomplete stops precede parse categorization. Raw parsed=false may include those stops.'
    result['by_correct_operator'] = {}
    for op in OPERATORS:
        subset = {r['problem_id'] for r in rows if r['correct_operator'] == op}
        rs = [r for r in records if r['problem_id'] in subset]
        result['by_correct_operator'][op] = dict(correct=sum(r['score']['correct'] for r in rs),
                                                outputs=len(rs), questions=len(subset))
    return result


def paired_recipe_contrast(single, paired, rows, samples, metric):
    a, families = _group_values(single, rows, samples, metric)
    b, other = _group_values(paired, rows, samples, metric)
    if families != other:
        raise ValueError('Recipe group/family pairing differs')
    differences = {g: b[g]-a[g] for g in a}
    indexed_a, _ = _record_index(single, rows, samples)
    indexed_b, _ = _record_index(paired, rows, samples)
    gained = sum(not indexed_a[k]['score']['correct'] and indexed_b[k]['score']['correct'] for k in indexed_a)
    lost = sum(indexed_a[k]['score']['correct'] and not indexed_b[k]['score']['correct'] for k in indexed_a)
    result = dict(contrast='G-paired minus G-single', metric=metric,
        **group_interval(differences, families),
        G_single=group_interval(a, families), G_paired=group_interval(b, families),
        group_rows=[dict(group_id=g, family=families[g], G_single=a[g], G_paired=b[g],
                        difference=differences[g]) for g in sorted(a)],
        output_rescue=gained, output_loss=lost, output_pair_denominator=len(indexed_a),
        G_single_correct_outputs=sum(r['score']['correct'] for r in single),
        G_paired_correct_outputs=sum(r['score']['correct'] for r in paired),
        output_denominator=len(single),
        output_pair_note='Sample-index coupling is descriptive; inference resamples whole number groups.',
        uncertainty_scope=UNCERTAINTY)
    if samples == 1 and metric == 'both_targets_correct':
        result.update(G_single_correct_groups=int(sum(a.values())),
                      G_paired_correct_groups=int(sum(b.values())), group_denominator=len(a),
                      group_rescue=sum(not a[g] and b[g] for g in a),
                      group_loss=sum(a[g] and not b[g] for g in a))
    result['hole_position_strata'] = {}
    _, index, _ = _data_index(rows)
    for position in ('root', 'internal'):
        ids = [g for g in a if index[g, 0].get('hole_position',
            'root' if not index[g, 0].get('hole_path') else 'internal') == position]
        result['hole_position_strata'][position] = group_interval({g: differences[g] for g in ids}, families)
    return result


def operator_metrics(records, rows):
    result = _operator_metrics_base(records, rows)
    families = _data_index(rows)[2]
    contexts = result['context_results']
    by = {(c['group_id'], c['target_index']): c for c in contexts}
    for context in contexts:
        logp = context['candidate_log_probabilities']; correct = context['correct_operator']
        context['correct_minus_best_wrong_logp_margin'] = logp[correct]-max(
            p for op, p in logp.items() if op != correct)
    pairs = {g for g in families if (g, 0) in by and (g, 1) in by}
    margin = {g: sum(by[g, t]['correct_minus_best_wrong_logp_margin'] for t in (0, 1))/2 for g in pairs}
    result['correct_minus_best_wrong_logp_margin'] = dict(**group_interval(margin, families),
        units='natural log probability', paired_context_denominator=2*len(pairs))
    result['operator_marginals'] = {op: dict(
        registered_true_labels=sum(r['correct_operator'] == op for r in rows),
        available_true_labels=sum(c['correct_operator'] == op for c in contexts),
        unique_argmax_count=sum(c['argmax_operators'] == [op] for c in contexts),
        argmax_including_ties_count=sum(op in c['argmax_operators'] for c in contexts),
        correct_unique_argmax=sum(c['correct_operator'] == op and c['correct_unique_argmax'] for c in contexts),
        available_contexts=len(contexts)) for op in OPERATORS}
    result['family_group_counts'] = dict(Counter(families.values()))
    result['group_families'] = families
    return result


def training_diagnostic(records, rows, samples, state):
    if state not in ARMS or samples != 1:
        raise ValueError('Training diagnostic is greedy, final endpoint only')
    result = view_metrics(records, rows, samples)
    by_id = {r['problem_id']: r for r in rows}
    result['sampling_scope'] = ('Fixed 16 training groups, two per anchor-operator × root/internal stratum. '
        'G-single saw the anchor target only; G-paired saw both. These are not held-out generalization data. '
        'Training exposure labels concern new H supervision; shared F uses disjoint number groups.')
    result['target_exposure'] = {}
    for label in ('anchor', 'countergoal'):
        selected = [r for r in rows if bool(r.get('is_anchor',
            r['target_index'] == r.get('anchor_target_index'))) == (label == 'anchor')]
        if len(selected)*2 != len(rows):
            raise ValueError('Training diagnostic needs exactly one anchor and countergoal per group')
        selected_ids = {r['problem_id'] for r in selected}
        rs = [r for r in records if r['problem_id'] in selected_ids]
        values = {by_id[r['problem_id']]['group_id']: int(r['score']['correct']) for r in rs}
        families = {r['group_id']: r['skeleton_family_id'] for r in selected}
        result['target_exposure'][label] = dict(
            H_target_seen_during_training=state == 'G-paired' or label == 'anchor',
            **_rate(values, sum(values.values()), len(rs), families),
            failures=dict(Counter(r['score']['failure'] for r in rs)),
            resources_targets=dict(Counter(r['score']['resource_target_category'] for r in rs)))
    return result


def registered_events():
    events = []
    for state in STATES:
        for decoding, samples in (('greedy', 1), ('sampled', 4)):
            for interface in (INTERFACES if samples == 1 else ('F', 'H')):
                events.append(dict(name=f'{state}_{interface}_{decoding}', state=state,
                    interface=interface, decoding=decoding, view='eval', samples=samples,
                    sampling=samples == 4, questions=96, generations=96*samples,
                    checkpoint_step=32 if state == 'E031' else 256))
    for state in ARMS:
        events.append(dict(name=f'{state}_midpoint_H_greedy', state=state, interface='H',
            decoding='greedy', view='midpoint12', checkpoint_step=128,
            samples=1, sampling=False, questions=24, generations=24))
        for interface in ('F', 'H'):
            events.append(dict(name=f'{state}_train_{interface}_greedy', state=state, interface=interface,
                decoding='greedy', view='train16', checkpoint_step=256,
                samples=1, sampling=False, questions=32, generations=32))
    return [dict(event, expected_records=event['generations']) for event in events]


def analyze_generations(completed, pools):
    views = []
    for event in registered_events():
        name = event['name']; records = completed.get(name)
        rows = pools[event['view']][event['interface']]
        metric = None
        if records is not None:
            metric = (training_diagnostic(records, rows, event['samples'], event['state'])
                      if event['view'] == 'train16' else view_metrics(records, rows, event['samples']))
        views.append(dict(evaluation=name, **{k: v for k, v in event.items() if k != 'name'},
            status='measured' if metric is not None else 'not_measured_complete_view', metrics=metric))
    comparisons = []
    for interface, decoding, samples, metric, role in (
        ('H', 'greedy', 1, 'both_targets_correct', 'primary_direct_J_H'),
        ('F', 'sampled', 4, 'correct', 'primary_transfer_pass_at_1'),
        ('F', 'greedy', 1, 'correct', 'supporting_greedy'),
        ('F', 'sampled', 4, 'pass_at_4', 'supporting_pass_at_4'),
        ('H', 'greedy', 1, 'correct', 'supporting_target_accuracy'),
        ('H', 'sampled', 4, 'correct', 'supporting_sampled_target_accuracy'),
        ('H', 'sampled', 4, 'both_targets_correct', 'supporting_sample_index_pair'),
        ('H', 'sampled', 4, 'independent_target_product', 'supporting_independent_target_product'),
        ('H', 'greedy', 1, 'scaffold_followed', 'supporting_interface'),
        ('C', 'greedy', 1, 'correct', 'supporting_compute')):
        a, b = (f'{state}_{interface}_{decoding}' for state in ARMS)
        measured = a in completed and b in completed
        comparisons.append(dict(role=role, interface=interface, decoding=decoding, metric=metric,
            status='measured' if measured else 'not_measured_paired_views',
            result=paired_recipe_contrast(completed[a], completed[b], pools['eval'][interface], samples, metric)
                   if measured else None))
    baseline = []
    for arm in ARMS:
        for interface, decoding, samples in (('F', 'sampled', 4), ('H', 'greedy', 1), ('C', 'greedy', 1)):
            a, b = f'E031_{interface}_{decoding}', f'{arm}_{interface}_{decoding}'
            if a in completed and b in completed:
                aa, families = _group_values(completed[a], pools['eval'][interface], samples)
                bb, _ = _group_values(completed[b], pools['eval'][interface], samples)
                estimate = group_interval({g: bb[g]-aa[g] for g in aa}, families)
            else:
                estimate = None
            baseline.append(dict(contrast=arm+' minus E031', interface=interface, decoding=decoding,
                status='measured' if estimate is not None else 'not_measured_paired_views', result=estimate,
                interpretation='Includes common F replay, common H format training and further optimization; not a paired-goal-specific effect.'))
    return dict(views=views, recipe_comparisons=comparisons, baseline_descriptive_comparisons=baseline,
        bootstrap_replicates=N_BOOTSTRAP, bootstrap_seed=BOOTSTRAP_SEED, uncertainty_scope=UNCERTAINTY,
        primary_interpretation='The primary contrast is G-paired minus G-single at fixed step256. '
            'Report J_H and F transfer separately. Shared improvement relative to E031 does not identify recipe efficacy.',
        midpoint_scope='Frozen 12-group H subset at step128; descriptive only, never a stopping or checkpoint-selection rule.')


def operator_recipe_contrasts(results):
    by_state = {r['state']: r['metrics'] for r in results}
    if not all(s in by_state for s in ARMS):
        return dict(status='not_measured_paired_states', metrics=None)
    a, b = (by_state[s] for s in ARMS)
    aa = {r['group_id']: r for r in a['per_group'] if r['status'] == 'measured'}
    bb = {r['group_id']: r for r in b['per_group'] if r['status'] == 'measured'}
    ca = {(r['group_id'], r['target_index']): r for r in a['context_results']}
    cb = {(r['group_id'], r['target_index']): r for r in b['context_results']}
    groups = sorted(set(aa) & set(bb))
    families = {g: a['group_families'][g] for g in groups}
    metrics = {}
    for field in ('D_goal', 'both_targets_correct_unique_argmax', 'correct_unique_argmax',
                  'correct_minus_best_wrong_logp_margin', 'candidate_probability_mass',
                  'correct_raw_probability', 'correct_candidate_normalized_probability'):
        if field in ('D_goal', 'both_targets_correct_unique_argmax'):
            differences = {g: float(bb[g][field])-float(aa[g][field]) for g in groups}
        else:
            differences = {g: sum(float(cb[g, t][field])-float(ca[g, t][field]) for t in (0, 1))/2
                           for g in groups}
        metrics[field] = dict(**group_interval(differences, families),
                              per_group=[dict(group_id=g, difference=differences[g]) for g in groups])
    return dict(status='measured_available_complete_pairs' if groups else 'not_measured_paired_contexts',
        contrast='G-paired minus G-single', metrics=metrics,
        available_complete_groups=len(groups), uncertainty_scope=UNCERTAINTY)


def _report(summary, tables, operators):
    lines = ['# Post-E037 paired-goal training analysis', '',
        'Status: **'+summary['status']+'**. Offline analysis used no model calls.', '',
        'The main comparison is G-paired minus G-single at step256. Both arms receive the same '
        'F replay and H interface training. Their changes relative to E031 also contain those shared '
        'interventions and additional optimization.', '',
        '| Primary outcome | G-single | G-paired | Paired difference [95% group CI] |',
        '|---|---:|---:|---:|']
    for row in tables['recipe_comparisons']:
        if not row['role'].startswith('primary_'):
            continue
        m = row['result']
        if m is None:
            cells = ['NA', 'NA', 'NA — paired complete views not measured']
        else:
            cells = [f"{m[s]['mean']:.4f}" for s in ('G_single', 'G_paired')]
            cells += [f"{m['mean']:+.4f} [{m['group_ci'][0]:+.4f}, {m['group_ci'][1]:+.4f}]"]
        lines.append('| '+row['role']+' | '+' | '.join(cells)+' |')
    lines += ['', '| State | Pool | Interface | Decoding | Strict correct / outputs | Both targets / pairs |',
              '|---|---|---|---|---:|---:|']
    for row in tables['views']:
        m = row['metrics']
        cells = ([f"{m[k]['numerator']}/{m[k]['denominator']}" for k in ('correct', 'both_targets_correct')]
                 if m else ['NA', 'NA'])
        lines.append('| '+' | '.join([row['state'], row['view'], row['interface'], row['decoding']]+cells)+' |')
    lines += ['', UNCERTAINTY, '',
        'J_H counts groups whose two H greedy answers are both strictly correct. The sampled F primary '
        'is mean per-output correctness, equally weighting targets and number groups; sampled pass@4 '
        'and greedy are reported alongside it. Invalid, incomplete and unparsed outputs remain in denominators. '
        'Fixed sample-index pairs and products of target success fractions are supplementary; neither '
        'creates additional independent groups.', '',
        'The fixed training16 diagnostic oversamples anchor-operator × hole-position strata and separates '
        'anchor from countergoal. The G-single countergoal was not supervised for that number/template; '
        'both goals were supervised in G-paired. These are training-instance diagnostics, not held-out '
        'generalization estimates. The fixed midpoint12 H subset is not used to select checkpoints.', '',
        'Operator ranking, label/argmax marginals, correct-vs-best-wrong log-probability margin and D_goal '
        'condition on a supplied valid prefix. Raw full-vocabulary probability, candidate mass and '
        'within-set probability are separate. Positive D_goal alone is not correct choice or free construction.', '',
        'This two-arm recipe comparison changes distinct target/program support and repetition jointly. '
        'It does not establish an internal mechanism, a same-target multipath comparison, structural OOD, '
        'or an interaction with the old preparation states. No continuation is selected by this report.', '']
    return '\n'.join(lines)


def audit_commits(path, rows, event, tokenizer, ledger, release):
    """Bind a complete publication to immutable raw/score commits and reservations."""
    from experiments.post_e037_goal_training.generation import _descriptor, _digest, _protocol
    folder = path.with_suffix('.resume')
    manifest_path = folder/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    descriptor = manifest['descriptor']
    protocol, _ = _protocol(event, tokenizer)
    if descriptor != _descriptor(rows, event, descriptor['identity'], protocol):
        raise ValueError('Generation descriptor differs from the frozen protocol/rows')
    if descriptor['identity']['split_hash'] != sha256_file(release/'manifest.json'):
        raise ValueError('Generation split-manifest SHA differs from the frozen release')
    reservations = {r['name']: r['reserved'] for r in ledger['events']}
    before, records, raws, keys = manifest['initial_rng'], [], [], []
    files = sorted((folder/'batches').glob('*.raw.json'))
    for index, raw_path in enumerate(files):
        if raw_path.name != f'{index:06d}.raw.json':
            raise ValueError('Noncontiguous immutable batch stream')
        requests = descriptor['request_ids'][index*8:(index+1)*8]
        key = 'eval_batch_'+_digest(requests)
        identity = dict(evaluation_hash=_digest(descriptor), batch_index=index,
                        request_key=key, request_ids=requests, generations=len(requests))
        stem = folder/'batches'/f'{index:06d}'
        raw = json.loads(raw_path.read_text())
        intent = json.loads(Path(str(stem)+'.intent.json').read_text())
        reserved = json.loads(Path(str(stem)+'.reserved.json').read_text())
        scored = json.loads(Path(str(stem)+'.scored.json').read_text())
        if (not requests or raw['identity'] != identity or intent['identity'] != identity or
                reserved != identity or raw['rng_before'] != before or intent['rng_before'] != before or
                reservations.get(key) != len(requests) or scored['identity'] != identity or
                scored['raw_sha256'] != sha256_file(raw_path) or
                scored['records_sha256'] != _digest(scored['records'])):
            raise ValueError('Immutable batch/RNG/reservation/score binding differs')
        before = raw['rng_after']; records.extend(scored['records']); raws.append(raw['raw']); keys.append(key)
    if records != read_jsonl(path) or raws != read_jsonl(path.with_suffix('.raw_batches.jsonl')):
        raise ValueError('Published stream differs from immutable batches')
    return dict(status='verified', manifest_sha256=sha256_file(manifest_path),
                batches=len(raws), records=len(records), request_keys=keys,
                model_hash=descriptor['identity']['model_hash'])


def audit_predictions(path, rows, event, tokenizer, *, both_targets=True):
    """E037 replay contract, also usable on one physical target substream."""
    by_id = {row['problem_id']: row for row in rows}
    records = read_jsonl(path)
    decode = lambda ids: tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    vocab, specials = len(tokenizer), set(tokenizer.all_special_ids)
    for record in records:
        row = by_id[record['problem_id']]
        ids = record['batch_output_ids']
        stop = first_stop(ids, decode, tokenizer.eos_token_id, 512, specials | {t for t in ids if t >= vocab})
        if (record['forced_prefix'] != '' or stop != record['stop'] or
                record['generated_ids'] != ids[:stop['retained_tokens']] or
                any(t != tokenizer.eos_token_id for t in ids[stop['retained_tokens']:]) or
                record['prompt_ids'] != tokenizer.encode(prefix(row['prompt']), add_special_tokens=False) or
                record['score'] != score(row, stop) or
                any(record.get(k) != row[k] for k in ('task', 'interface', 'group_id', 'target_index'))):
            raise ValueError('Independent prompt/token/stop/scorer replay differs: '+path.name)
    wanted = [(row['problem_id'], s) for row in rows for s in range(event['samples'])]
    if [(r['problem_id'], r['sample_index']) for r in records] != wanted:
        raise ValueError('Published output is not the complete frozen row/sample order')
    if both_targets:
        _record_index(records, rows, event['samples'])
    return records, audit_batch_journal(path, records, rows, event, tokenizer)


def audit_completed_view(path, rows, event, summary, tokenizer, ledger, release, expected_model):
    from .generation import _digest, SEED, target_seed
    if (summary['status'] != 'completed' or summary['completed_records'] != len(rows)*event['samples'] or
            summary['predictions_sha256'] != sha256_file(path) or
            summary['adapter']['sha256'] != expected_model):
        raise ValueError('Completed view count/hash/model identity differs: '+path.name)
    if not event['sampling']:
        saved_event = json.loads((path.with_suffix('.resume')/'manifest.json').read_text())['descriptor']['event']
        if any(saved_event.get(k) != v for k, v in event.items()):
            raise ValueError('Saved event differs from frozen queue')
        records, journal = audit_predictions(path, rows, saved_event, tokenizer)
        commit = audit_commits(path, rows, saved_event, tokenizer, ledger, release)
        if commit['model_hash'] != expected_model:
            raise ValueError('Generation descriptor model differs from checkpoint')
        return records, dict(journal=journal, immutable_commits=commit)
    folder = path.with_suffix('.targets')
    binding = json.loads((folder/'manifest.json').read_text())
    saved_event = binding['event']
    if (any(saved_event.get(k) != v for k, v in event.items()) or
            binding != json.loads(path.with_suffix('.generation.json').read_text()) or
            binding['rows_sha256'] != _digest(rows) or binding['model_hash'] != expected_model or
            binding['split_hash'] != sha256_file(release/'manifest.json') or
            binding['base_seed'] != SEED or binding['mode'] != 'independent_target_substreams' or
            binding['target_seeds'] != {str(i): target_seed(i) for i in (0, 1)}):
        raise ValueError('Logical target-substream manifest differs')
    streams = summary['substreams']
    if [s['target_index'] for s in streams] != [0, 1]:
        raise ValueError('Missing, duplicated or reordered target streams')
    merged, audits = {}, []
    for index, stream in enumerate(streams):
        subset = [r for r in rows if r['target_index'] == index]
        subpath = folder/f't{index}.jsonl'
        subsummary_path = subpath.with_suffix('.summary.json')
        sm = json.loads(subsummary_path.read_text())
        subevent = dict(saved_event, name=saved_event['name']+f'_t{index}', questions=len(subset),
            generations=len(subset)*4, expected_records=len(subset)*4,
            evaluation_seed=target_seed(index), target_index=index)
        if (stream['seed'] != target_seed(index) or stream['status'] != 'completed' or
                stream['path'] != str(subpath.relative_to(path.parent)) or
                stream['summary_path'] != str(subsummary_path.relative_to(path.parent)) or
                stream['completed_records'] != len(subset)*4 or
                stream['predictions_sha256'] != sha256_file(subpath) or
                stream['manifest_sha256'] != sha256_file(subpath.with_suffix('.resume')/'manifest.json') or
                any(sm.get(k) != v for k, v in subevent.items()) or
                any(sm.get(k) != v for k, v in stream.items()) or
                sm['adapter_sha256'] != expected_model):
            raise ValueError('Target-substream summary binding differs')
        rs, journal = audit_predictions(subpath, subset, subevent, tokenizer, both_targets=False)
        commit = audit_commits(subpath, subset, subevent, tokenizer, ledger, release)
        if commit['model_hash'] != expected_model:
            raise ValueError('Target-substream model differs')
        for record in rs:
            merged[record['problem_id'], record['sample_index']] = record
        audits.append(dict(target_index=index, seed=target_seed(index), journal=journal, immutable_commits=commit))
    records = read_jsonl(path)
    if records != [merged[row['problem_id'], s] for row in rows for s in range(4)]:
        raise ValueError('Logical sampled publication differs from independently verified target streams')
    _record_index(records, rows, 4)
    return records, dict(mode='independent_target_substreams', substreams=audits,
                         logical_manifest_sha256=sha256_file(folder/'manifest.json'))


PARENT_SHA = '0936c1682d6df767fbc91a54deba6de1ff558dfd5e8182ae8b3c0d32a892074e'


def checkpoint_models(run, manifest, release):
    registration = json.loads((Path(__file__).parent/'registration.json').read_text())['entries']
    if manifest.get('parent') != 'E031' or manifest['parent_adapter']['sha256'] != PARENT_SHA:
        raise ValueError('Common initial checkpoint is not the frozen E031 parent')
    models = {('E031', 32): PARENT_SHA}
    training = []
    for entry in registration:
        state = entry['state']; directory = run/entry['run_id']
        path = directory/'run_manifest_final.json'
        final = json.loads(path.read_text()) if path.exists() else None
        for step in (128, 256):
            identity = directory/f'checkpoint_{step}'/'checkpoint_identity.json'
            if identity.exists():
                cp = json.loads(identity.read_text())
                models[state, step] = cp['parameter_digest']['sha256']
        measured_nll = {}
        for interface in ('H', 'F'):
            measured_nll[interface] = {}
            for when in ('before', 'after'):
                nll_path = directory/f'reference_{interface}_{when}.json'
                value = json.loads(nll_path.read_text()) if nll_path.exists() else None
                if value is not None and (value.get('forward_calls') != 512 or
                        not math.isfinite(value.get('forward_seconds', float('nan'))) or value['forward_seconds'] < 0):
                    raise ValueError('Reference NLL measured forward accounting differs')
                measured_nll[interface][when] = value
        if final:
            if (final['status'] != 'completed' or final['completed_updates'] != 256 or
                    final['state'] != state or final['parent_adapter']['sha256'] != PARENT_SHA or
                    final['identity']['data_sha256'] != sha256_file(release/(entry['data']+'.jsonl')) or
                    final['final_adapter']['sha256'] != models.get((state, 256)) or
                    final['optimizer_reset'] is not True or final['scheduler_reset'] is not True):
                raise ValueError('Final training endpoint or recipe differs from registration')
            history = read_jsonl(directory/'train_history.jsonl')
            if len(history) != 256 or [r['step'] for r in history] != list(range(1, 257)):
                raise ValueError('Final training update history is incomplete or noncontiguous')
        training.append(dict(state=state, status='completed' if final else 'not_completed',
            final_manifest=final, reference_nll=measured_nll,
            reference_scope='Reference CE on that arm\'s training H512 and identical F512. '
                'H references differ across recipes; these are not matched held-out targets. '
                'NLL diagnoses fit and is not a success criterion. Before/after likelihoods include '
                'the complete supervised response and EOS; measured forward_seconds is retained.'))
    return models, training


def _inventory_partial(path):
    result = dict(status='not_run', published_records=0, durable_raw_batches=0, durable_raw_records=0)
    if path.exists():
        inventory, visible = incomplete_file(path)
        result.update(status='incomplete_not_in_metrics', inventory=inventory, published_records=len(visible))
    files = list(path.with_suffix('.resume').glob('batches/*.raw.json'))
    files += list(path.with_suffix('.targets').glob('*.resume/batches/*.raw.json'))
    if files:
        result.update(status='incomplete_not_in_metrics', durable_raw_batches=len(files),
            durable_raw_records=sum(len(json.loads(p.read_text())['raw']['problem_ids']) for p in files))
    return result


def analyze(run=RUN, release=RELEASE, output=OUTPUT, *, tokenizer_dir):
    from .data import load_rows, load_operator_rows
    run, release, output = Path(run), Path(release), Path(output)
    if output.exists():
        raise FileExistsError('Never overwrite a completed or partial analysis')
    verify_manifest(release)
    pools = {pool: {i: load_rows(i, release, pool=pool) for i in interfaces}
             for pool, interfaces in (('eval', INTERFACES), ('train16', ('F', 'H')), ('midpoint12', ('H',)))}
    for pool, views in pools.items():
        for rows in views.values():
            groups = _data_index(rows)[2]
            if len(groups) != {'eval': 48, 'train16': 16, 'midpoint12': 12}[pool]:
                raise ValueError('Frozen analysis pool count differs')
    contexts = load_operator_rows(release)
    tokenizer, tokenizer_identity = verified_tokenizer(Path(tokenizer_dir))
    ledger_path = run/'generation_ledger.json'
    manifest_path = next((run/p for p in ('run_manifest_final.json', 'progress.json', 'run_manifest.json') if (run/p).exists()), None)
    if manifest_path is None:
        raise FileNotFoundError('Run has no execution manifest')
    manifest, ledger = json.loads(manifest_path.read_text()), json.loads(ledger_path.read_text())
    release_hash = sha256_file(release/'manifest.json')
    if manifest['release_manifest_sha256'] != release_hash:
        raise ValueError('Run is bound to a different frozen release')
    events = ledger['events']
    if (len({e['name'] for e in events}) != len(events) or ledger['cap'] != 3600 or
            any(type(e['reserved']) is not int or e['reserved'] <= 0 for e in events) or
            sum(e['reserved'] for e in events) != ledger['used'] or not 0 <= ledger['used'] <= 3600):
        raise ValueError('New-phase generation ledger is inconsistent')
    models, training = checkpoint_models(run, manifest, release)
    completed, coverage, audits = {}, [], {}
    for event in registered_events():
        name = event['name']; path = run/(name+'.jsonl'); summary_path = path.with_suffix('.summary.json')
        rows = pools[event['view']][event['interface']]
        summary = json.loads(summary_path.read_text()) if summary_path.exists() else None
        item = dict(evaluation=name, expected_records=event['generations'], **_inventory_partial(path))
        if summary and summary.get('status') == 'completed':
            if any(summary.get(k) != v for k, v in event.items()):
                raise ValueError('Completed summary differs from registered queue: '+name)
            step = 32 if event['state'] == 'E031' else 128 if event['view'] == 'midpoint12' else 256
            expected_model = models.get((event['state'], step))
            if expected_model is None:
                raise ValueError('Completed view has no verified scientific checkpoint identity')
            records, audit = audit_completed_view(path, rows, event, summary, tokenizer, ledger, release, expected_model)
            completed[name] = records; audits[name] = audit
            item.update(status='complete_independently_verified', completed_records=len(records))
        coverage.append(item)
    tables = analyze_generations(completed, pools)
    operator_results = []
    for state in STATES:
        path = run/'operator_scores'/(state+'.json')
        artifact = json.loads(path.read_text()) if path.exists() else None
        if artifact:
            expected = models.get((state, 32 if state == 'E031' else 256))
            if (artifact['state'] != state or artifact['model_hash'] != expected or
                    artifact['release_manifest_sha256'] != release_hash):
                raise ValueError('Operator artifact endpoint/release differs')
            frozen._operator_bindings(artifact, contexts, tokenizer, directory=run/'operator_scores'/state,
                                      model_hash=expected, release_hash=release_hash)
        metrics = operator_metrics(artifact['records'] if artifact else [], pools['eval']['H'])
        operator_results.append(dict(state=state, status='recorded' if artifact else 'not_measured',
            metrics=metrics, forward_metadata={k: v for k, v in artifact.items() if k != 'records'} if artifact else None))
    complete = (len(completed) == len(coverage) and
                all(r['metrics']['recorded_contexts'] == len(contexts) for r in operator_results) and
                all(r['status'] == 'completed' for r in training))
    if manifest.get('status') == 'completed' and not complete:
        raise ValueError('Completed phase is missing training, generation or operator units')
    summary = dict(status='all_registered_outputs_verified' if complete else 'partial_coverage_verified',
        completed_generation_views=len(completed), registered_generation_views=len(coverage),
        completed_unique_generations=sum(map(len, completed.values())), registered_generations=3344,
        charged_generation_reservations=ledger['used'], generation_cap=ledger['cap'],
        planned_training_runs=2, completed_training_runs=sum(r['status'] == 'completed' for r in training),
        completed_training_updates=manifest.get('training_updates'),
        planned_training_updates=512, analysis_model_calls=0, tokenizer=tokenizer_identity,
        generation_audits=audits, historical_phase_budgets_used_for_new_generation=False,
        verification_scope='Independent frozen prompt/token/stop/scorer replay, immutable raw/score/request/RNG '
            'bindings, scientific checkpoint hashes, target-substream identities and operator likelihood arithmetic. '
            'No model forward replay; weight contents rely on exported checkpoint hash/parameter identities.',
        uncertainty_scope=UNCERTAINTY)
    output.mkdir(parents=True, exist_ok=False)
    dump(output/'SUMMARY.json', summary)
    dump(output/'COVERAGE.json', coverage)
    dump(output/'GOAL_SWITCH_RESULTS.json', dict(
        **{k: v for k, v in tables.items() if k != 'views'},
        views=[r for r in tables['views'] if r['view'] == 'eval']))
    dump(output/'FREE_CONSTRUCTION_TRANSFER.json', dict(
        views=[r for r in tables['views'] if r['view'] == 'eval' and r['interface'] == 'F'],
        recipe_comparisons=[r for r in tables['recipe_comparisons'] if r['interface'] == 'F'],
        baseline_descriptive_comparisons=[r for r in tables['baseline_descriptive_comparisons'] if r['interface'] == 'F'],
        uncertainty_scope=UNCERTAINTY))
    dump(output/'OPERATOR_CHOICE_RESULTS.json', dict(results=operator_results,
        recipe_contrasts=operator_recipe_contrasts(operator_results), uncertainty_scope=UNCERTAINTY))
    dump(output/'TRAIN_SEEN_COUNTERGOAL_DIAGNOSTIC.json', dict(
        views=[r for r in tables['views'] if r['view'] == 'train16'],
        scope='Fixed training instances, stratified 2 per anchor operator × root/internal; not held-out generalization.'))
    dump(output/'MIDPOINT_DIAGNOSTIC.json', dict(
        views=[r for r in tables['views'] if r['view'] == 'midpoint12'],
        scope=tables['midpoint_scope'], selected_endpoint_step=256))
    dump(output/'TRAINING_AND_REFERENCE_NLL.json', dict(runs=training,
        interpretation='Both arms share F source rows and slots. H references differ by recipe; NLL is diagnostic only.'))
    jsonl(output/'SCORED_OUTPUTS.jsonl', [dict(evaluation=name, **record)
        for name, records in completed.items() for record in records])
    (output/'REPORT.md').write_text(_report(summary, tables, operator_results))
    error_lines = ['# Strict-score error inventory', '',
        'All invalid and incomplete generations remain in denominators. H categories are mutually '
        'exclusive with incomplete stops assigned before parse errors. No output is repaired or rescored '
        'under a relaxed rule.', '', '| Evaluation | Error category | Count |', '|---|---|---:|']
    for row in tables['views']:
        if row['metrics'] is None:
            continue
        categories = row['metrics'].get('interface_error_categories', row['metrics']['failures'])
        for category, count in sorted(categories.items()):
            error_lines.append(f"| {row['evaluation']} | {category} | {count} |")
    error_lines += ['', 'C strict scores evaluate the original expression. A wrong C answer with consistent '
        'local equations may still change numbers, operand order or grouping. Those descriptive program '
        'changes require trace-level review; local consistency is not expression fidelity. Missing arithmetic '
        'evidence remains NA. Per-output text, original strict scores and resource/target/local-arithmetic '
        'fields are retained in SCORED_OUTPUTS.jsonl.', '']
    (output/'ERROR_CASES.md').write_text('\n'.join(error_lines))
    bindings = {str(p): sha256_file(p) for p in sorted(run.rglob('*'))
                if p.is_file() and p.suffix in ('.json', '.jsonl') and not p.is_symlink()}
    bindings[str(release/'manifest.json')] = release_hash
    bindings[str(Path(__file__).parent/'registration.json')] = sha256_file(Path(__file__).parent/'registration.json')
    sources = ('experiments/post_e037_goal_training/analyze.py', 'experiments/post_e037_goal_training/generation.py',
        'experiments/post_e037_goal_training/data.py', 'experiments/post_e036_goal_probe/analyze.py',
        'experiments/post_e036_goal_probe/scoring.py', 'src/trace_audit.py', 'analyses/completion_contract.py')
    dump(output/'manifest.json', dict(input_files_sha256=bindings,
        source_files_sha256={p: sha256_file(p) for p in sources},
        files_sha256={p.name: sha256_file(p) for p in sorted(output.iterdir())}))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=RUN)
    parser.add_argument('--release', type=Path, default=RELEASE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--tokenizer-dir', required=True)
    args = parser.parse_args()
    result = analyze(args.run_dir, args.release, args.output, tokenizer_dir=args.tokenizer_dir)
    print(json.dumps({k: result[k] for k in ('status', 'completed_generation_views', 'completed_unique_generations')}))
