import unittest

from experiments.learning_regime_p009.stage1_nc_contract import slot, forecast, transport_checked
from experiments.learning_regime_p009.stage1_endpoint_engine import checked_endpoint
from experiments.sft_allocation_midpoint.common import digest


class NCContract(unittest.TestCase):
    def setUp(self):
        self.rows=[]
        for i in range(1319):
            row=dict(problem_id=f'gsm8k/test/{i:05d}',input_ids=[10,20])
            self.rows.append(dict(row,candidate_id='NC::'+row['problem_id'],source_row_sha256=digest(row)))

    def raw(self, ids, reason='length', stop=None):
        row=self.rows[0]
        return dict(candidate_id=row['candidate_id'],problem_id=row['problem_id'],
            source_row_sha256=row['source_row_sha256'],sampling=checked_endpoint('NC',self.rows),
            prompt_token_ids=row['input_ids'],output_count=1,backend_text='synthetic transport only',
            token_ids=ids,finish_reason=reason,stop_reason=stop)

    def test_two_fixed_slots_and_reserves(self):
        for name,n in [('nc_s17_n400',400),('nc_s17_n3200',3200)]:
            v=slot(name);self.assertEqual((v['n'],v['updates'],v['targets'],v['reserved_cents']),(n,1024,2097148,655))
            self.assertEqual(v['full_window_seconds'],5200)
        with self.assertRaises(ValueError):slot('s1_s17_n400')

    def test_missing_or_nonfinite_observation_cannot_be_zero_cost(self):
        for durations in ([],[0],[float('nan')],[float('inf')],[True]):
            with self.assertRaises(ValueError):forecast(10,64,6,durations,[1],5000)

    def test_slowest_observation_remains_binding(self):
        good=forecast(10,64,6,[1,2],[1,2],5000)
        bad=forecast(10,64,6,[1,2,100],[1,2],5000)
        self.assertTrue(good['admitted']);self.assertFalse(bad['admitted'])
        self.assertEqual(bad['training_block_max_seconds'],100)

    def test_eighty_percent_gate_is_separate_from_hard_reserve(self):
        gate=forecast(2800,0,0,[1],[1],655)
        self.assertLessEqual(gate['forecast_cents'],655)
        self.assertFalse(gate['admitted'])
        self.assertTrue(forecast(2800,0,0,[1],[1],1310)['admitted'])

    def test_only_native_eos_at_exact_cap_accepts_length_metadata(self):
        transport_checked(self.rows,self.rows[:1],[self.raw([7]*511+[151643])])
        transport_checked(self.rows,self.rows[:1],[self.raw([7]*512)])
        with self.assertRaises(ValueError):transport_checked(self.rows,self.rows[:1],[self.raw([7]*510+[151643])])
        with self.assertRaises(ValueError):transport_checked(self.rows,self.rows[:1],[self.raw([151643]+[7]*511)])

    def test_foreign_sampling_or_unconfirmed_shape_stays_invalid(self):
        value=self.raw([7,151643],reason='stop');value['sampling']=dict(value['sampling'],temperature=.8)
        with self.assertRaises(ValueError):transport_checked(self.rows,self.rows[:1],[value])
        value=self.raw([7,151643],reason='stop');value['output_count']=2
        with self.assertRaises(ValueError):transport_checked(self.rows,self.rows[:1],[value])


if __name__=='__main__':unittest.main()
