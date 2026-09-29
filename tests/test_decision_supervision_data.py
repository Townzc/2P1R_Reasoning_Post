from collections import Counter
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.post_e039_decision_supervision import data
from src.sft_data import read_jsonl, sha256_file, encode_row


class CharacterTokenizer:
    eos_token_id=200000
    def __call__(self,text,return_offsets_mapping=False,**kwargs):
        result={'input_ids':list(map(ord,text))}
        if return_offsets_mapping:result['offset_mapping']=[(i,i+1) for i in range(len(text))]
        return result


class DecisionDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=data.previous.load_inputs()
        cls.groups=read_jsonl(data.PRIOR/'train_groups.jsonl')
        cls.tokenizer=CharacterTokenizer()

    def test_actual_F_prompt_token_dedup_and_fixed_nested_subsets(self):
        rows,end,mid,audit=data.unique_f_prompts(self.old['single'][512:],self.tokenizer)
        self.assertEqual((len(rows),len(end),len(mid)),(256,64,16))
        self.assertEqual(audit['source_rows_per_prompt'],{'2':256})
        self.assertEqual(set(r['problem_id'] for r in mid)&set(r['problem_id'] for r in end),set(r['problem_id'] for r in mid))
        for row in rows:
            originals=[self.old['single'][512+i] for i in row['source_F_row_indices']]
            self.assertTrue(all(row['prompt']==r['prompt'] for r in originals))
            self.assertEqual(row['reference_responses'],[r['response'] for r in originals])
            self.assertTrue(row['actual_F_replay_training_prompt']);self.assertFalse(row['H_transfer_view'])
        other=data.unique_f_prompts(self.old['single'][512:],self.tokenizer)
        self.assertEqual((rows,end,mid,audit),other)
        bad=copy.deepcopy(self.old['single'][512:]);bad[1]['target']+=1
        with self.assertRaises(ValueError):data.unique_f_prompts(bad,self.tokenizer)

    def test_H32_stratification_and_H8_nested_targets_are_fixed(self):
        selected,mid,audit=data.select_h_groups(self.groups)
        self.assertEqual((len(selected),len(mid),len(audit['H32_stratum_quotas'])),(32,8,24))
        self.assertEqual(Counter((g['anchor_operator'],g['hole_position']) for g in selected),
                         {(o,p):4 for o in data.previous.OPS for p in ('root','internal')})
        self.assertEqual(Counter((g['anchor_operator'],g['hole_position']) for g in mid),
                         {(o,p):1 for o in data.previous.OPS for p in ('root','internal')})
        self.assertTrue({g['group_id'] for g in mid}<={g['group_id'] for g in selected})
        rows=data.reference_rows(selected,'H',self.old)
        self.assertEqual(len(rows),64);self.assertEqual(sum(r['is_anchor'] for r in rows),32)
        for row in rows:
            self.assertEqual(bool(row['training_references']['single']),row['is_anchor'])
            self.assertEqual(len(row['training_references']['single']),2 if row['is_anchor'] else 0)
            self.assertEqual(len(row['training_references']['paired']),1)
            self.assertEqual(row['single_target_supervised'],row['is_anchor'])

    def test_fresh_pool_excludes_all_prior_and_preserves_pair_position_quotas(self):
        excluded,audit=data.protected_identities()
        for filename in ('train_groups','eval_groups'):
            self.assertTrue({tuple(sorted(r['numbers'])) for r in read_jsonl(data.PRIOR/(filename+'.jsonl'))}<=excluded)
        new,selection=data.previous.make_groups(excluded,quotas=data.previous.EVAL_QUOTAS,pool='decision_eval',seed=data.SEEDS['data'])
        data.previous.validate_groups(new,data.previous.EVAL_QUOTAS)
        self.assertFalse({tuple(sorted(g['numbers'])) for g in new}&excluded)
        self.assertEqual(Counter(g['hole_position'] for g in new),{'root':24,'internal':24})
        self.assertFalse(audit['reserved_question_contents_read'])

    def test_128_updates_inherit_first_two_exact_epochs_and_learning_rate_recipe(self):
        schedule=data.continuation_schedule()
        self.assertEqual(schedule,self.old['schedules']['single'][:128])
        self.assertEqual(Counter(i for batch in schedule for i in batch),{i:2 for i in range(1024)})
        lrs=data.learning_rates(128)
        self.assertEqual(len(lrs),128);self.assertEqual(lrs[7],5e-5);self.assertEqual(lrs[-1],1e-5)
        bad=copy.deepcopy(schedule);bad[0][0]=bad[0][1]
        with self.assertRaises(ValueError):data.validate_schedule(bad)

    def test_freeze_preserves_all_original_bytes_masks_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/'release'
            with patch('scripts.audit_family_matching.verified_tokenizer',return_value=(self.tokenizer,{'fixture':True})):
                manifest=data.prepare('fixture',folder)
            inputs=data.load_inputs(folder)
            for name in ('single','paired','shared_F'):
                self.assertEqual((folder/(name+'.jsonl')).read_bytes(),(data.PRIOR/(name+'.jsonl')).read_bytes())
            counts={k:len(inputs[k]) for k in ('single','paired','spans_single','spans_paired','eval_H','eval_F','train_H','train_F','train_F64','midpoint_H','midpoint_F')}
            self.assertEqual(counts,dict(single=1024,paired=1024,spans_single=1024,spans_paired=1024,eval_H=96,eval_F=96,train_H=64,train_F=256,train_F64=64,midpoint_H=16,midpoint_F=16))
            self.assertEqual(manifest['planned_generations'],4736)
            for arm in ('single','paired'):
                dose=inputs['dose'][arm]
                self.assertEqual((dose['optimizer_updates'],dose['presentations'],dose['decision_tokens_presented']),(128,2048,1024))
                self.assertAlmostEqual(dose['normalized_weight_mass'],dose['raw_supervised_denominator'])
                self.assertEqual(data.load_span_rows(arm,folder),inputs['spans'][arm])
            for pool,count in [('eval',96),('train32',64),('midpoint',16)]:
                contexts=data.load_candidate_contexts(folder,pool=pool)
                self.assertEqual(len(contexts),count)
                self.assertTrue(all(c['all_candidate_prefixes_identical'] for c in contexts))
            self.assertEqual(len(data.load_span_rows('train_F',folder)),256)
            for name,expected in manifest['files_sha256'].items():self.assertEqual(sha256_file(folder/name),expected)
            with self.assertRaises(FileExistsError):data.prepare('fixture',folder)


if __name__=='__main__':unittest.main()
