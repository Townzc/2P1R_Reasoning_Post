import copy
import json
from pathlib import Path
import tempfile
import unittest

from experiments.thursday_probe.arithmetic_eval import score
from experiments.thursday_probe.common import verify_manifest
from experiments.thursday_probe_v2.config import DATA, RELEASE
from experiments.thursday_probe_v2.resume_diagnostics import (
    RESUME_RELEASE, construction_error_breakdown, load_generation_rows,
    load_reference_rows, prepare_release, select_training_questions)
from src.sft_data import read_jsonl, sha256_file
from src.trace_audit import audit_trace


class ConstructionBreakdownTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(task='construct', numbers=[8, 25, 19, 21], target=42)
        self.text = ('Step 1: 25 - 19 = 6.\nStep 2: 8 * 6 = 48.\n'
                     'Step 3: 48 - 21 = 27.\nAnswer: (8 * (25 - 19)) - 21')

    def test_true_arithmetic_and_connected_expression_can_miss_target(self):
        before = copy.deepcopy(self.row)
        event = dict(answer_segment=self.text, stop_reason='native_eos')
        original = score(self.row, event)
        r = construction_error_breakdown(self.row, self.text, stop_reason='native_eos', output_tokens=70)
        self.assertTrue(r['parsed'])
        self.assertTrue(r['uses_input_multiset'])
        self.assertTrue(r['intermediate_arithmetic_consistent'])
        self.assertTrue(r['trace_final_value_consistent'])
        self.assertTrue(r['trace_final_expression_consistent'])
        self.assertFalse(r['trace_target_consistent'])
        self.assertFalse(r['reaches_target'])
        self.assertEqual(r['exact_value'], '27')
        self.assertEqual(r['resource_target_category'], 'resource_correct_target_wrong')
        self.assertEqual(r['complete_trace_status'], 'inconsistent')
        self.assertEqual(score(self.row, event), original)
        self.assertEqual(self.row, before)

    def test_resource_target_cross_table_and_missing_steps(self):
        cases = [('1+2+3+4', 10, 'both_satisfied'),
                 ('1+2+3+4', 11, 'resource_correct_target_wrong'),
                 ('10', 10, 'target_correct_resource_wrong'),
                 ('9', 10, 'both_wrong')]
        for expression, target, expected in cases:
            row = dict(task='construct', numbers=[1, 2, 3, 4], target=target)
            with self.subTest(expression=expression, target=target):
                result = construction_error_breakdown(row, 'Answer: '+expression)
                self.assertEqual(result['resource_target_category'], expected)
                self.assertIsNone(result['intermediate_arithmetic_consistent'])
                self.assertEqual(result['intermediate_arithmetic_status'], 'NA')

    def test_false_equation_is_independent_of_final_target(self):
        row = dict(self.row, target=27)
        result = construction_error_breakdown(row, self.text.replace('25 - 19 = 6', '25 - 19 = 7'))
        self.assertTrue(result['reaches_target'])
        self.assertFalse(result['intermediate_arithmetic_consistent'])
        self.assertEqual(result['resource_target_category'], 'both_satisfied')

    def test_unknown_grammar_and_unsupported_expressions_are_not_certified(self):
        result = construction_error_breakdown(self.row, 'I know the answer.\nAnswer: 42')
        self.assertIsNone(result['intermediate_arithmetic_consistent'])
        for text in ('Answer: __import__("os").system("bad")', 'Answer: 8**25',
                     'Answer: (8+', 'Answer: 1\nAnswer: 2'):
            with self.subTest(text=text):
                result = construction_error_breakdown(self.row, text)
                self.assertFalse(result['parsed'])
                self.assertIsNone(result['reaches_target'])
                self.assertEqual(result['resource_target_category'], 'unparseable')

    def test_exact_rationals_zero_division_and_cap_preserve_components(self):
        row = dict(task='construct', numbers=[1, 2, 3, 6], target=1)
        result = construction_error_breakdown(row, 'Answer: 1/2+3/6', stop_reason='length_cap')
        self.assertEqual(result['exact_value'], '1')
        self.assertTrue(result['reaches_target'])
        self.assertTrue(result['uses_input_multiset'])
        self.assertFalse(result['completed'])
        result = construction_error_breakdown(row, 'Answer: 1/(3-3)')
        self.assertTrue(result['parsed'])
        self.assertFalse(result['safely_executable'])
        self.assertIsNone(result['reaches_target'])
        self.assertEqual(result['resource_target_category'], 'undefined_value')


class FrozenSelectionTests(unittest.TestCase):
    def inputs(self):
        return (read_jsonl(DATA/'train_problems.jsonl'),
                json.loads((DATA/'assignment.json').read_text()),
                read_jsonl(RELEASE/'reference_identity_labels.jsonl'))

    def test_stratification_is_input_order_independent(self):
        problems, assignment, labels = self.inputs()
        selected, report = select_training_questions(problems, assignment, labels)
        reversed_result = select_training_questions(list(reversed(problems)), assignment,
                                                    list(reversed(labels)))
        self.assertEqual((selected, report), reversed_result)
        self.assertEqual(len({r['problem_id'] for r in selected}), 16)
        self.assertEqual([s['final_selected_count'] for s in report['strata']], [4]*4)
        self.assertEqual(report['fallback_selected_ids'], [])

    def test_small_support_uses_recorded_lexicographic_fallback(self):
        problems, assignment, labels = self.inputs()
        # A deliberately small CPU fixture exercises shortage handling only.
        subset = [r for r in problems if assignment[r['problem_id']] == 'A'][:20]
        ids = {r['problem_id'] for r in subset}
        selected, report = select_training_questions(subset, {pid: 'A' for pid in ids},
                                                     [l for l in labels if l['problem_id'] in ids])
        initial = {pid for group in report['strata'] for pid in group['initial_selected_ids']}
        self.assertEqual(report['fallback_selected_ids'], sorted(ids-initial)[:16-len(initial)])
        self.assertEqual(len(selected), 16)
        self.assertTrue(any(s['shortage'] for s in report['strata']))

    def test_release_is_immutable_and_references_are_connected(self):
        original = sha256_file(RELEASE/'manifest.json')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'release'
            manifest = prepare_release(output)
            self.assertEqual(manifest['generation_accounting']['planned_cumulative'], 4784)
            verify_manifest(output)
            selected = load_generation_rows(output)
            for family in ('A', 'B'):
                references = load_reference_rows(family, output)
                self.assertEqual([r['problem_id'] for r in references],
                                 [r['problem_id'] for r in selected])
                for row in references:
                    self.assertEqual(audit_trace(row['response'], row['numbers'], row['target'])[
                        'complete_trace_status'], 'verified')
            with self.assertRaises(FileExistsError):
                prepare_release(output)
            with (output/'train_diagnostic.jsonl').open('a') as stream:
                stream.write('{}\n')
            with self.assertRaises(ValueError):
                load_generation_rows(output)
        self.assertEqual(sha256_file(RELEASE/'manifest.json'), original)

    def test_published_selection_reconstructs_from_unchanged_sources(self):
        if not RESUME_RELEASE.exists():
            self.skipTest('Release has not yet been frozen')
        selected, report = select_training_questions(*self.inputs())
        self.assertEqual(load_generation_rows(), selected)
        self.assertEqual(json.loads((RESUME_RELEASE/'selection.json').read_text()), report)


if __name__ == '__main__':
    unittest.main()
