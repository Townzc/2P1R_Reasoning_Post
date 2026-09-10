import unittest

from analyses.completion_contract import first_stop, completion_score


class CompletionContractTests(unittest.TestCase):
    @staticmethod
    def event(text, eos=False, cap=None):
        ids = list(text.encode()) + ([1000] if eos else [])
        return first_stop(ids, lambda xs: bytes(xs).decode(), 1000, cap or len(ids))

    def test_boundary_is_not_native_eos(self):
        event = self.event('Answer: 4\nProblem: new\nAnswer: 99', eos=True)
        self.assertEqual(event['stop_reason'], 'new_problem_boundary')
        self.assertFalse(event['actual_eos_at_stop'])
        result = completion_score({'answer': '4'}, event)
        self.assertTrue(result['task_answer_correct'])
        self.assertFalse(result['native_eos_correct'])
        self.assertFalse(result['marked']['clean_correct'])

    def test_stop_does_not_depend_on_gold(self):
        event = self.event('Answer: 4\n\tQuestion: new\nAnswer: 99')
        self.assertTrue(completion_score({'answer': '4'}, event)['task_answer_correct'])
        self.assertFalse(completion_score({'answer': '99'}, event)['task_answer_correct'])
        self.assertEqual(event['trigger_text'], '\tQuestion:')

    def test_early_boundary_is_not_answer_success(self):
        event = self.event('Problem: another question\nAnswer: 4')
        self.assertFalse(completion_score({'answer': '4'}, event)['task_answer_correct'])

    def test_conflicting_claims_still_fail(self):
        event = self.event('Answer: 4\n#### 5\nProblem: new')
        for gold in ('4', '5'):
            self.assertFalse(completion_score({'answer': gold}, event)['task_answer_correct'])

    def test_inline_and_incomplete_headers_do_not_stop(self):
        for text in ('An inline Problem: label\nAnswer: 4', 'Answer: 4\nProble'):
            event = self.event(text, eos=True)
            self.assertEqual(event['stop_reason'], 'native_eos')

    def test_boundary_split_across_tokens(self):
        pieces = {1: 'Answer: 4\n', 2: 'Prob', 3: 'lem', 4: ': ignored', 5: ' tail'}
        event = first_stop([1, 2, 3, 4, 5], lambda xs: ''.join(pieces[x] for x in xs), 1000, 5)
        self.assertEqual(event['retained_tokens'], 4)
        self.assertEqual(event['answer_segment'], 'Answer: 4\n')

    def test_length_cap_and_incomplete_stream(self):
        event = self.event('Answer: 4')
        self.assertFalse(completion_score({'answer': '4'}, event)['task_answer_correct'])
        with self.assertRaises(ValueError):
            self.event('Answer: 4', cap=100)

    def test_native_eos_wins_over_later_padding(self):
        event = first_stop([65, 1000, 66], lambda xs: bytes(xs).decode(), 1000, 3)
        self.assertEqual((event['stop_reason'], event['retained_tokens']), ('native_eos', 2))

    def test_special_token_is_not_a_successful_stop(self):
        ids = list(b'Answer: 4') + [1001]
        event = first_stop(ids, lambda xs: bytes(xs).decode(), 1000, len(ids), {1001})
        self.assertEqual(event['stop_reason'], 'invalid_special_token')
        self.assertFalse(completion_score({'answer': '4'}, event)['task_answer_correct'])

    def test_all_frozen_boundary_spelling_classes(self):
        for header in ('Q:', 'Question:', 'Problem:', '[Problem]', '[Question]'):
            with self.subTest(header=header):
                self.assertEqual(self.event('Answer: 4\n' + header + ' new')['stop_reason'],
                                 'new_problem_boundary')


if __name__ == '__main__':
    unittest.main()
