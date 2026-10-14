import copy
import json
import unittest

from analyses.completion_contract import first_stop
from experiments.learning_regime_p009.p0_stop_metadata import raw_checked


class StopMetadataTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(problem_id='gsm8k/test/00115', input_ids=[5, 6])
        self.tie = dict(problem_id=self.row['problem_id'], prompt_token_ids=[5, 6],
                        token_ids=[12]*511+[151643], backend_text='unaltered',
                        finish_reason='length', stop_reason=None)

    def test_exact_cap_native_eos_preserves_original_bytes_and_object(self):
        rows = [self.tie]
        before = json.dumps(rows, sort_keys=True)
        self.assertIs(raw_checked([self.row], rows), rows)
        self.assertEqual(json.dumps(rows, sort_keys=True), before)

    def test_frozen_logical_stop_retains_real_eos_at_cap(self):
        event = first_stop(self.tie['token_ids'], lambda _: 'unscored text', 151643, 512)
        self.assertEqual(event['stop_reason'], 'native_eos')
        self.assertEqual(event['retained_tokens'], 512)
        self.assertTrue(event['actual_eos_at_stop'])

    def test_short_length_eos_is_not_the_documented_tie(self):
        self.tie['token_ids'] = [12, 151643]
        with self.assertRaises(ValueError):
            raw_checked([self.row], [self.tie])

    def test_post_eos_or_duplicate_eos_rejected(self):
        for ids in ([12]*510+[151643, 13], [12]*510+[151643, 151643]):
            raw = copy.deepcopy(self.tie)
            raw['token_ids'] = ids
            with self.assertRaises(ValueError):
                raw_checked([self.row], [raw])

    def test_missing_terminal_eos_does_not_complete_short_stream(self):
        self.tie['token_ids'] = [12]*511
        with self.assertRaises(ValueError):
            raw_checked([self.row], [self.tie])

    def test_cap_tie_nonnull_stop_reason_rejected(self):
        self.tie['stop_reason'] = 151643
        with self.assertRaises(ValueError):
            raw_checked([self.row], [self.tie])

    def test_existing_native_eos_and_genuine_length_remain_valid(self):
        for ids, finish in (([12, 151643], 'stop'), ([12]*512, 'length')):
            raw = copy.deepcopy(self.tie)
            raw.update(token_ids=ids, finish_reason=finish)
            raw_checked([self.row], [raw])

    def test_tie_does_not_bypass_prompt_identity_or_token_validation(self):
        changes = ({'problem_id': 'different'}, {'prompt_token_ids': [6, 5]},
                   {'token_ids': [False]+[12]*510+[151643]},
                   {'token_ids': [151936]+[12]*510+[151643]})
        for change in changes:
            raw = copy.deepcopy(self.tie)
            raw.update(change)
            with self.assertRaises(ValueError):
                raw_checked([self.row], [raw])


if __name__ == '__main__':
    unittest.main()
