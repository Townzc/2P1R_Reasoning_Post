import copy
from pathlib import Path
import unittest

from experiments.post_e039_decision_supervision import decision_spans as spans
from src.sft_data import read_jsonl, encode_row


class CharacterTokenizer:
    eos_token_id=200000
    def __call__(self,text,return_offsets_mapping=False,**kwargs):
        result={'input_ids':list(map(ord,text))}
        if return_offsets_mapping:result['offset_mapping']=[(i,i+1) for i in range(len(text))]
        return result


class DecisionSpanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=Path('experiments/post_e037_goal_training/release_v1')
        cls.rows={arm:read_jsonl(base/(arm+'.jsonl')) for arm in ('single','paired')}
        cls.tokenizer=CharacterTokenizer()

    def test_all1024_original_H_references_first_causal_semantic_position(self):
        for arm in self.rows:
            for row in self.rows[arm][:512]:
                record=spans.annotate(row,self.tokenizer);encoded=encode_row(row,self.tokenizer,1024)
                self.assertTrue(spans.validate_mask(encoded,record))
                self.assertEqual(record['status'],'valid_first_semantic_decision')
                self.assertEqual(record['decision_token_count'],1)
                self.assertEqual(record['earlier_hole_dependent_atoms'],0)
                self.assertFalse(record['prior_leakage'])
                start,end=record['response_char_span']
                self.assertEqual(row['response'][start:end],row['correct_operator'])
                self.assertLess(end,row['response'].index('Answer:'))
                self.assertEqual(record['causal_logit_indices'],[record['decision_token_indices'][0]-1])
                self.assertFalse(record['decision_mask'][-1])
                self.assertFalse(any(record['decision_mask'][:encoded['n_prompt']]))
                self.assertEqual({op:r['token_ids'] for op,r in record['candidates'].items()},
                                 {op:[ord(op)] for op in spans.OPS})
                earlier=[a for a in record['semantic_atoms'] if a['response_char_span'][0]<start]
                self.assertFalse(any(a['depends_on_hole'] for a in earlier))

    def test_late_answer_or_mutated_reference_cannot_silently_become_mask(self):
        row=copy.deepcopy(self.rows['single'][0]);row['response']='Answer: '+row['expression']
        with self.assertRaises(ValueError):spans.annotate(row,self.tokenizer)
        row=copy.deepcopy(self.rows['single'][0]);row['hole_path']=[2]
        with self.assertRaises(ValueError):spans.annotate(row,self.tokenizer)
        row=copy.deepcopy(self.rows['single'][0]);row['correct_operator']='/'
        with self.assertRaises(ValueError):spans.annotate(row,self.tokenizer)

    def test_changed_mask_identity_and_causal_shift_are_rejected(self):
        row=self.rows['paired'][20];encoded=encode_row(row,self.tokenizer,1024)
        record=spans.annotate(row,self.tokenizer)
        bad=copy.deepcopy(record);bad['decision_mask'][-1]=True
        with self.assertRaises(ValueError):spans.validate_mask(encoded,bad)
        bad=copy.deepcopy(record);bad['causal_logit_indices']=bad['decision_token_indices']
        with self.assertRaises(ValueError):spans.validate_mask(encoded,bad)
        bad=copy.deepcopy(encoded);bad['labels'][0]=0
        with self.assertRaises(ValueError):spans.validate_mask(bad,record)

    def test_F_original_program_and_copy_masks_are_diagnostic_only(self):
        for row in self.rows['single'][512:]:
            record=spans.annotate(row,self.tokenizer)
            self.assertEqual(record['status'],'F_decomposition_only')
            self.assertFalse(any(record['decision_mask']))
            self.assertEqual(sum(record['program_operator_mask']),6)
            self.assertGreater(sum(record['input_copy_mask']),0)
            self.assertGreater(sum(record['computed_numeric_mask']),0)
            self.assertEqual(record['semantic_prefix_dead_end'],'unknown_without_strict_completion_certificate')


if __name__=='__main__':unittest.main()
