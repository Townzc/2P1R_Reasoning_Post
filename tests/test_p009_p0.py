import copy
import unittest
from experiments.learning_regime_p009.p0_contract import (
    raw_checked, prompts_checked, remaining_forecast, cost_cents, RESERVED_CENTS)


class P0ContractTests(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(problem_id='gsm8k/test/00000',input_ids=[1,2])]
        self.raw=[dict(problem_id='gsm8k/test/00000',prompt_token_ids=[1,2],
                       token_ids=[12,151643],finish_reason='stop',stop_reason=151643)]

    def test_native_eos_preserved(self):
        self.assertEqual(raw_checked(self.rows,self.raw),self.raw)

    def test_missing_eos_not_invented(self):
        self.raw[0]['token_ids']=[12]
        with self.assertRaises(ValueError):raw_checked(self.rows,self.raw)

    def test_length_cap_is_a_complete_raw_response(self):
        self.raw[0].update(token_ids=[12]*512,finish_reason='length',stop_reason=None)
        raw_checked(self.rows,self.raw)

    def test_wrong_prompt_or_reordered_identity_rejected(self):
        for field,value in [('problem_id','gsm8k/test/00001'),('prompt_token_ids',[2,1])]:
            raw=copy.deepcopy(self.raw);raw[0][field]=value
            with self.assertRaises(ValueError):raw_checked(self.rows,raw)

    def test_no_post_eos_token(self):
        self.raw[0]['token_ids']=[12,151643,13]
        with self.assertRaises(ValueError):raw_checked(self.rows,self.raw)

    def test_no_duplicate_endpoint(self):
        value=dict(n=1319,eos_token_id=151643,max_context=2048,max_new_tokens=512,
                   prompts=[dict(problem_id=f'gsm8k/test/{i:05d}',input_ids=[12]) for i in range(1319)])
        prompts_checked(value)
        value['prompts'][-1]=value['prompts'][0]
        with self.assertRaises(ValueError):prompts_checked(value)

    def test_forecast_uses_slowest_complete_batch(self):
        x=remaining_forecast(100,[1,2,8],80)
        self.assertEqual(x['full_batch_max_seconds'],8)
        self.assertGreater(x['predicted_total_worker_seconds'],1000)
        self.assertFalse(x['admitted'])

    def test_no_measurement_is_not_free(self):
        with self.assertRaises(ValueError):remaining_forecast(1,[],80)
        with self.assertRaises(ValueError):remaining_forecast(1,[float('nan')],80)

    def test_hard_reservation_includes_full_platform_startup(self):
        self.assertEqual(cost_cents(1260+600)+20,RESERVED_CENTS)
        self.assertFalse(remaining_forecast(50,[1],80,stage_used_cents=900)['admitted'])


if __name__=='__main__':unittest.main()
