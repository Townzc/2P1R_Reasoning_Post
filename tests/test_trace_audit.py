"""Independent trace-audit counterexamples, grammar limits and exact arithmetic."""
import unittest
from src.trace_audit import audit_trace, parse_expression


def trace(*lines, answer):
    return '\n'.join([f'Step {i}: {line}.' for i, line in enumerate(lines, 1)]+['Answer: '+answer])


class TraceAuditTest(unittest.TestCase):
    def test_valid_provenance_with_equal_values_and_duplicate_inputs(self):
        text = trace('2 + 2 = 4', '4 + 4 = 8', '8 * 3 = 24', answer='(((2 + 2) + 4) * 3)')
        result = audit_trace(text, [2, 2, 4, 3], 24)
        self.assertEqual(result['complete_trace_status'], 'verified')

    def test_correct_answer_does_not_repair_false_intermediate(self):
        text = trace('1 + 2 = 8', '8 + 3 = 11', '11 + 4 = 15', answer='((1 + 2) + (3 + 4))')
        result = audit_trace(text, [1, 2, 3, 4], 10)
        self.assertTrue(result['final_expression']['correct'])
        self.assertEqual(result['local_equations_status'], 'inconsistent')
        self.assertEqual(result['complete_trace_status'], 'inconsistent')

    def test_locally_correct_reused_number_is_not_valid(self):
        text = trace('1 + 1 = 2', '2 + 3 = 5', '5 + 4 = 9', answer='1 + 2 + 3 + 4')
        result = audit_trace(text, [1, 2, 3, 4], 10)
        self.assertEqual(result['local_equations_status'], 'consistent')
        self.assertEqual(result['resource_derivation_status'], 'inconsistent')

    def test_exact_rationals_and_negative_intermediate(self):
        text = trace('2 - 5 = -3', '(-3) / 6 = -1/2', '(-1/2) + 8 = 15/2', answer='(((2 - 5) / 6) + 8)')
        self.assertEqual(audit_trace(text, [2, 5, 6, 8], 7.5)['complete_trace_status'], 'verified')

    def test_roundoff_is_not_tolerated(self):
        text = trace('1 / 3 = 333/1000', answer='1 / 3')
        self.assertEqual(audit_trace(text, [1, 3], 1)['local_equations_status'], 'inconsistent')

    def test_zero_division_is_contradiction(self):
        result = audit_trace(trace('2 / 0 = 0', answer='2 / 0'), [2, 0], 0)
        self.assertEqual(result['local_equations_status'], 'inconsistent')

    def test_unknown_lines_are_not_verified(self):
        text = 'Somehow we solve it.\nAnswer: 1 + 2'
        self.assertEqual(audit_trace(text, [1, 2], 3)['complete_trace_status'], 'unverifiable')

    def test_no_trace_is_not_verified(self):
        result = audit_trace('Answer: 1 + 2', [1, 2], 3)
        self.assertTrue(result['final_expression']['correct'])
        self.assertEqual(result['complete_trace_status'], 'unverifiable')

    def test_unsupported_nested_step_is_locally_true_only(self):
        text = trace('(1 + 2) + 3 = 6', answer='(1 + 2) + 3')
        result = audit_trace(text, [1, 2, 3], 6)
        self.assertEqual(result['local_equations_status'], 'consistent')
        self.assertEqual(result['complete_trace_status'], 'unverifiable')

    def test_different_correct_final_tree_is_not_assumed_connected(self):
        text = trace('1 + 2 = 3', '3 + 3 = 6', answer='1 + (2 + 3)')
        result = audit_trace(text, [1, 2, 3], 6)
        self.assertEqual(result['resource_derivation_status'], 'verified')
        self.assertEqual(result['answer_connection_status'], 'ac_equivalent_only')
        self.assertEqual(result['complete_trace_status'], 'unverifiable')

    def test_wrong_target_with_valid_derivation(self):
        result = audit_trace(trace('1 + 2 = 3', answer='1 + 2'), [1, 2], 4)
        self.assertEqual(result['resource_derivation_status'], 'verified')
        self.assertEqual(result['complete_trace_status'], 'inconsistent')

    def test_unknown_trace_does_not_erase_wrong_final_target(self):
        result = audit_trace('Unsupported reasoning.\nAnswer: 1 + 2', [1, 2], 4)
        self.assertEqual(result['local_equations_status'], 'unverifiable')
        self.assertEqual(result['complete_trace_status'], 'inconsistent')
        self.assertIn('final_answer_violates_inputs_or_target', result['reasons'])

    def test_unknown_trace_does_not_erase_wrong_final_inputs(self):
        result = audit_trace('Unsupported reasoning.\nAnswer: 1 + 1', [1, 2], 2)
        self.assertTrue(result['final_expression']['reaches_target'])
        self.assertEqual(result['complete_trace_status'], 'inconsistent')

    def test_trace_size_limit_does_not_erase_wrong_final_answer(self):
        result = audit_trace('Unknown.\n' * 65 + 'Answer: 1 + 2', [1, 2], 4)
        self.assertIn('trace_size_limit', result['reasons'])
        self.assertEqual(result['complete_trace_status'], 'inconsistent')

    def test_resource_chain_disagrees_with_correct_final_value(self):
        text = trace('1 + 2 = 3', '3 + 3 = 6', answer='(1 + 2) * 3')
        result = audit_trace(text, [1, 2, 3], 9)
        self.assertTrue(result['final_expression']['correct'])
        self.assertEqual(result['resource_derivation_status'], 'verified')
        self.assertEqual(result['complete_trace_status'], 'inconsistent')
        self.assertIn('derivation_does_not_reach_target', result['reasons'])
        self.assertIn('derivation_answer_value_mismatch', result['reasons'])

    def test_wrong_target_chain_is_known_even_without_a_parseable_answer(self):
        text = trace('1 + 2 = 3', answer='unknown')
        result = audit_trace(text, [1, 2], 4)
        self.assertFalse(result['final_expression']['parsed'])
        self.assertEqual(result['resource_derivation_status'], 'verified')
        self.assertEqual(result['complete_trace_status'], 'inconsistent')
        self.assertIn('derivation_does_not_reach_target', result['reasons'])

    def test_same_value_non_ac_tree_remains_unverifiable(self):
        text = trace('1 * 3 = 3', answer='3 / 1')
        result = audit_trace(text, [1, 3], 3)
        self.assertTrue(result['final_expression']['correct'])
        self.assertEqual(result['resource_derivation_status'], 'verified')
        self.assertEqual(result['answer_connection_status'], 'no_exact_or_ac_tree_match')
        self.assertEqual(result['complete_trace_status'], 'unverifiable')
        self.assertNotIn('derivation_answer_value_mismatch', result['reasons'])

    def test_missing_step_and_bad_order(self):
        missing = audit_trace(trace('1 + 2 = 3', answer='1 + 2 + 3'), [1, 2, 3], 6)
        self.assertEqual(missing['resource_derivation_status'], 'inconsistent')
        bad = audit_trace('Answer: 1 + 2\nStep 1: 1 + 2 = 3.', [1, 2], 3)
        self.assertEqual(bad['complete_trace_status'], 'unverifiable')

    def test_surface_frames(self):
        for frame in ['We now calculate: {}.', 'Next, we obtain {}.', 'This calculation gives us {}.']:
            text = frame.format('1 + 2 = 3')+'\nAnswer: 1 + 2'
            self.assertEqual(audit_trace(text, [1, 2], 3)['complete_trace_status'], 'verified')

    def test_ast_rejects_code_and_numeric_extensions(self):
        for text in ['__import__("os").system("id")', 'x + 1', 'True + 1', '1.0 + 2', '2 ** 4', '[1][0]', '3 // 2', '2 << 10']:
            with self.subTest(text=text), self.assertRaises((ValueError, SyntaxError)):
                parse_expression(text)
        with self.assertRaises(ValueError): parse_expression('-1', final=True)
        with self.assertRaises(ValueError): parse_expression('9'*2050)

    def test_multiple_answers_never_verified(self):
        result = audit_trace('Step 1: 1 + 2 = 3.\nAnswer: 1 + 2\nAnswer: 1 + 2', [1, 2], 3)
        self.assertFalse(result['final_expression']['correct'])
        self.assertEqual(result['complete_trace_status'], 'unverifiable')


if __name__ == '__main__':
    unittest.main()
