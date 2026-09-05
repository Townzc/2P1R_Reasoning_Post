import math
import tempfile
from pathlib import Path
import unittest

from src.sft_data import encode_row, prefix, update_schedule, budget_report
from src.countdown_smoke import build, make_pool
from src.evaluation import score_text, summarize


class CharTokenizer:
    eos_token_id = 2
    pad_token_id = 2
    def __call__(self, text, **kwargs):
        return {'input_ids': [ord(c)+3 for c in text],
                'offset_mapping': [(i,i+1) for i in range(len(text))]}


def row(response='Answer: 1+2+3+4', pid='p'):
    return {'problem_id':pid, 'prompt':'Make ten.', 'response':response, 'path_id':'a'}


class DataTests(unittest.TestCase):
    def test_response_mask_eos_and_first_prediction(self):
        r = encode_row(row(), CharTokenizer(), 256)
        first = len(prefix(row()['prompt']))
        self.assertEqual(r['labels'][:first], [-100]*first)
        self.assertEqual(r['labels'][first:], r['input_ids'][first:])
        self.assertEqual(r['labels'][-1], 2)
        self.assertEqual(r['n_supervised'], len(row()['response'])+1)

    def test_refuse_truncation_and_empty_response(self):
        with self.assertRaises(ValueError): encode_row(row(), CharTokenizer(), 10)
        with self.assertRaises(ValueError): encode_row(row(''), CharTokenizer(), 256)

    def test_boundary_crossing_refused(self):
        class CrossTokenizer(CharTokenizer):
            def __call__(self, text, **kw):
                out = super().__call__(text, **kw)
                b = len(prefix(row()['prompt']))
                if len(text) > b:
                    out['offset_mapping'][b-1] = (b-1,b+1)
                return out
        with self.assertRaises(ValueError): encode_row(row(), CrossTokenizer(), 256)

    def test_deterministic_exposure_across_epoch_boundary(self):
        a = update_schedule(3, 3, 2, 17)
        self.assertEqual(a, update_schedule(3,3,2,17))
        flattened = sum(a, [])
        self.assertEqual(sorted(flattened[:3]), [0,1,2])
        self.assertEqual(sorted(flattened[3:]), [0,1,2])

    def test_token_budget_counts_exposure_and_padding(self):
        rows = [encode_row(row('a','p'), CharTokenizer(),256), encode_row(row('abc','q'), CharTokenizer(),256)]
        report = budget_report(rows, [[0,1],[1,0]], 2)
        self.assertEqual(report['supervised_response_tokens'], 12)
        self.assertEqual(report['padding_tokens'], 4)
        self.assertEqual(report['problem_exposures'], {'p':2,'q':2})
        self.assertEqual(report['presentations'], 4)

    def test_finite_domain_and_existing_outputs_refused(self):
        with self.assertRaises(ValueError): make_pool(math.comb(20,4)+1,17)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileExistsError): build(Path(d),4,1,1,17)

    def test_generated_split_reproduction(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b'
            audit=build(a,4,1,1,17)
            build(b,4,1,1,17)
            self.assertTrue(audit['number_multiset_disjoint_splits'])
            self.assertEqual((a/'sha256.json').read_bytes(),(b/'sha256.json').read_bytes())


class EvaluationTests(unittest.TestCase):
    def test_expression_parse_and_correctness_are_separate(self):
        self.assertTrue(score_text('Answer: 1+2+3+4',[1,2,3,4],10)['correct'])
        wrong=score_text('Answer: 1+2+3+4',[1,2,3,4],24)
        self.assertTrue(wrong['parsed'])
        self.assertFalse(wrong['correct'])
        self.assertFalse(score_text('Answer: __import__("os")',[1,2,3,4],10)['parsed'])

    def test_multiple_answers_rejected(self):
        self.assertFalse(score_text('Answer: 1+2+3+4\nAnswer: 1+2+3+4',[1,2,3,4],10)['parsed'])

    def test_problem_macro_not_generation_micro(self):
        base={'parsed':True,'eos':True,'truncated':False,'output_tokens':2,'structure_id':None}
        predictions=[dict(base,problem_id='a',correct=True,structure_id='s')]
        predictions += [dict(base,problem_id='b',correct=False) for _ in range(3)]
        self.assertEqual(summarize(predictions)['accuracy_macro'],.5)


try:
    import torch
except ImportError:
    torch = None


@unittest.skipIf(torch is None, 'torch required; mandatory on training server')
class TorchTests(unittest.TestCase):
    def test_padding_same_id_as_eos_keeps_real_eos_label(self):
        from src.sft_data import collate
        rows=[encode_row(row('a'),CharTokenizer(),256),encode_row(row('abc'),CharTokenizer(),256)]
        batch=collate(rows,2)
        end=len(rows[0]['input_ids'])-1
        self.assertEqual(batch['labels'][0,end].item(),2)
        self.assertTrue(torch.all(batch['labels'][0,end+1:]==-100))
        self.assertTrue(torch.all(batch['attention_mask'][0,end+1:]==0))
        self.assertEqual(batch['input_ids'].shape[0],2)

    def test_accumulation_matches_combined_token_normalization(self):
        from src.sft_data import shifted_loss_sum
        torch.manual_seed(1)
        weights=torch.randn(3,7,requires_grad=True)
        features=torch.randn(2,5,3)
        labels=torch.tensor([[-100,-100,1,2,3],[-100,-100,-100,-100,4]])
        loss=shifted_loss_sum(features@weights,labels)/4
        loss.backward()
        expected=weights.grad.clone()
        weights.grad=None
        for i in range(2):
            (shifted_loss_sum(features[i:i+1]@weights,labels[i:i+1])/4).backward()
        torch.testing.assert_close(expected,weights.grad)

    def test_separate_batch_rows_do_not_attend_to_other_samples(self):
        import torch.nn.functional as F
        torch.manual_seed(3)
        q,k,v=(torch.randn(2,1,4,8) for _ in range(3))
        expected=F.scaled_dot_product_attention(q,k,v,is_causal=True)
        k[1]=1000; v[1]=-500
        actual=F.scaled_dot_product_attention(q,k,v,is_causal=True)
        torch.testing.assert_close(expected[0],actual[0])
