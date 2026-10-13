import copy,unittest
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_p008.main_binding import validate_binding
from experiments.sft_allocation_p008.contract import DEADLINE_EPOCH,run_roster


def fixture(role='pool'):
    cfg=dict(run_id='pool_d1',role='pool',draw=1,high_multiple=8,max_physical_attempts=16384,max_seconds=3000,input_sha256='a'*64)
    if role=='main':cfg={**run_roster()[0], 'max_seconds':3000,'input_sha256':'a'*64}
    plan=dict(campaign_id='p008-main-fixture',created_epoch=DEADLINE_EPOCH-60000,deadline_epoch=DEADLINE_EPOCH,
       total_cap_cents=23500,stage_caps_cents={'main':23500},slots={cfg['run_id']:dict(stage='main',reserved_cents=500)})
    spec=dict(plan_sha256=digest(plan),config_sha256={cfg['run_id']:digest(cfg)},phase0_cap_cents=1500,
      stage_cap_cents=25000,project_ceiling_cents=45000,protected_cents=5000,branch=[8,True,2],
      common_targets={'1':524287,'8':4194296},draw_local_oracle_sha256={'1':'b'*64,'2':'c'*64})
    gates=dict(runtime_review=dict(verdict='PASS',scope='main-runtime',review_commit='1'*40,review_report_sha256='2'*64,source_files={'x.py':'3'*64},spec_sha256=digest(spec)),
      phase0=dict(oracle_passed=True,four_gpu_verified=True,provider_released=True,oracle_sha256='4'*64),
      upload=dict(passed=True,input_sha256=cfg['input_sha256']),joint_plan_gate=dict(passed=True,sha256='5'*64),
      draw_review=dict(draw=1,verdict='PASS',review_commit='6'*40,local_oracle_sha256='b'*64),
      required_terminals=[dict(campaign='p008-phase0-20261013-r1',run_id=r,terminal={'status':'completed'}) for r in ('teacher_calibration','student_smoke','io_probe_a','io_probe_b')])
    if role=='main':gates['required_terminals'] += [dict(campaign=plan['campaign_id'],run_id=f'pool_d{d}',terminal={'status':'completed'}) for d in (1,2)]
    release=dict(source_files={'x.py':'3'*64},spec_sha256=digest(spec),gates=gates)
    return plan,cfg,release,spec

class MainBindingTest(unittest.TestCase):
 def test_pool(self):self.assertTrue(validate_binding(*fixture()))
 def test_student(self):self.assertTrue(validate_binding(*fixture('main')))
 def test_not_four_verified(self):
  a=fixture();a[2]['gates']['phase0']['four_gpu_verified']=False
  with self.assertRaisesRegex(ValueError,'four-way'):validate_binding(*a)
 def test_pending_review(self):
  a=fixture();a[2]['gates']['runtime_review']['verdict']='pending'
  with self.assertRaisesRegex(ValueError,'review'):validate_binding(*a)
 def test_wrong_draw_review(self):
  a=fixture('main');a[2]['gates']['draw_review']['draw']=2
  with self.assertRaisesRegex(ValueError,'G1'):validate_binding(*a)
 def test_foreign_upload(self):
  a=fixture();a[2]['gates']['upload']['input_sha256']='f'*64
  with self.assertRaisesRegex(ValueError,'readback'):validate_binding(*a)
 def test_missing_pool_terminal(self):
  a=fixture('main');a[2]['gates']['required_terminals'].pop()
  with self.assertRaisesRegex(ValueError,'terminal roster'):validate_binding(*a)
 def test_reserve_cannot_use_average_time(self):
  a=fixture();a[0]['slots']['pool_d1']['reserved_cents']=1;a[3]['plan_sha256']=digest(a[0]);a[2]['spec_sha256']=digest(a[3]);a[2]['gates']['runtime_review']['spec_sha256']=digest(a[3])
  with self.assertRaisesRegex(ValueError,'under-reserved'):validate_binding(*a)
 def test_no_deadline_extension_even_if_rehashed(self):
  a=fixture();a[0]['deadline_epoch']+=3600;a[3]['plan_sha256']=digest(a[0]);a[2]['spec_sha256']=digest(a[3]);a[2]['gates']['runtime_review']['spec_sha256']=digest(a[3])
  with self.assertRaisesRegex(ValueError,'deadline'):validate_binding(*a)

if __name__=='__main__':unittest.main()
