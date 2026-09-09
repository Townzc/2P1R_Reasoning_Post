import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_pilot_structure_bias import identity_operations, checked_predictions, write_audit
from src.countdown_smoke import safe_parse
from src.evaluation import score_text


class PilotStructureBiasTests(unittest.TestCase):
    def events(self, expression):
        return identity_operations(safe_parse(expression))[1]

    def test_intermediate_one_and_zero_are_not_literal_input_tests(self):
        self.assertTrue(self.events('7 * (3 - 2)'))
        self.assertTrue(self.events('7 / (3 - 2)'))
        self.assertTrue(self.events('7 + ((4 + 2) - 6)'))
        self.assertTrue(self.events('7 - ((4 + 2) - 6)'))

    def test_operand_direction_and_absorbing_operations_are_not_identities(self):
        for expression in ('0 - 7', '1 / 7', '7 * 0', '7 / 7', '7 - 7'):
            with self.subTest(expression=expression):
                self.assertEqual(self.events(expression), [])

    def test_one_or_zero_in_input_does_not_imply_identity(self):
        self.assertEqual(self.events('(1 + 2) * (3 + 4)'), [])
        self.assertEqual(self.events('(0 - 2) / (3 + 4)'), [])

    def test_both_sides_of_commutative_identities_and_nested_event(self):
        for expression in ('1 * 7', '7 * 1', '0 + 7', '7 + 0'):
            self.assertEqual(len(self.events(expression)), 1)
        event = self.events('(7 * (3 - 2)) / 9')[0]
        self.assertEqual(event['node_address'], 'L')
        self.assertEqual(event['right_value'], '1')

    def test_exact_fraction_evaluation_avoids_roundoff_false_negative(self):
        self.assertEqual(len(self.events('7 * ((1 / 3) + (2 / 3))')), 1)
        self.assertEqual(self.events('7 * ((1 / 3) + (1 / 3))'), [])

    def test_division_by_zero_is_invalid_not_a_neutral_operation(self):
        with self.assertRaises(ZeroDivisionError):
            self.events('7 / (2 - 2)')

    def prediction(self):
        reference = {'problem_id': 'example', 'numbers': [1, 2, 3, 4],
                     'target': 10, 'prompt': 'Example'}
        text = 'Answer: ((1 + 2) + (3 + 4))'
        prediction = {**reference, 'text': text, 'sample_index': 0,
                      **score_text(text, reference['numbers'], reference['target'])}
        return reference, prediction

    def test_saved_corrupt_correctness_and_duplicate_samples_are_rejected(self):
        reference, prediction = self.prediction()
        with self.assertRaisesRegex(ValueError, 'correctness'):
            checked_predictions([dict(prediction, correct=False)], [reference], 1)
        with self.assertRaisesRegex(ValueError, 'sample indices'):
            checked_predictions([prediction, prediction], [reference], 2)
        with self.assertRaisesRegex(ValueError, 'unknown problem'):
            checked_predictions([dict(prediction, problem_id='other')], [reference], 1)

    def test_missing_problem_and_prompt_mismatch_are_rejected(self):
        reference, prediction = self.prediction()
        with self.assertRaisesRegex(ValueError, 'sample indices'):
            checked_predictions([], [reference], 1)
        with self.assertRaisesRegex(ValueError, 'prompt'):
            checked_predictions([dict(prediction, target=11)], [reference], 1)

    def test_output_cannot_overwrite_prior_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'audit'
            write_audit(out, {'status': 'original'}, [{'problem_id': 'first'}])
            with self.assertRaises(FileExistsError):
                write_audit(out, {'status': 'changed'}, [])
            self.assertEqual(json.loads((out / 'summary.json').read_text())['status'], 'original')


if __name__ == '__main__':
    unittest.main()
