import copy
import math
import json
from pathlib import Path
import tempfile
import unittest

from experiments.post_e037_goal_training import analyze as a
from experiments.post_e036_goal_probe.scoring import score


def fixture(interface='H', samples=1, successes=None):
    rows, records = [], []
    for gi in range(4):
        for target_index, (target, operator) in enumerate(((19, '-'), (49, '+'))):
            row = dict(interface=interface, task='compute' if interface == 'C' else 'construct',
                group_id='g'+str(gi), problem_id=f'g{gi}_t{target_index}_{interface}',
                target_index=target_index, numbers=[12, 5, 3, 2], target=target, answer=str(target),
                template='((12 ? 5) * 3) - 2', correct_operator=operator,
                skeleton_family_id='family'+str(gi//2), hole_path=[1, 1],
                hole_position='root' if gi < 2 else 'internal',
                is_anchor=target_index == gi % 2, anchor_target_index=gi % 2)
            rows.append(row)
            for sample in range(samples):
                right = successes is None or (gi, target_index, sample) in successes
                chosen = operator if right else ('+' if operator == '-' else '-')
                text = f'Answer: ((12 {chosen} 5) * 3) - 2'
                if interface == 'C':
                    text = 'Answer: '+str(target if right else 0)
                stop = dict(answer_segment=text, stop_reason='native_eos')
                records.append(dict(problem_id=row['problem_id'], sample_index=sample,
                    stop=stop, generated_ids=[1, 0], score=score(row, stop)))
    return rows, records


def operator_record(group, target, probabilities=None):
    probabilities = probabilities or ({'+': .1, '-': .7, '*': .1, '/': .1} if target == 0
                                      else {'+': .7, '-': .1, '*': .1, '/': .1})
    mass = .2
    return dict(group_id=group, target_index=target, correct_operator='-' if target == 0 else '+',
        candidate_ids={op: [i] for i, op in enumerate(a.OPERATORS)}, candidate_probability_mass=mass,
        candidates=[dict(operator=op, probability=p*mass, normalized_probability=p,
                        log_probability=math.log(p*mass)) for op, p in probabilities.items()])


class RecipeAnalysisTests(unittest.TestCase):
    def test_primary_switch_differs_from_per_target_accuracy(self):
        rows, single = fixture(successes={(i, 0, 0) for i in range(4)})
        _, paired = fixture(successes={(i, t, 0) for i in (0, 1) for t in (0, 1)})
        result = a.paired_recipe_contrast(single, paired, rows, 1, 'both_targets_correct')
        self.assertEqual((result['G_single_correct_groups'], result['G_paired_correct_groups']), (0, 2))
        self.assertEqual(result['mean'], .5)
        self.assertEqual(result['groups'], 4)
        self.assertEqual(result['families'], 2)
        per_target = a.paired_recipe_contrast(single, paired, rows, 1, 'correct')
        self.assertEqual(per_target['mean'], 0)
        self.assertEqual(result['group_rescue'], 2)
        self.assertEqual(result['group_loss'], 0)

    def test_sample_pairs_and_cross_product_are_not_independent_groups(self):
        successes = {(g, 0, s) for g in range(4) for s in (0, 1)}
        successes |= {(g, 1, s) for g in range(4) for s in (2, 3)}
        rows, records = fixture(samples=4, successes=successes)
        result = a.view_metrics(records, rows, 4)
        self.assertEqual(result['both_targets_correct']['denominator'], 16)
        self.assertEqual(result['both_targets_correct']['numerator'], 0)
        self.assertEqual(result['correct']['numerator'], 16)
        self.assertEqual(result['correct']['denominator'], 32)
        self.assertEqual(result['independent_target_product']['mean'], .25)
        self.assertEqual(result['independent_target_product']['denominator'], 4)
        self.assertEqual(result['pass_at_4']['numerator'], 8)
        self.assertEqual(result['pass_at_4']['denominator'], 8)

    def test_bootstrap_pairing_seed_and_reproducibility(self):
        values = dict(a=-1, b=0, c=1, d=.25)
        families = dict(a='f0', b='f0', c='f1', d='f2')
        self.assertEqual(a.BOOTSTRAP_SEED, 2026091708)
        first = a.group_interval(values, families)
        self.assertEqual(first, a.group_interval(dict(reversed(list(values.items()))), families))
        self.assertEqual(first['mean'], .0625)
        self.assertEqual(first['groups'], 4)
        self.assertEqual(first['families'], 3)
        self.assertIsNone(a.group_interval({}, {})['mean'])

    def test_missing_or_duplicate_outputs_cannot_become_zero(self):
        rows, records = fixture()
        with self.assertRaisesRegex(ValueError, 'every frozen'):
            a.view_metrics(records[:-1], rows, 1)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            a.view_metrics(records+[records[0]], rows, 1)
        pools = {pool: {i: fixture(i)[0] for i in interfaces}
                 for pool, interfaces in (('eval', 'FHC'), ('train16', 'FH'), ('midpoint12', 'H'))}
        table = a.analyze_generations({}, pools)
        self.assertEqual(len(table['views']), 21)
        self.assertTrue(all(v['metrics'] is None for v in table['views']))
        self.assertTrue(all(c['result'] is None for c in table['recipe_comparisons']))
        self.assertEqual(sum(e['generations'] for e in a.registered_events()), 3344)

    def test_seen_countergoal_labels_and_unequal_exposure_scope(self):
        rows, records = fixture()
        single = a.training_diagnostic(records, rows, 1, 'G-single')
        paired = a.training_diagnostic(records, rows, 1, 'G-paired')
        self.assertTrue(single['target_exposure']['anchor']['H_target_seen_during_training'])
        self.assertFalse(single['target_exposure']['countergoal']['H_target_seen_during_training'])
        self.assertTrue(paired['target_exposure']['countergoal']['H_target_seen_during_training'])
        self.assertEqual(single['target_exposure']['countergoal']['denominator'], 4)
        self.assertIn('not held-out', single['sampling_scope'])

    def test_incomplete_stop_precedes_parse_without_modifying_score(self):
        rows, records = fixture()
        row = rows[0]
        stop = dict(answer_segment='Answer: ((12 ? 5) * 3) - 2', stop_reason='length_cap')
        record = dict(stop=stop, score=score(row, stop))
        before = copy.deepcopy(record)
        self.assertEqual(a.hole_error_category(record, row), 'incomplete_stop')
        self.assertEqual(record, before)
        stop['stop_reason'] = 'native_eos'; record['score'] = score(row, stop)
        self.assertEqual(a.hole_error_category(record, row), 'parse_unfilled_question_mark')

    def test_operator_margins_labels_mass_and_ties_are_separate(self):
        rows, _ = fixture()
        records = [operator_record('g'+str(g), t) for g in range(4) for t in (0, 1)]
        result = a.operator_metrics(records, rows)
        self.assertAlmostEqual(result['D_goal']['mean'], 2*math.log(7))
        self.assertAlmostEqual(result['correct_minus_best_wrong_logp_margin']['mean'], math.log(7))
        self.assertEqual(result['operator_marginals']['+']['unique_argmax_count'], 4)
        self.assertEqual(result['operator_marginals']['+']['registered_true_labels'], 4)
        self.assertAlmostEqual(result['raw_candidate_probability_mass']['mean'], .2)
        self.assertAlmostEqual(result['context_results'][0]['correct_raw_probability'], .14)
        tied = operator_record('g0', 0, {op: .25 for op in a.OPERATORS})
        result = a.operator_metrics([tied], rows)
        self.assertEqual(result['operator_marginals']['+']['unique_argmax_count'], 0)
        self.assertEqual(result['operator_marginals']['+']['argmax_including_ties_count'], 1)
        self.assertIsNone(result['D_goal']['mean'])

    def test_operator_recipe_difference_uses_common_complete_pairs(self):
        rows, _ = fixture()
        good = [operator_record('g'+str(g), t) for g in range(4) for t in (0, 1)]
        tie = [operator_record('g'+str(g), t, {op: .25 for op in a.OPERATORS}) for g in range(4) for t in (0, 1)]
        results = [dict(state='G-single', metrics=a.operator_metrics(tie, rows)),
                   dict(state='G-paired', metrics=a.operator_metrics(good, rows))]
        result = a.operator_recipe_contrasts(results)
        self.assertEqual(result['available_complete_groups'], 4)
        self.assertEqual(result['metrics']['both_targets_correct_unique_argmax']['mean'], 1)
        self.assertAlmostEqual(result['metrics']['D_goal']['mean'], 2*math.log(7))

    def test_independent_target_publication_audit_detects_tampering(self):
        # CPU fixture exercises the real durable generation writer, but the
        # fake model has no parameters and makes no model/service call.
        from experiments.post_e037_goal_training import generation as gen
        from src.sft_data import sha256_file
        from tests.test_goal_probe_runtime import RuntimeTests
        from tests.test_thursday_v2_resumable_generation import Model, Tokenizer, Budget
        rows, _ = fixture('H', 4)
        for row in rows:
            row['prompt'] = 'Use the given numbers and fill the template.'
        event = dict(name='G-single_H_sampled', state='G-single', interface='H', decoding='sampled',
                     view='eval', samples=4, sampling=True, questions=len(rows), generations=len(rows)*4)
        with tempfile.TemporaryDirectory() as tmp, RuntimeTests().cpu():
            root = Path(tmp); release = root/'release'; release.mkdir()
            (release/'manifest.json').write_text('{}')
            identity = dict(model_hash='a'*64, split_hash=sha256_file(release/'manifest.json'),
                            batch_time_reserve_seconds=120.)
            path = root/'G-single_H_sampled.jsonl'; budget = Budget(root/'ledger.json')
            result = gen.run_event(Model(), Tokenizer(), rows, path, event, identity, 99, budget, 1e20)
            summary = dict(status='completed', completed_records=len(result['records']),
                predictions_sha256=sha256_file(path), adapter={'sha256': 'a'*64},
                substreams=result['substreams'])
            records, audit = a.audit_completed_view(path, rows, event, summary, Tokenizer(),
                                                    budget.record(), release, 'a'*64)
            self.assertEqual(len(records), 32)
            self.assertEqual(len(audit['substreams']), 2)
            # Re-hashing the public merged file must not bypass immutable
            # substream evidence or the frozen row/sample order.
            records[0]['score']['correct'] = not records[0]['score']['correct']
            path.write_text(''.join(json.dumps(r)+'\n' for r in records))
            summary['predictions_sha256'] = sha256_file(path)
            with self.assertRaisesRegex(ValueError, 'Logical sampled publication differs'):
                a.audit_completed_view(path, rows, event, summary, Tokenizer(), budget.record(), release, 'a'*64)

    def test_analysis_queue_matches_runtime_scientific_endpoints(self):
        from experiments.post_e037_goal_training.queue import evaluation_queue
        self.assertEqual({e['name']: e for e in a.registered_events()},
                         {e['name']: e for e in evaluation_queue()})


if __name__ == '__main__':
    unittest.main()
