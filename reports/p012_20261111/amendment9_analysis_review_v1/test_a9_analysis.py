"""Synthetic identity and decision-boundary checks; no real-data statistics."""
import copy
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
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

    def catalog(self):
        return json.loads(a9.CATALOG_PATH.read_text())

    def unit_manifest(self):
        return {'units':['R01'], 'endpoints':{'R01:17':{}, 'R01:29':{}}}

    def test_complete_selected_unit_allowed(self):
        self.assertEqual(a9.select_units(self.unit_manifest(),self.catalog(),set()),['R01'])

    def test_missing_units_rejected(self):
        m=self.unit_manifest();m.pop('units')
        with self.assertRaisesRegex(ValueError,'nonempty'):a9.select_units(m,self.catalog(),set())

    def test_missing_endpoint_within_unit_rejected(self):
        m=self.unit_manifest();m['endpoints'].pop('R01:29')
        with self.assertRaisesRegex(ValueError,'complete selected units'):a9.select_units(m,self.catalog(),set())

    def test_extra_endpoint_rejected(self):
        m=self.unit_manifest();m['endpoints']['R02:17']={}
        with self.assertRaisesRegex(ValueError,'complete selected units'):a9.select_units(m,self.catalog(),set())

    def test_unknown_unit_rejected(self):
        m=self.unit_manifest();m['units']=['R07']
        with self.assertRaisesRegex(ValueError,'Unknown'):a9.select_units(m,self.catalog(),set())

    def test_duplicate_unit_rejected(self):
        m=self.unit_manifest();m['units']=['R01','R01']
        with self.assertRaisesRegex(ValueError,'Duplicate unit'):a9.select_units(m,self.catalog(),set())

    def test_previously_run_unit_rejected(self):
        with self.assertRaisesRegex(ValueError,'already analyzed'):
            a9.select_units(self.unit_manifest(),self.catalog(),{'R01'})

    def test_prior_result_cannot_be_omitted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'one').mkdir();(root/'one/RESULTS.json').write_text('{}')
            with patch.object(a9,'RUNS_DIR',root):
                with self.assertRaisesRegex(ValueError,'Missing or unregistered'):
                    a9.prior_results({'prior_results':[]})

    def test_prediction_and_manifest_modified_together_rejected(self):
        changed='e'*64
        m={'accepted_analysis_review_commit':a9.ACCEPTED_REVIEW,'authority_commit':a9.AUTHORITY,
           'catalog_sha256':a9.CATALOG_SHA,'prediction_sha256':changed}
        def fake_sha(p):
            return changed if Path(p)==a9.PRED_PATH else a9.CATALOG_SHA if Path(p)==a9.CATALOG_PATH else a9.CORE_SHA
        with patch.object(a9,'sha',side_effect=fake_sha):
            with self.assertRaisesRegex(ValueError,'Prediction binding'):a9.analyze(m)

    def test_partial_aggregate_is_null_with_missing_units(self):
        out=a9.aggregate({'R01':{'same_sign':True,'miss_replicates':True}}, {})
        self.assertIsNone(out['single_epoch_all_same_sign'])
        self.assertEqual(out['missing_units']['single_epoch_all_same_sign'],['R02','R03','R04'])
        self.assertTrue(all(x is None for x in out['M_predictions'].values()))

    def test_M3_needs_only_qwen_base(self):
        out=a9.aggregate({}, {'qwen_base_gsm8k':{'accuracy_pct_by_seed':{'PK2':{'17':68.,'29':69.}}}})
        self.assertTrue(out['M_predictions']['M-3']);self.assertIsNone(out['M_predictions']['M-1'])

    def test_complete_R_aggregate(self):
        R={f'R{i:02d}':{'same_sign':True,'miss_replicates':i<=3,'mean_residual_pp':4} for i in range(1,7)}
        out=a9.aggregate(R,{})
        self.assertTrue(out['single_epoch_all_same_sign']);self.assertTrue(out['single_epoch_at_least3_misses_repeat'])
        self.assertTrue(out['interaction_failure_trigger']);self.assertEqual(out['missing_units']['interaction_failure_trigger'],[])


if __name__=='__main__':unittest.main()
