import unittest
from experiments.sft_allocation_p008.forecast import forecasts,makespan
class ForecastTest(unittest.TestCase):
 def args(self):
  return [dict(committed_updates=256,training_update_seconds=400,other_worker_seconds=3600) for _ in range(8)],dict(four_gpu_verified=True,teacher_outputs=1024,teacher_batch_count=32,teacher_active_seconds=200,teacher_load_seconds=30,teacher_mean_prompt_output_tokens=380,teacher_batch_p95_seconds=10,phase0_cost_upper_usd=3),2.
 def test_dependency_and_tail_not_gpu_hours_divided(self):
  duration,lanes=makespan([10,1,1,1,10]);self.assertEqual(duration,11);self.assertEqual(len(lanes),4)
 def test_all_four_predeclared_forecasts(self):
  result=forecasts(*self.args());self.assertEqual(len(result['branches']),4);self.assertEqual(len(result['branches'][0]['student_seconds']),20)
  self.assertTrue(result['forecast_uses_no_main_outcomes']);self.assertEqual(result['branches'][0]['teacher_attempts_per_draw_forecast'],16384)
 def test_deadline_can_hold_without_scores(self):
  args=self.args();result=forecasts(args[0],args[1],18.);self.assertIsNone(result['selected'])
 def test_no_claim_of_capacity_from_submissions(self):
  args=self.args();args[1]['four_gpu_verified']=False
  with self.assertRaises(ValueError):forecasts(*args)
if __name__=='__main__':unittest.main()
