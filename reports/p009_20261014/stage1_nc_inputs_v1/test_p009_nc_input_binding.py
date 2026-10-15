"""New local input-boundary checks; no tokenizer, scorer or old oracle runs."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_p009_nc_inputs import physical_jsonl, checked_encoding, original_endpoint


class NCInputBoundaryTests(unittest.TestCase):
    def test_physical_jsonl_keeps_unicode_separator_inside_answer(self):
        row = {'response': 'first\u2028second\u2029last'}
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'source.jsonl'
            path.write_text(json.dumps(row, ensure_ascii=False)+'\n'+json.dumps(row)+'\n')
            self.assertEqual(physical_jsonl(path), [row, row])

    def test_original_lengths_and_answer_are_both_required(self):
        h = hashlib.sha256(b'answer').hexdigest()
        row = dict(problem_id='p', path_id='p::1', response='answer', source=dict(
            candidate_id='p::1', response_sha256=h, n_prompt=3, n_processed=7, n_supervised=4))
        encoded = dict(problem_id='p', path_id='p::1', response_hash=h,
                       n_prompt=3, n_processed=7, n_supervised=4)
        checked_encoding(row, encoded)
        changed = copy.deepcopy(row); changed['response'] = 'another'
        with self.assertRaises(ValueError):
            checked_encoding(changed, encoded)
        changed = dict(encoded, n_supervised=3)
        with self.assertRaises(ValueError):
            checked_encoding(row, changed)

    @staticmethod
    def prompts():
        return dict(n=1319, eos_token_id=151643, max_context=2048, max_new_tokens=512,
            prompts=[dict(problem_id=f'gsm8k/test/{i:05d}', input_ids=[42, 19]) for i in range(1319)])

    def test_endpoint_rejects_reordered_or_missing_original_ids(self):
        value = self.prompts()
        self.assertEqual(original_endpoint(value)[-1]['candidate_id'], 'NC::gsm8k/test/01318')
        value['prompts'][0], value['prompts'][1] = value['prompts'][1], value['prompts'][0]
        with self.assertRaises(ValueError):
            original_endpoint(value)
        value = self.prompts(); value['prompts'].pop()
        with self.assertRaises(ValueError):
            original_endpoint(value)

    def test_endpoint_rejects_invalid_tokens_without_retokenization(self):
        for ids in ([True], [151936], [], [0]*1537):
            value = self.prompts(); value['prompts'][0]['input_ids'] = ids
            with self.assertRaises(ValueError):
                original_endpoint(value)


if __name__ == '__main__':
    unittest.main()
