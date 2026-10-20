"""New synthetic endpoint/answer-region/paired-statistic checks only."""
import unittest
from experiments.p011 import long_evaluation as le
from experiments.learning_regime_p009.math_scoring import last_box, decide
from experiments.sft_allocation_midpoint.common import digest


class LongEvaluationDraft(unittest.TestCase):
    @staticmethod
    def benchmarks():
        return [dict(benchmark=k, source_row=i, problem=f'{k} question{i}', answer='1')
                for k,n in le.BENCHMARK_COUNTS.items() for i in range(n)]

    class Tokenizer:
        def apply_chat_template(self, messages, tokenize, add_generation_prompt):
            assert not tokenize and add_generation_prompt and len(messages) == 1
            assert messages[0]['role'] == 'user'
            return '<native>' + messages[0]['content']
        def __call__(self, text, add_special_tokens):
            assert not add_special_tokens
            return {'input_ids': [1,2,3]}

    def test_full_roster_seeds_and_no_truncation(self):
        rows = le.request_roster(self.benchmarks(), self.Tokenizer())
        self.assertEqual(len(rows), 3300)
        self.assertEqual(len({r['id'] for r in rows}), 3300)
        self.assertEqual([r['seed'] for r in rows[:4]], list(range(4)))
        self.assertEqual(rows[4]['mode'], 'greedy')
        self.assertEqual(rows[0]['required_context'], 16387)
        s = le.sampling(rows[0], [151645,151643])
        self.assertEqual((s['temperature'],s['top_p'],s['max_tokens']),(.6,.95,16384))
        self.assertIsNone(s['stop'])
        self.assertFalse(s['skip_special_tokens'])

    def test_duplicate_missing_gold_or_missing_endpoint_rejected(self):
        for mutation in ('duplicate','gold','missing'):
            b = self.benchmarks()
            if mutation == 'duplicate': b[1]['source_row'] = 0
            elif mutation == 'gold': b[0]['answer'] = ''
            else: b.pop()
            with self.assertRaises(ValueError): le.request_roster(b, self.Tokenizer())

    def test_final_think_boundary_and_full_no_think_text(self):
        self.assertEqual(le.answer_region('a</think>b</think>final'), 'final')
        original = r'\boxed{1}' + 'z' * 3000
        self.assertEqual(le.answer_region(original), original)
        self.assertEqual(last_box(le.answer_region(original))['answer'], '1')
        self.assertEqual(last_box(le.answer_region(r'\boxed{1}</think>none'))['status'], 'no_box')
        self.assertEqual(last_box(le.answer_region(r'</think>\boxed{1} then \boxed{'))['status'], 'unclosed_last_box')

    def test_cap_remains_wrong_and_unknown_is_not_zero(self):
        r = dict(id='one',gold='1')
        o = {'id':'one','request_sha256':digest(r),'stop_reason':'length_cap','answer_text':r'</think>\boxed{1}'}
        row = le.scoring_rows([r], {'one':o})[0]
        score = decide(row['gold'],last_box(row['answer_segment']),{'status':'compared','equivalent':True},stop_reason=row['stop_reason'])
        self.assertFalse(score['correct'])
        o['stop_reason'] = 'unknown'
        with self.assertRaises(ValueError): le.scoring_rows([r], {'one':o})

    def test_question_level_constant_difference_and_exact_four_samples(self):
        a = {str(i):[False]*4 for i in range(500)}
        b = {str(i):[True,False,False,False] for i in range(500)}
        out = le.paired_question_interval(a,b)
        self.assertEqual(out['difference_pp'],25.)
        self.assertEqual(out['ci95_pp'],[25.,25.])
        b['0'] = [True]
        with self.assertRaises(ValueError): le.paired_question_interval(a,b)


if __name__ == '__main__': unittest.main()
