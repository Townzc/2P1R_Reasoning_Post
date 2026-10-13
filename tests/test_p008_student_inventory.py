import copy
import unittest
from experiments.sft_allocation_p008.student_inventory import training_rows


def fixture():
    parents=[dict(id='q1',problem='p\u2028text',answer='3',reference='reference'),
             dict(id='q2',problem='other',answer='4',reference='reference2')]
    row=dict(problem_id='q1',candidate_id='a1',attempt=1,usable=True,
             score=dict(clean_correct=True),usable_duplicate_of=None,
             stop=dict(eos=True,truncated=False),text='whole teacher answer')
    return parents,['q1'],[row]


class InventoryTests(unittest.TestCase):
    def test_exact_identity_metadata_and_text_preserved(self):
        a=fixture();original=copy.deepcopy(a);rows=training_rows(*a)
        self.assertEqual(a,original)
        self.assertEqual(rows[0]['group_id'],rows[0]['problem_id'])
        self.assertEqual(rows[0]['prompt'],a[0][0]['problem'])
        self.assertEqual(rows[0]['response'],a[2][0]['text'])
        self.assertEqual(rows[0]['answer'],a[0][0]['answer'])

    def test_every_usable_answer_retained(self):
        a=fixture();a[2].append(dict(a[2][0],candidate_id='a2',attempt=2,text='second full answer'))
        self.assertEqual([r['path_id'] for r in training_rows(*a)],['a1','a2'])

    def test_existing_score_and_attempt_checks_preserved(self):
        for field,value in [('usable',None),('attempt',2),('usable_duplicate_of','prior')]:
            a=fixture();a[2][0][field]=value
            with self.assertRaises(ValueError):training_rows(*a)

    def test_foreign_group_schema_not_silently_accepted(self):
        a=fixture();a[0][0]['group_id']='foreign'
        with self.assertRaises(ValueError):training_rows(*a)

    def test_reference_is_not_training_response(self):
        a=fixture();a[0][0]['reference']='a different reference'
        self.assertEqual(training_rows(*a)[0]['response'],a[2][0]['text'])


if __name__=='__main__':unittest.main()
