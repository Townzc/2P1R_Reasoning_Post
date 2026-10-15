import unittest
from copy import deepcopy
from experiments.learning_regime_p009.stage1_roster import math_first_attempt_inventory,nested_encoded_sets


def source(pid,key):return dict(problem_id=pid,question_sha256=key*64,problem='original question')
def raw(pid,attempt=1,stop='native_eos'):
    return dict(id=f'{pid}::attempt{attempt:02d}',problem_id=pid,attempt=attempt,
                stop=dict(stop_reason=stop,answer_segment='original whole answer'))
def score(row,correct=True):return dict(id=row['id'],score=dict(correct=correct,parsed=True,teacher_label_eligible=True))
def encoded(i,length=4):
    ids=[1,2]+[3]*(length-1)+[99]
    return dict(problem_id=f'p/{i}',path_id=f'p/{i}/a',input_ids=ids,labels=[-100]*2+ids[2:],
        n_prompt=2,n_supervised=length,n_processed=len(ids))

class RosterTests(unittest.TestCase):
    def test_first_original_duplicate_cannot_be_rescued(self):
        a,b=raw('a'),raw('b')
        out=math_first_attempt_inventory([source('a','a'),source('b','a')],[a,b],[score(a,False),score(b)],[])
        self.assertEqual(out['rows'],[]);self.assertEqual(out['duplicate_rows'],1)
    def test_later_correct_attempt_never_rescues_first(self):
        a,b=raw('a'),raw('a',2)
        out=math_first_attempt_inventory([source('a','a')],[a,b],[score(a,False),score(b)],[])
        self.assertEqual(out['rows'],[])
    def test_original_text_and_proof_preserved(self):
        a=raw('a');out=math_first_attempt_inventory([source('a','a')],[a],[score(a)],[])
        self.assertEqual(out['rows'][0]['response'],a['stop']['answer_segment']);self.assertFalse(out['runtime_admitted'])
    def test_boundary_and_unsupported_not_eligible(self):
        a,b=raw('a',stop='new_problem_boundary'),raw('b')
        out=math_first_attempt_inventory([source('a','a'),source('b','b')],[a,b],[score(a)],[b['id']])
        self.assertEqual(out['rows'],[])
    def test_missing_or_conflicting_labels_rejected(self):
        a=raw('a')
        for labels,missing in [([],[]),([score(a)],[a['id']]),([score(a),score(a)],[])]:
            with self.assertRaises(ValueError):math_first_attempt_inventory([source('a','a')],[a],labels,missing)
    def test_nested_permutation_stable_to_inventory_order(self):
        rows=[encoded(i) for i in range(3205)]
        a=nested_encoded_sets(rows,17,99);b=nested_encoded_sets(list(reversed(rows)),17,99)
        self.assertEqual(a['selections'],b['selections'])
        self.assertEqual(a['selections']['100']['problem_ids'],a['selections']['3200']['problem_ids'][:100])
        self.assertNotEqual(a['full_order'],nested_encoded_sets(rows,29,99)['full_order'])
    def test_no_smaller_n_or_zero_exposure_escape(self):
        with self.assertRaisesRegex(ValueError,'3200'):nested_encoded_sets([encoded(i) for i in range(3199)],17,99)
        with self.assertRaisesRegex(ValueError,'fixed dose'):nested_encoded_sets([encoded(i,700) for i in range(3200)],17,99)
    def test_nc_and_seeds(self):
        rows=[encoded(i) for i in range(3200)]
        self.assertEqual(set(nested_encoded_sets(rows,17,99,negative_control=True)['selections']),{'400','3200'})
        for seed in (True,31,29):
            with self.assertRaises(ValueError):nested_encoded_sets(rows,seed,99,negative_control=True)

if __name__=='__main__':unittest.main()
