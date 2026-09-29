import copy
from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.post_e037_goal_training import data
from src.countdown_smoke import safe_parse,value
from src.sft_data import sha256_file,read_jsonl


class CharacterTokenizer:
    eos_token_id=200000
    def encode(self,text,**kwargs):return list(map(ord,text))
    def decode(self,ids,**kwargs):return ''.join(map(chr,ids))
    def __call__(self,text,return_offsets_mapping=False,**kwargs):
        result={'input_ids':self.encode(text)}
        if return_offsets_mapping:result['offset_mapping']=[(i,i+1) for i in range(len(text))]
        return result


class GoalTrainingDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.excluded,cls.leakage=data.protected_identities()
        raw,cls.audit=data.make_groups(cls.excluded)
        cls.training=data.assign(raw)
        blocked=cls.excluded|{tuple(sorted(g['numbers'])) for g in raw}
        evaluation,_=data.make_groups(blocked,quotas=data.EVAL_QUOTAS,pool='eval')
        cls.evaluation=data.assign(evaluation,pool='eval')

    def test_exact_quotas_unique_groups_and_finite_generation(self):
        data.validate_groups(self.training,data.TRAIN_QUOTAS)
        data.validate_groups(self.evaluation,data.EVAL_QUOTAS)
        self.assertEqual(len(self.training),256);self.assertEqual(len(self.evaluation),48)
        self.assertEqual(Counter(t['expected_operator'] for g in self.training for t in g['targets']),{o:128 for o in data.OPS})
        self.assertEqual(Counter(g['hole_position'] for g in self.training),{'root':128,'internal':128})
        new={tuple(sorted(g['numbers'])) for g in self.training+self.evaluation}
        self.assertEqual(len(new),304);self.assertFalse(new&self.excluded)
        other,audit=data.make_groups(self.excluded)
        self.assertEqual(data.assign(other),self.training);self.assertEqual(audit,self.audit)
        with self.assertRaises(RuntimeError):data.make_groups(attempts_per_slot=0)

    def test_anchors_styles_and_display_order_are_stratified(self):
        audit=data.assignment_audit(self.training)
        for key in ('anchor_operator_by_position','style0_operator_by_position','index0_operator_by_position'):
            self.assertEqual(set(audit[key].values()),{32})
        self.assertTrue(0<audit['anchor_is_smaller_target']<256)
        for arm in ('single','paired'):
            rows=data.training_rows(self.training,arm)
            self.assertEqual(len(rows),512)
            counts=Counter((r['expected_operator'],r['hole_position'],r['rendering_id']) for r in rows)
            self.assertEqual(len(counts),16);self.assertEqual(set(counts.values()),{32})
            for group,a,b in zip(self.training,rows[::2],rows[1::2]):
                self.assertEqual((a['rendering_id'],b['rendering_id']),(0,1))
                if arm=='single':
                    self.assertEqual(a['target'],b['target']);self.assertEqual(a['expression'],b['expression'])
                    self.assertTrue(a['is_anchor'] and b['is_anchor'])
                else:self.assertNotEqual(a['target'],b['target'])
                self.assertNotIn('?',a['response']);self.assertNotIn('?',b['response'])
                self.assertEqual(a['response'].splitlines()[-1],'Answer: '+a['expression'])

    def test_ordered_ast_and_candidate_corruption_are_rejected(self):
        bad=copy.deepcopy(self.training)
        bad[0]['targets'][0]['expression']=bad[0]['targets'][1]['expression']
        with self.assertRaises(ValueError):data.validate_groups(bad,data.TRAIN_QUOTAS)
        bad=copy.deepcopy(self.training);bad[0]['candidate_values']['+']='999'
        with self.assertRaises(ValueError):data.validate_groups(bad,data.TRAIN_QUOTAS)
        for group in self.training+self.evaluation:
            self.assertEqual(len({t['target'] for t in group['targets']}),2)
            for target in group['targets']:
                values={op:value(safe_parse(group['template'].replace('?',op))) for op in data.OPS}
                self.assertEqual([op for op in data.OPS if values[op]==target['target']],[target['expected_operator']])

    def test_shared_surface_is_original_bytes_and_prompt_values(self):
        raw,rows=data.shared_surface()
        self.assertEqual(raw,data.SURFACE.read_bytes());self.assertEqual(len(rows),512)
        self.assertEqual(len({r['problem_id'] for r in rows}),256)
        self.assertEqual(Counter(r['rendering_id'] for r in rows),{0:256,1:256})
        self.assertEqual(rows,read_jsonl(data.SURFACE))

    def test_balanced_epoch_slots_and_same_F_positions(self):
        schedule=data.make_schedule();self.assertEqual(schedule,data.make_schedule())
        self.assertEqual(len(schedule),256)
        self.assertEqual(Counter(i for u in schedule for i in u),{i:4 for i in range(1024)})
        for update in schedule:
            self.assertEqual(len(update),16)
            self.assertTrue(all(i<512 for i in update[::2]))
            self.assertTrue(all(i>=512 for i in update[1::2]))
        bad=copy.deepcopy(schedule);bad[0][0]=bad[0][1]
        with self.assertRaises(ValueError):data.validate_schedule(bad)

    def test_fixed_train_and_midpoint_diagnostics_keep_seen_labels(self):
        training,mid=data.diagnostic_groups(self.training,self.evaluation)
        self.assertEqual(Counter((g['anchor_operator'],g['hole_position']) for g in training),
                         {(o,p):2 for o in data.OPS for p in ('root','internal')})
        self.assertEqual(Counter((tuple(g['operator_pair']),g['hole_position']) for g in mid),
                         {(o,p):1 for o in data.PAIRS for p in ('root','internal')})
        for interface in 'FH':
            rows=data.interface_rows(training,interface)
            self.assertEqual(len(rows),32);self.assertEqual(sum(r['single_target_supervised'] for r in rows),16)
            self.assertTrue(all(r['paired_target_supervised'] for r in rows))
            for a,b in zip(rows[::2],rows[1::2]):
                self.assertNotEqual(a['is_anchor'],b['is_anchor']);self.assertEqual(a['anchor_target_index'],b['anchor_target_index'])
        self.assertEqual(len(data.interface_rows(mid,'H')),24)

    def test_exclusions_use_public_identity_lists_not_sealed_bodies(self):
        original=Path.open
        def checked(path,*args,**kwargs):
            if any(s in str(path) for s in ('holdout.jsonl','holdout_','test_iid','dev_matched.jsonl','dev_broad.jsonl')):
                raise AssertionError('Sealed question body opened')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',checked):excluded,audit=data.protected_identities()
        self.assertEqual(excluded,self.excluded);self.assertEqual(audit['E037_number_groups_excluded'],24)
        self.assertFalse(audit['reserved_question_contents_read'])

    def test_freeze_hashes_ancestry_doses_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'release'
            with patch('scripts.audit_family_matching.verified_tokenizer',return_value=(CharacterTokenizer(),{'fixture':True})):
                manifest=data.prepare('fixture',output)
            inputs=data.load_inputs(output)
            self.assertEqual({k:len(inputs[k]) for k in ('single','paired','F','H','C','train_F','train_H','midpoint_H')},
                dict(single=1024,paired=1024,F=96,H=96,C=96,train_F=32,train_H=32,midpoint_H=24))
            self.assertEqual((output/'shared_F.jsonl').read_bytes(),data.SURFACE.read_bytes())
            self.assertEqual(inputs['single'][512:],inputs['paired'][512:])
            for actual,expected in zip(inputs['single'][512:],read_jsonl(data.SURFACE)):
                self.assertEqual({k:v for k,v in actual.items() if k!='interface'},expected)
            self.assertEqual(inputs['schedules']['single'],inputs['schedules']['paired'])
            self.assertEqual(inputs['learning_rates'],data.learning_rates(256))
            self.assertAlmostEqual(max(inputs['learning_rates']),5e-5)
            self.assertAlmostEqual(inputs['learning_rates'][-1],1e-5)
            for arm in ('single','paired'):
                dose=inputs['dose'][arm]
                self.assertEqual((dose['presentations'],dose['optimizer_updates'],dose['padding_tokens']),(4096,256,0))
                self.assertEqual(len(dose['encoded_row_sha256']),1024)
                self.assertEqual(dose['pools']['H']['presentations'],2048)
                self.assertEqual(dose['pools']['F']['presentations'],2048)
            support=json.loads((output/'TRAIN_TARGET_SUPPORT_AUDIT.json').read_text())
            self.assertFalse(support['E030_is_ancestor'])
            self.assertEqual(support['scopes']['E031_actual_ancestor_prep_control']['rows'],256)
            self.assertEqual(support['scopes']['single_actual_ancestor_plus_new_source_union']['rows'],1280)
            self.assertEqual(support['scopes']['single_new_H']['distinct_targets_per_multiset_histogram'],{'1':256})
            self.assertEqual(support['scopes']['paired_new_H']['distinct_targets_per_multiset_histogram'],{'2':256})
            self.assertEqual(len(data.load_operator_rows(output)),96)
            for name,expected in manifest['files_sha256'].items():self.assertEqual(sha256_file(output/name),expected)
            with self.assertRaises(FileExistsError):data.prepare('fixture',output)


if __name__=='__main__':unittest.main()
