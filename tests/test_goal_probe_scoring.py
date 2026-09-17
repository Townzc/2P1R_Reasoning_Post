import math
import unittest

from experiments.post_e036_goal_probe import analyze

from experiments.post_e036_goal_probe.scoring import score, ordered_expression_key


def row(interface='H', target=19, correct_operator='-'):
    return dict(interface=interface, task='construct', problem_id='fixture/0',
                numbers=[12, 5, 3, 2], target=target, answer=target,
                template='((12 ? 5) * 3) - 2', correct_operator=correct_operator)


def answer(text, stop_reason='native_eos'):
    return dict(answer_segment=text, stop_reason=stop_reason)


class GoalProbeScoringTests(unittest.TestCase):
    def test_h_accepts_whitespace_outer_parens_and_switches_correctly(self):
        for target, operator in ((19, '-'), (49, '+')):
            s = score(row(target=target, correct_operator=operator),
                      answer('Answer: ( ( (12 '+operator+' 5) * 3 ) - 2 )'))
            self.assertTrue(s['correct'])
            self.assertTrue(s['scaffold_followed'])
            self.assertEqual(s['selected_operator'], operator)

    def test_commutative_rewrite_passes_f_but_fails_h(self):
        text = 'Answer: 3 * (12 - 5) - 2'
        self.assertTrue(score(row('F'), answer(text))['correct'])
        s = score(row(), answer(text))
        self.assertTrue(s['free_correct'])
        self.assertTrue(s['unconstrained_correct_off_template'])
        self.assertFalse(s['scaffold_followed'])
        self.assertFalse(s['correct'])
        self.assertEqual(s['failure'], 'template_violation')
        self.assertNotEqual(ordered_expression_key('3 * (12 - 5) - 2'),
                            ordered_expression_key('(12 - 5) * 3 - 2'))

    def test_wrong_target_is_not_an_intermediate_arithmetic_error(self):
        text = ('Step 1: 12 + 5 = 17.\nStep 2: 17 * 3 = 51.\n'
                'Step 3: 51 - 2 = 49.\nAnswer: ((12 + 5) * 3) - 2')
        s = score(row(), answer(text))
        self.assertTrue(s['scaffold_followed'])
        self.assertTrue(s['uses_input_multiset'])
        self.assertFalse(s['reaches_target'])
        self.assertEqual(s['intermediate_arithmetic_status'], 'consistent')
        self.assertFalse(s['operator_correct'])
        self.assertFalse(s['correct'])

    def test_stop_resource_and_parse_failures_remain_in_strict_score(self):
        text = 'Answer: ((12 - 5) * 3) - 2'
        self.assertFalse(score(row(), answer(text, 'length_cap'))['correct'])
        bad = score(row('F'), answer('Answer: 19'))
        self.assertTrue(bad['reaches_target'])
        self.assertFalse(bad['uses_input_multiset'])
        self.assertFalse(bad['correct'])
        for text in ('Answer: ((12 ** 5) * 3) - 2', 'Answer: 19\nAnswer: 19', 'no answer'):
            self.assertFalse(score(row(), answer(text))['correct'])

    def test_c_checks_exact_value_without_construction_resources(self):
        s = score(row('C', target=49), answer('Answer: 98 / 2'))
        self.assertTrue(s['correct'])
        self.assertIsNone(s['uses_input_multiset'])
        self.assertIsNone(s['scaffold_followed'])
        self.assertFalse(score(row('C', target=49), answer('Answer: 48'))['correct'])
        self.assertFalse(score(row('C'), answer('Answer: 1 / 0'))['correct'])

    def test_bad_template_registration_is_rejected(self):
        for changes in ({'template': '(12 ? 5) ? (3 - 2)'},
                        {'correct_operator': '+'}, {'template': '((12 ? 5) * 3) - 3'}):
            with self.assertRaises(ValueError):
                score(dict(row(), **changes), answer('Answer: ((12 - 5) * 3) - 2'))


class GoalProbeAnalysisTests(unittest.TestCase):
    def fixture(self, interface='H', samples=4):
        rows, records = [], []
        for group in ('g0', 'g1'):
            for target_index, (target, operator) in enumerate(((19, '-'), (49, '+'))):
                problem = dict(row(interface, target, operator), group_id=group,
                    target_index=target_index, problem_id=group+str(target_index)+interface,
                    skeleton_family_id=group)
                rows.append(problem)
                for sample in range(samples):
                    # One group succeeds at both targets only in sample0; the
                    # other always emits the same '-' expression for both goals.
                    chosen = operator if group == 'g0' and sample == 0 else '-'
                    stop = answer('Answer: ((12 '+chosen+' 5) * 3) - 2')
                    records.append(dict(problem_id=problem['problem_id'], sample_index=sample,
                        score=score(problem, stop), stop=stop, generated_ids=[1, 0]))
        return rows, records

    def test_pair_denominator_and_uncertainty_use_groups_not_draws(self):
        rows, records = self.fixture()
        metrics = analyze.view_metrics(records, rows, 4)
        self.assertEqual(metrics['both_targets_correct']['numerator'], 1)
        self.assertEqual(metrics['both_targets_correct']['denominator'], 8)
        self.assertEqual(metrics['both_targets_correct']['groups'], 2)
        self.assertEqual(metrics['correct_operator_switch']['numerator'], 1)
        self.assertEqual(metrics['same_ordered_expression_failure']['numerator'], 7)
        self.assertEqual(metrics['correct']['numerator'], 9)
        self.assertEqual(metrics['correct']['denominator'], 16)
        with self.assertRaisesRegex(ValueError, 'every frozen'):
            analyze.view_metrics(records[:-1], rows, 4)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            analyze.view_metrics(records+[records[0]], rows, 4)

    def test_rescue_and_loss_are_separate_paired_counts(self):
        frows, free = self.fixture('F', 1)
        hrows, hole = self.fixture('H', 1)
        free[0]['score']['correct'] = False
        hole[2]['score']['correct'] = False
        result = analyze.rescue_loss(free, hole, frows, hrows, 1)
        self.assertEqual(result['rescued_F_wrong_H_correct']['numerator'], 1)
        self.assertEqual(result['lost_F_correct_H_wrong']['numerator'], 1)
        self.assertEqual(result['H_minus_F']['mean'], 0)
        missing = analyze.analyze_generations({}, {'F': frows, 'H': hrows, 'C': []})
        self.assertTrue(all(v['metrics'] is None for v in missing['views']))

    def operator_record(self, target_index, group='g0', mass=0.2):
        probabilities = {'+': .1, '-': .7, '*': .1, '/': .1}
        if target_index:
            probabilities['+'], probabilities['-'] = probabilities['-'], probabilities['+']
        return dict(group_id=group, target_index=target_index,
                    correct_operator='+' if target_index else '-',
                    candidate_ids={op: [i] for i, op in enumerate(analyze.OPERATORS)},
                    candidate_probability_mass=mass,
                    candidates=[dict(operator=op, probability=p*mass,
                        normalized_probability=p, log_probability=math.log(p*mass))
                                for op, p in probabilities.items()])

    def test_D_goal_uses_paired_raw_log_odds_and_preserves_probability_mass(self):
        rows, _ = self.fixture()
        records = [self.operator_record(t, g) for g in ('g0', 'g1') for t in (0, 1)]
        result = analyze.operator_metrics(records, rows)
        self.assertAlmostEqual(result['D_goal']['mean'], 2*math.log(7))
        self.assertEqual(result['D_goal']['denominator'], 2)
        self.assertEqual(result['both_targets_correct_unique_argmax']['numerator'], 2)
        self.assertAlmostEqual(result['raw_candidate_probability_mass']['mean'], .2)
        self.assertAlmostEqual(result['context_results'][0]['correct_raw_probability'], .14)
        self.assertAlmostEqual(result['context_results'][0]['correct_candidate_normalized_probability'], .7)
        records[0]['candidate_probability_mass'] = 1
        with self.assertRaisesRegex(ValueError, 'mass differs'):
            analyze.operator_metrics(records, rows)

    def test_operator_unavailability_and_ties_do_not_become_correct_switches(self):
        rows, _ = self.fixture()
        record = self.operator_record(0)
        for candidate in record['candidates']:
            candidate.update(probability=.05, normalized_probability=.25, log_probability=math.log(.05))
        result = analyze.operator_metrics([record,
            dict(group_id='g0', target_index=1, status='unavailable', reason='token prefix mismatch')], rows)
        self.assertIsNone(result['D_goal']['mean'])
        self.assertFalse(result['context_results'][0]['correct_unique_argmax'])
        self.assertTrue(result['context_results'][0]['correct_in_argmax'])
        self.assertEqual(result['missing_contexts'], 2)
        self.assertEqual(result['available_contexts'], 1)
        record['candidate_ids']['+'] = [1, 2]
        record['candidate_ids']['-'] = [1]
        with self.assertRaisesRegex(ValueError, 'prefix-free'):
            analyze.operator_metrics([record], rows)


if __name__ == '__main__':
    unittest.main()
