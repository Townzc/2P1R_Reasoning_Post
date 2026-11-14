import copy
import unittest
from experiments.p012.tinker_export_recovery import validate_training, storage_receipt


class ExportRecoveryIdentityTests(unittest.TestCase):
    def setUp(self):
        self.request={'run_id':'a6_3_tinker_lora_4b_math_e8_s17_20261113_v1',
                      'mode':'train','model':'Qwen/Qwen3.5-4B','cell':'E8','seed':17,'rank':32,
                      'dose':{'expected_updates':1024},'cpu_counts':{'full_training_input_tokens':3471504}}
        self.order=list(range(1024))*8
        self.losses=[{'step':i+1,'row_indices':self.order[i*8:(i+1)*8]} for i in range(1024)]
        self.path='tinker://frozen-run/weights/final'
        self.state={'path':self.path};self.usage={'training_input_tokens':3471504,'sampling':None}

    def check(self):
        validate_training(self.request,self.losses,self.order,self.state,self.usage,self.path)

    def test_complete_state(self):self.check()

    def test_wrong_seed(self):
        self.request['seed']=29
        with self.assertRaises(ValueError):self.check()

    def test_wrong_model(self):
        self.request['model']='Qwen/Qwen3.5-9B'
        with self.assertRaises(ValueError):self.check()

    def test_missing_last_update(self):
        self.losses.pop()
        with self.assertRaises(ValueError):self.check()

    def test_duplicate_update(self):
        self.losses[-1]['step']=1023
        with self.assertRaises(ValueError):self.check()

    def test_crosswired_state(self):
        self.state['path']='tinker://other-run/weights/final'
        with self.assertRaises(ValueError):self.check()

    def test_sampler_is_not_training_state(self):
        self.path=self.state['path']='tinker://frozen-run/sampler_weights/final'
        with self.assertRaises(ValueError):self.check()

    def test_wrong_presentations(self):
        self.order[-1]=3;self.losses[-1]['row_indices'][-1]=3
        with self.assertRaises(ValueError):self.check()

    def test_incomplete_token_usage(self):
        self.usage['training_input_tokens']-=1
        with self.assertRaises(ValueError):self.check()


class StorageAdmissionTests(unittest.TestCase):
    def receipt(self, count=99, size=99_999_999_999, paid=False):
        return storage_receipt({'data': [{'checkpoint_count': count, 'size_bytes': size,
                                         'user_email': 'private@example.invalid'}],
                                'effective_rate_usd_per_gigabyte_month': 0.0}, paid)

    def test_free_below_both_limits(self):
        self.assertTrue(self.receipt()['admitted'])

    def test_free_count_limit(self):
        self.assertFalse(self.receipt(count=100)['admitted'])

    def test_free_byte_limit(self):
        self.assertFalse(self.receipt(size=100_000_000_000)['admitted'])

    def test_explicit_paid_declaration_admits_full_storage(self):
        self.assertTrue(self.receipt(count=100, size=110_000_000_000, paid=True)['admitted'])
        self.assertFalse(self.receipt(count=100, paid='true')['admitted'])

    def test_receipt_has_no_user_identifiers(self):
        self.assertNotIn('user_email', str(self.receipt()))


if __name__=='__main__':unittest.main()
