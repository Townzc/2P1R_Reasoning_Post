"""New synthetic paired-question analysis checks; no actual outcome inputs."""
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('new_p010_analysis',Path('.local/p010_20261019/r1/p010_analysis_prepared.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
ids=[f'synthetic_{i}' for i in range(500)]
def vector(values,metric='greedy'):
 return dict(technical_unknown=0,complete=True,question_ids=ids,metric=metric,question_values=values,samples_per_question=4)
def comparison(name,left,right):return dict(name=name,left=left,right=right)
class PairedAnalysisChecks(unittest.TestCase):
 def test_identical_and_constant_effect_exact_intervals(self):
  v={'zero':vector([False]*500),'one':vector([True]*500)}
  r=a.paired_summary(v,[comparison('zero','zero','zero'),comparison('all','one','zero')],ids,'greedy')['contrasts']
  self.assertEqual(r[0]['pointwise_95_ci_pp'],[0.0,0.0]);self.assertEqual(r[1]['pointwise_95_ci_pp'],[100.0,100.0])
  self.assertEqual(r[1]['net_correct_count'],500);self.assertEqual(r[1]['discordant_questions'],500)
 def test_paired_draws_are_shared_and_order_independent(self):
  v={'a':vector([i%3==0 for i in range(500)]),'b':vector([i%5==0 for i in range(500)])}
  c=[comparison('ab','a','b'),comparison('ba','b','a')]
  r=a.paired_summary(v,c,ids,'greedy')['contrasts'];s=a.paired_summary(v,c[::-1],ids,'greedy')['contrasts']
  self.assertEqual(r,s[::-1]);self.assertAlmostEqual(r[0]['difference_pp'],-r[1]['difference_pp'])
  self.assertAlmostEqual(r[0]['pointwise_95_ci_pp'][0],-r[1]['pointwise_95_ci_pp'][1])
 def test_question_or_unknown_missing_cell_cannot_be_substituted(self):
  v=vector([False]*500);v['technical_unknown']=1
  with self.assertRaises(ValueError):a.paired_summary({'a':v},[comparison('x','a','a')],ids,'greedy')
  v=vector([False]*500)
  with self.assertRaises(ValueError):a.paired_summary({'a':v},[comparison('cancelled','a','missing')],ids,'greedy')
  v['question_ids']=ids[::-1]
  with self.assertRaises(ValueError):a.paired_summary({'a':v},[comparison('x','a','a')],ids,'greedy')
 def test_sample_mean_not_best_of_four(self):
  v={'a':vector([.25]*500,'sampled_mean_pass_at_1'),'b':vector([0]*500,'sampled_mean_pass_at_1')}
  r=a.paired_summary(v,[comparison('samples','a','b')],ids,'sampled_mean_pass_at_1')['contrasts'][0]
  self.assertEqual(r['difference_pp'],25.0);self.assertEqual(r['pointwise_95_ci_pp'],[25.0,25.0])
  self.assertNotIn('net_correct_count',r)
if __name__=='__main__':unittest.main()
