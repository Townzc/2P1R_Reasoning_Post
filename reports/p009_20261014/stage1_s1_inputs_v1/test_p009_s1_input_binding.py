import copy
import unittest

from scripts.prepare_p009_s1_inputs import (
    P1_SCOPE, P1_TARGET, join_original_rows, original_endpoint, require_p1_review,
)


class S1InputBindingTests(unittest.TestCase):
    def test_real_G0_scope_and_independent_adjudication_are_required(self):
        value = dict(scope=P1_SCOPE, target_commit=P1_TARGET,
            decision='PASS_WITH_SEPARATE_ELIGIBILITY_AND_G0_DISPOSITIONS',
            teacher_labels_eligible_for_frozen_roster=True, raw_integrity_passed=True,
            labels_changed=False, independent_adjudication_decision='PASS-WITH-NOTES',
            adjudicated_sample_count=117, G0={'S1':dict(passed=True, teacher_correct=359,
                student_zero_correct=136, total=500, caps=[36,68], technical_unknown=0)})
        self.assertIs(require_p1_review(value), value)
        for key, replacement in [('labels_changed',True),('adjudicated_sample_count',50),
                                  ('teacher_labels_eligible_for_frozen_roster',False)]:
            bad=copy.deepcopy(value);bad[key]=replacement
            with self.assertRaises(ValueError):require_p1_review(bad)
        bad=copy.deepcopy(value);bad['G0']['S1']['passed']=False
        with self.assertRaises(ValueError):require_p1_review(bad)

    def test_unsupported_gold_stays_unscored_and_lineage_is_exact(self):
        raw=[dict(id=f'p{i}',untouched='original') for i in range(8993)]
        rows=[dict(id=x['id'],dataset='math_procurement',original_generation_record=x) for x in raw[:8989]]
        rows += [dict(id=f'e{i}',dataset='qwen_math_zero') for i in range(1500)]
        scores=[dict(id=x['id'],score={'original_boolean':True}) for x in rows]
        excluded=[dict(dataset='math_procurement',id=x['id'],original_record=x) for x in raw[8989:]]
        selected,unsupported=join_original_rows(rows,scores,excluded,raw)
        self.assertEqual(len(selected),8989);self.assertEqual(unsupported,['p8989','p8990','p8991','p8992'])
        self.assertIs(selected[0],scores[0])
        bad=copy.deepcopy(raw);bad[0]['untouched']='altered'
        with self.assertRaises(ValueError):join_original_rows(rows,scores,excluded,bad)
        missing=copy.deepcopy(scores);missing[-1]['id']='p8992'
        with self.assertRaises(ValueError):join_original_rows(rows,missing,excluded,raw)

    def test_endpoint_order_and_token_identity_are_preserved(self):
        gold=[dict(problem_id=f'm{i}') for i in range(500)]
        value=dict(n=500,eos_token_id=151643,max_context=2048,max_new_tokens=1024,
                   prompts=[dict(problem_id=x['problem_id'],input_ids=[1,2,3]) for x in gold])
        result=original_endpoint(value,gold)
        self.assertEqual([x['problem_id'] for x in result],[x['problem_id'] for x in gold])
        self.assertIs(result[0]['input_ids'],value['prompts'][0]['input_ids'])
        bad=copy.deepcopy(value);bad['prompts'][0],bad['prompts'][1]=bad['prompts'][1],bad['prompts'][0]
        with self.assertRaises(ValueError):original_endpoint(bad,gold)

    def test_endpoint_context_and_integer_tokens_fail_closed(self):
        gold=[dict(problem_id=f'm{i}') for i in range(500)]
        value=dict(n=500,eos_token_id=151643,max_context=2048,max_new_tokens=1024,
                   prompts=[dict(problem_id=x['problem_id'],input_ids=[1]) for x in gold])
        for tokens in ([True],[151936],[1]*1025):
            bad=copy.deepcopy(value);bad['prompts'][0]['input_ids']=tokens
            with self.assertRaises(ValueError):original_endpoint(bad,gold)


if __name__ == '__main__':
    unittest.main()
