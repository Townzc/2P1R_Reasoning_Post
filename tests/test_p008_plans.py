import unittest
from unittest.mock import patch
from experiments.sft_allocation_p008.student_plans import common_plans
from experiments.sft_allocation_p008.contract import run_roster

class PlanTest(unittest.TestCase):
 def corpora(self):
  return {(r['draw'],r['budget_multiple'],r['price'],r['policy']):[
    dict(path_id='a',problem_id='p',n_supervised=4,n_processed=6,n_prompt=2),
    dict(path_id='b',problem_id='q',n_supervised=6,n_processed=8,n_prompt=2),
    dict(path_id='c',problem_id='r',n_supervised=10,n_processed=12,n_prompt=2)] for r in run_roster(4,False,1)}
 def test_all_cells_before_plan(self):
  c=self.corpora();c.pop(next(iter(c)))
  with self.assertRaises(ValueError):common_plans(c,(4,False,1))
 def test_common_downward_choice_not_one_sided(self):
  # Scaled CPU fixture creates odd nominal target with an even-length inventory.
  with patch('experiments.sft_allocation_p008.student_plans.BASE_TARGETS',2001),patch('experiments.sft_allocation_p008.student_plans.BASE_UPDATES',16):
   r=common_plans(self.corpora(),(4,False,1));self.assertEqual(r['dose_choices']['1']['realized'],2000)
   self.assertEqual(r['dose_choices']['4']['realized'],8004)
   self.assertEqual({p['supervised_targets'] for p in r['plans'].values() if p['run']['training_multiple']==1},{2000})
 def test_no_feasible_dose_is_hold(self):
  with patch('experiments.sft_allocation_p008.student_plans.BASE_TARGETS',999),patch('experiments.sft_allocation_p008.student_plans.BASE_UPDATES',16):
   with self.assertRaises(ValueError):common_plans(self.corpora(),(4,False,1))

if __name__=='__main__':unittest.main()
