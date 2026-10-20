import unittest
from scripts.prepare_p010_e9_inputs import inspect_cell

def pair(length=10,targets=5):
 return [dict(problem_id='p',path_id='a')],[dict(problem_id='p',path_id='a',input_ids=[1,100257],labels=[-100,100257],n_processed=length,n_supervised=targets)]
class E9(unittest.TestCase):
 def test_full_long_answer_retained_and_blocks(self):
  r,e=pair(2049);v=inspect_cell(r,e,1);self.assertFalse(v['planning_allowed']);self.assertEqual(v['omitted_answers'],0);self.assertEqual(len(v['whole_context_unsupported']),1)
 def test_full_coverage_overdose_blocks_without_reduction(self):
  r,e=pair(targets=2097149);v=inspect_cell(r,e,1);self.assertFalse(v['planning_allowed']);self.assertEqual(v['once_each_targets'],2097149)
 def test_original_ids_and_native_eos_required(self):
  r,e=pair();self.assertTrue(inspect_cell(r,e,1)['planning_allowed']);e[0]['input_ids'][-1]=151643
  with self.assertRaises(ValueError):inspect_cell(r,e,1)
if __name__=='__main__':unittest.main()
