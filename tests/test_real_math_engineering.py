import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_real_math_engineering_outputs import audit_predictions
from src.real_math_engineering import numeric_final, score_completion, summarize, engineering_gate


class NumericCompletionTests(unittest.TestCase):
    def setUp(self):
        self.row = {'problem_id': 'fixture', 'prompt': 'Six plus six?', 'answer': '12',
                    'response': r'The result is \boxed{12}.'}

    def test_exact_scalar_equivalence_and_formatting(self):
        for final in ('12', '12.0', r'\frac{24}{2}', r'\text{12}'):
            self.assertTrue(score_completion(self.row, r'Work. \boxed{'+final+'}', True, False)['terminated_correct'])
        self.assertTrue(score_completion(self.row, 'Work.\n#### 12', True, False)['answer_correct'])

    def test_do_not_mine_working_or_join_numeric_tokens(self):
        for text in ('12', 'I computed 12 dollars.', r'\boxed{1 2}', r'\boxed{12 dollars}', r'\boxed{12%}', r'\boxed{12/0}'):
            self.assertFalse(score_completion(self.row, text, True, False)['answer_correct'])

    def test_last_marker_overrides_earlier_correct_working(self):
        for text in (r'\boxed{12} then \boxed{13}', '\\boxed{12}\n#### 13', r'#### 12 then \boxed{13}', r'\boxed{12} then \boxed{'):
            self.assertFalse(score_completion(self.row, text, True, False)['answer_correct'])

    def test_eos_truncation_and_specials_separate_from_numeric_answer(self):
        score = score_completion(self.row, r'\boxed{12}', False, True)
        self.assertTrue(score['answer_correct']); self.assertFalse(score['terminated_correct'])
        self.assertFalse(score_completion(self.row, r'<|im_end|>\boxed{12}', True, False)['answer_correct'])
        self.assertFalse(score_completion(self.row, r'\boxed{12}', True, False)['reasoning_validated'])

    def test_gate_requires_dose_profile_termination_and_nll(self):
        cfg = {'steps': 256, 'train_count': 32, 'overfit_required_correct': 31, 'overfit_max_nll': .1}
        stats = {'n': 32, 'terminated_correct': 31, 'truncated': 0}
        self.assertTrue(engineering_gate(cfg, 256, {'profile_complete': True}, stats, .01)['passed'])
        for steps, profile, sample, nll in [(255, True, stats, .01), (256, False, stats, .01),
                (256, True, {**stats, 'terminated_correct': 30}, .01),
                (256, True, {**stats, 'truncated': 1}, .01), (256, True, stats, float('nan')),
                (256, True, stats, .1)]:
            self.assertFalse(engineering_gate(cfg, steps, {'profile_complete': profile}, sample, nll)['passed'])

    def test_token_identity_and_score_tampering_block(self):
        class Tokens:
            eos_token_id = 2
            def __len__(self): return 300
            def decode(self, ids, **kwargs): return ''.join(chr(i-3) for i in ids)
        text = self.row['response']
        ids = [ord(c)+3 for c in text]+[2]
        pred = {**self.row, 'text': text, 'generated_ids': ids, 'generated_tokens': len(ids),
                'score': score_completion(self.row, text, True, False)}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'predictions.jsonl'
            path.write_text(json.dumps(pred)+'\n')
            self.assertEqual(len(audit_predictions(path, [self.row], Tokens(), {'max_new_tokens': 100})), 1)
            for mutation in ({'answer': '13'}, {'text': text+'x'}, {'generated_ids': [2]+ids},
                             {'score': {**pred['score'], 'terminated_correct': False}},
                             {'generated_ids': ids[:-1], 'generated_tokens': len(ids)-1}):
                path.write_text(json.dumps({**pred, **mutation})+'\n')
                with self.assertRaises(ValueError):
                    audit_predictions(path, [self.row], Tokens(), {'max_new_tokens': 100})


if __name__ == '__main__':
    unittest.main()
