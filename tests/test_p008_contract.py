import math
import unittest
from experiments.sft_allocation_p008.contract import lrs, stable_seed, run_roster, select_branch, overlap_seconds, PHASE0_ROLES
from experiments.sft_allocation_midpoint.runtime import lrs as original_lrs

class ContractTest(unittest.TestCase):
    def test_original_vector_byte_identical(self):
        import struct
        self.assertEqual(b''.join(struct.pack('d', x) for x in lrs(256)), b''.join(struct.pack('d', x) for x in original_lrs()))
    def test_long_lr_has_no_rebound(self):
        for u in (256,1024,2048):
            r=lrs(u);w=u//16
            self.assertEqual(len(r),u);self.assertEqual(r[w-1],1e-4);self.assertEqual(r[-1],1e-5)
            self.assertTrue(all(a<=b for a,b in zip(r[:w],r[1:w])))
            self.assertTrue(all(a>=b for a,b in zip(r[w-1:],r[w:])))
            self.assertTrue(all(math.isfinite(x) and 0<x<=1e-4 for x in r))
    def test_invalid_lr(self):
        for value in (0,8,-16,17,True,256.):
            with self.assertRaises(ValueError):lrs(value)
    def test_domain_separation(self):
        seeds=[stable_seed('teacher',d,f'gsm8k/train/{i:05}',a) for d in (1,2) for i in range(6973) for a in range(1,9)]
        self.assertEqual(len(set(seeds)),len(seeds))
        self.assertNotEqual(stable_seed('teacher',1,'a',1),stable_seed('calibration',1,'a',1))
        self.assertNotEqual(stable_seed('teacher',1,'ab',2),stable_seed('teacher',1,'a',2))
    def test_all_design_branches(self):
        for branch,n,units in [((8,True,2),20,90),((8,False,2),18,74),((4,False,2),18,42),((4,False,1),10,22)]:
            rows=run_roster(*branch);self.assertEqual(len(rows),n);self.assertEqual(sum(r['training_multiple'] for r in rows),units)
            self.assertEqual(len(set(r['run_id'] for r in rows)),n)
            self.assertEqual({r['seed'] for r in rows},{17})
    def test_forecast_only_branch_choice(self):
        from experiments.sft_allocation_p008.contract import BRANCHES
        f=[dict(branch=list(b),total_stage_usd_upper=199,finish_hour_pdt_upper=17) for b in BRANCHES]
        self.assertEqual(select_branch(f),BRANCHES[0]);f[0]['total_stage_usd_upper']=201
        self.assertEqual(select_branch(f),BRANCHES[1])
        for row in f:row['finish_hour_pdt_upper']=19
        self.assertIsNone(select_branch(f))
    def test_true_concurrency_not_four_submissions(self):
        a={r:(i,i+1) for i,r in enumerate(PHASE0_ROLES)};self.assertEqual(overlap_seconds(a),0)
        self.assertEqual(overlap_seconds({r:(0,10) for r in PHASE0_ROLES}),10)
        with self.assertRaises(ValueError):overlap_seconds({})


class ScheduleTest(unittest.TestCase):
    def test_low_training_bridge_allows_unexposed_inventory(self):
        from experiments.sft_allocation_p008.schedule import schedule
        s=schedule([4,6,10],6,1)
        self.assertEqual(s['updates'],[[1]]);self.assertEqual(s['zero_exposure_answers'],2)
        self.assertEqual(s['acquired_answers'],3);self.assertEqual(s['supervised_targets'],6)
    def test_old_all_once_case_preserved(self):
        from experiments.sft_allocation_p008.schedule import schedule
        from scripts.plan_real_math_scale import whole_response_schedule
        for budget in (60,64,66,70,76):
            self.assertEqual(schedule([4,6,10],budget,4)['updates'],whole_response_schedule([4,6,10],budget,4,17))
    def test_impossible_dose_is_not_truncated(self):
        from experiments.sft_allocation_p008.schedule import schedule
        with self.assertRaises(ValueError):schedule([4,6,10],5,1)
        with self.assertRaises(ValueError):schedule([4,6,10],6,2)

if __name__=='__main__':unittest.main()
