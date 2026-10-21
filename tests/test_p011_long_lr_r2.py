import ast
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from experiments.p011 import long_lr_r2_training as training
from experiments.p011 import long_lr_r2_path as path
from experiments.sft_allocation_midpoint.common import digest,sha
from scripts.p011_long_lr_r2_io import reused_input_receipt


class FrozenRateR2Tests(unittest.TestCase):
    def test_one_ulp_is_accepted_without_mutation(self):
        rates=training.learning_rates(2,'S-F15');rates[0]=math.nextafter(rates[0],math.inf);saved=copy.deepcopy(rates)
        self.assertTrue(training.compatible_frozen_rates(rates,2,'S-F15'))
        self.assertEqual(rates,saved)

    def test_large_change_and_nonfinite_or_nonfloat_rejected(self):
        original=training.learning_rates(2,'S-F15')
        for bad in (math.nan,math.inf,0,original[0]+2e-12*training.ARMS['S-F15']['peak_lr']):
            with self.subTest(bad=bad):
                rates=list(original);rates[0]=bad
                self.assertFalse(training.compatible_frozen_rates(rates,2,'S-F15'))
        self.assertFalse(training.compatible_frozen_rates(original[:1],2,'S-F15'))

    def test_frozen_vector_digest_and_non_lr_contract(self):
        row=dict(path_id='synthetic',input_ids=[3,4,151645],labels=[-100,4,151645],assistant_start=1,assistant_end=3,n_supervised=2,n_processed=3,eos_token_id=151645,template_final_newline_supervised=False)
        plan=dict(supervised_tokens=64002,optimizer_updates=2,seed=17,length_bucket_width=None,presentation_order='shuffled_full_passes_then_extras',row_path_ids=['synthetic'],updates=[[0]*32000,[0]],q=32001,exposures=[32001])
        rates=training.learning_rates(2,'S-F15');rates[1]=math.nextafter(rates[1],math.inf)
        proof=training.validate_plan([row],plan,rates,'S-F15')
        self.assertEqual(proof['lr_sha256'],digest(rates))
        changed=copy.deepcopy(plan);changed['seed']=18
        with self.assertRaises(ValueError):training.validate_plan([row],changed,rates,'S-F15')

    def test_training_functions_unchanged_except_exact_lr_predicate(self):
        old=Path('experiments/p011/long_training.py').read_text();new=Path('experiments/p011/long_lr_r2_training.py').read_text()
        original={x.name:ast.get_source_segment(old,x) for x in ast.parse(old).body if isinstance(x,ast.FunctionDef)}
        revised={x.name:ast.get_source_segment(new,x) for x in ast.parse(new).body if isinstance(x,ast.FunctionDef)}
        for name,text in original.items():
            expected=text.replace('rates != learning_rates(updates, arm)','not compatible_frozen_rates(rates, updates, arm)') if name=='validate_plan' else text
            self.assertEqual(revised[name],expected,name)

    def test_new_fences_allow_only_f15_a7_and_baseline(self):
        self.assertEqual(path.logical(dict(kind='student',cell='A7',arm='S-F15')),'long_A7_S-F15_s17_r2')
        self.assertEqual(path.logical(dict(kind='baseline',cell='baseline',arm='S-L15')),'long_baseline_S-L15_s17_r2')
        for cell,arm in [('A7','S-L15'),('A7','S-L3'),('A1','S-F15')]:
            with self.assertRaises(ValueError):path.logical(dict(kind='student',cell=cell,arm=arm))

    def test_both_initial_reserves_retained_and_pair_bounded(self):
        spec={'jobs':{n:{'limits':{'reserved_usd':r}} for n,r in zip(path.INITIAL_JOBS,['15.63','12.17'])}}
        steps=path.initial_pair_budget(spec,[],'47.66');self.assertEqual(steps[1]['prior_A_reserved_usd'],'63.29')
        with self.assertRaises(ValueError):path.initial_pair_budget(spec,[],'100')

    def test_prior_input_receipt_metadata_reuse_and_changed_bytes_fail(self):
        job=dict(kind='student',cell='A7',arm='S-F15')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);f=root/'receipt.json';f.write_text(json.dumps(dict(job_sha256=digest(job),all_remote_file_bytes_read_back=True)))
            spec={'prior_input_receipts':{path.logical(job):{'path':'receipt.json','sha256':sha(f)}}}
            expected=sha(f);self.assertEqual(reused_input_receipt(root,spec,job),expected)
            f.write_text('{}')
            with self.assertRaises(ValueError):reused_input_receipt(root,spec,job)

    def test_worker_and_oracle_route_same_new_validator(self):
        worker=Path('experiments/p011/long_lr_r2_execution.py').read_text()
        oracle=Path('experiments/p011/long_lr_r2_evidence.py').read_text()
        self.assertIn('long_lr_r2_training as training',worker)
        self.assertIn('from experiments.p011.long_lr_r2_training import ARMS, TARGETS, validate_plan',oracle)
        self.assertEqual(worker,Path('experiments/p011/long_execution.py').read_text().replace('long_training as training','long_lr_r2_training as training'))
        self.assertEqual(oracle,Path('experiments/p011/long_evidence.py').read_text().replace('from experiments.p011.long_training import','from experiments.p011.long_lr_r2_training import'))


if __name__=='__main__':unittest.main()
