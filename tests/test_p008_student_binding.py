import unittest
from tests.test_p008_main_binding import fixture
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_p008.student_binding import validate_student_binding


def prepared():
    plan,cfg,release,spec=fixture('main');g=release['gates']
    spec['common_plan_gate_sha256']=g['joint_plan_gate']['sha256'];spec['pool_admission_sha256']='7'*64
    g['pool_admission_sha256']='7'*64
    g['pool_terminals']=[t for t in g['required_terminals'] if t['campaign']==plan['campaign_id']]
    g['draw_review'].update(review_report_sha256='8'*64,target_commit='9'*40,input_sha256=cfg['input_sha256'],common_plan_gate_sha256=spec['common_plan_gate_sha256'])
    release['spec_sha256']=digest(spec);g['runtime_review']['spec_sha256']=digest(spec)
    return plan,cfg,release,spec

class StudentBindingTest(unittest.TestCase):
    def test_exact_prepared_binding(self):self.assertTrue(validate_student_binding(*prepared()))
    def test_pool_entry_rejected(self):
        with self.assertRaisesRegex(ValueError,'Student-only'):validate_student_binding(*fixture())
    def test_old_joint_gate_even_if_pass(self):
        a=prepared();a[2]['gates']['joint_plan_gate']['sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'all-draw'):validate_student_binding(*a)
    def test_unreviewed_inputs_rejected(self):
        a=prepared();a[2]['gates']['draw_review']['input_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'exact all-draw'):validate_student_binding(*a)
    def test_unreviewed_plans_rejected(self):
        a=prepared();a[2]['gates']['draw_review']['common_plan_gate_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'exact all-draw'):validate_student_binding(*a)
    def test_anonymous_review_rejected(self):
        a=prepared();del a[2]['gates']['draw_review']['review_report_sha256']
        with self.assertRaisesRegex(ValueError,'real fixed report'):validate_student_binding(*a)
    def test_unknown_pool_cannot_dispatch(self):
        a=prepared();a[2]['gates']['pool_terminals'][0]['terminal']={'status':'failed'}
        with self.assertRaises(ValueError):validate_student_binding(*a)
    def test_foreign_pool_provenance_rejected(self):
        a=prepared();a[2]['gates']['pool_admission_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'provenance'):validate_student_binding(*a)

if __name__=='__main__':unittest.main()
