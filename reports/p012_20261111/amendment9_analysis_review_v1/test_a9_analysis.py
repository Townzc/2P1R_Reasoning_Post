"""Synthetic identity and decision-boundary checks; no real-data statistics."""
import copy
import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('a9_candidate',Path(__file__).with_name('a9_analysis.py'))
a9=importlib.util.module_from_spec(spec);spec.loader.exec_module(a9)


class Checks(unittest.TestCase):
    def fixture(self):
        expected={'platform':'modal','training_run_id':'synthetic','model':'meta-llama/Llama-3.2-1B',
                  'revision':'a'*40,'cell':'A8_P2048_K2_E2','seed':29,'P':2048,'K':2,'E':2,
                  'updates':1024,'dataset_sha256':'d'*64}
        training={'run_id':'synthetic','model':{'repo':expected['model'],'revision':'a'*40},
                  'cell':expected['cell'],'config':{'seed':29,'data_seed':29,'num_train_epochs':2,
                      'per_device_train_batch_size':8,'gradient_accumulation_steps':1,'lr_scheduler_type':'cosine',
                      'learning_rate':1e-5,'finetuning_type':'full'},
                  'dose':{'parents':2048,'paths_per_parent':2,'epochs':2,'expected_updates':1024,
                          'distinct_rows':4096,'effective_batch':8,'presentations':8192},
                  'dataset':{'sha256':'d'*64}}
        return training,expected

    def test_valid_identity(self):
        a9.validate_training(*self.fixture())

    def test_cell_swap_rejected(self):
        t,e=self.fixture();t['cell']='K4'
        with self.assertRaises(ValueError):a9.validate_training(t,e)

    def test_base_instruct_swap_rejected(self):
        t,e=self.fixture();t['model']['repo']='meta-llama/Llama-3.2-1B-Instruct'
        with self.assertRaises(ValueError):a9.validate_training(t,e)

    def test_seed_swap_rejected(self):
        t,e=self.fixture();t['config']['seed']=17;t['config']['data_seed']=17
        with self.assertRaises(ValueError):a9.validate_training(t,e)

    def test_dataset_swap_rejected(self):
        t,e=self.fixture();t['dataset']['sha256']='e'*64
        with self.assertRaises(ValueError):a9.validate_training(t,e)

    def test_update_dose_rejected(self):
        t,e=self.fixture();t['dose']['expected_updates']=512
        with self.assertRaises(ValueError):a9.validate_training(t,e)

    def test_revision_swap_rejected(self):
        t,e=self.fixture();t['model']['revision']='b'*40
        with self.assertRaises(ValueError):a9.validate_training(t,e)

    def test_row_count_rejected(self):
        t,e=self.fixture();t['dose']['distinct_rows']=2048
        with self.assertRaises(ValueError):a9.validate_training(t,e)

    def test_lora_recipe(self):
        t,e=self.fixture();e.update(platform='tinker',model='Qwen/Qwen3.5-4B')
        t.update(model=e['model'],asset={'revision':e['revision']},seed=29,mode='train',rank=32,
                 learning_rate=.0004905250962784578,
                 source_sha256='050a9f43d81c7a610dfc9ca30c901103e145fff28384d2efd1f13247fc60f5ee')
        a9.validate_training(t,e)
        t['rank']=64
        with self.assertRaises(ValueError):a9.validate_training(t,e)

    def test_boundary_is_not_outside(self):
        p={'a8_prediction':50,'seed17_residual':-5,'band_pp':4}
        r=a9.replication(45,46,p)
        self.assertFalse(r['miss_replicates']);self.assertTrue(r['same_sign'])

    def test_negative_miss_replicates(self):
        p={'a8_prediction':50,'seed17_residual':-5,'band_pp':4}
        self.assertTrue(a9.replication(45,45.9,p)['miss_replicates'])

    def test_opposite_sign_not_replication(self):
        p={'a8_prediction':50,'seed17_residual':-5,'band_pp':4}
        self.assertFalse(a9.replication(45,55,p)['miss_replicates'])

    def test_positive_mean_residual(self):
        p={'a8_prediction':50,'seed17_residual':5,'band_pp':4}
        r=a9.replication(55,54.5,p)
        self.assertEqual(r['mean_residual_pp'],4.75);self.assertTrue(r['miss_replicates'])

    def test_unreviewed_real_analysis_blocked(self):
        with self.assertRaisesRegex(ValueError,'awaits accepted review'):a9.analyze({})


if __name__=='__main__':unittest.main()
