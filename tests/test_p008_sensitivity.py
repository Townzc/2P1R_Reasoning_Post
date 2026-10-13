import unittest
from experiments.sft_allocation_p008.sensitivity import extract_v2,task_score_v2

class SensitivityTest(unittest.TestCase):
 def test_e2_empty_line_with_box(self):
  r=extract_v2('The answer is:\n\\boxed{30}')
  self.assertEqual(r['primary_parser']['status'],'unresolved_marked_answer');self.assertEqual(r['value'],'30')
 def test_e1_percentage_without_rescaling(self):
  for s in (r'\boxed{50%}',r'\boxed{50\%}'):
   self.assertEqual(extract_v2(s)['value'],'50')
 def test_no_unmarked_gold_search(self):
  self.assertEqual(extract_v2('The reasoning includes 30.\nThe answer is:')['status'],'unresolved_marked_answer')
 def test_conflicts_and_nonempty_failures_still_fail(self):
  for s in ('The answer is: unknown\n\\boxed{30}','The answer is: 20\n\\boxed{30}',r'\boxed{50%} \boxed{40%}'):
   self.assertNotEqual(extract_v2(s)['status'],'parsed')
 def test_unknown_units_not_guessed(self):
  self.assertNotEqual(extract_v2(r'\boxed{5 million}')['status'],'parsed')
 def test_truncation_still_incorrect(self):
  e=dict(answer_segment=r'\boxed{30}',stop_reason='length_cap')
  self.assertFalse(task_score_v2({'answer':'30'},e)['task_answer_correct'])
 def test_no_primary_mutation(self):
  r=extract_v2(r'\boxed{50%}');self.assertIsNone(r['primary_parser']['claims'][0]['value'])

if __name__=='__main__':unittest.main()
