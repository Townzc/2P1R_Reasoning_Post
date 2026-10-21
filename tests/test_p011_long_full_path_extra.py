"""New final integration checks; no prior successful methods rerun."""
import copy,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from tests.test_p011_long_full_path import job,spec,Store
from scripts import prepare_p011_long_runtime_inputs as inputs,analyze_p011_long_pair as analysis
from experiments.p011 import long_path as p
from experiments.sft_allocation_midpoint.common import dump,manifest,digest

class FinalPath(unittest.TestCase):
    def test_native_eos_binding_new_validation(self):
        j=job();p.validate(spec(j));j['eos_token_ids']=[151645]
        with self.assertRaises(ValueError):p.validate(spec(j))
    def test_original_contrast_roster_excludes_selection_or_cross_arm(self):
        self.assertTrue(analysis.allowed(job(),job('student','A7','S-F15')))
        self.assertTrue(analysis.allowed(job('student','D1'),job('student','D2')))
        self.assertFalse(analysis.allowed(job('student','A1'),job('student','D2')))
        self.assertFalse(analysis.allowed(job('student','A5'),job('student','A7','S-L3')))
    def test_consumer_reuses_saved_values_and_plan_bytes_no_encoding(self):
        # Tiny synthetic source, validator mocked; no original source corpus read.
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'source';src.mkdir();out=Path(d)/'out';out.mkdir()
            row={'path_id':'p','exact':'a\u0304'};raw=json.dumps(row)+'\n';(src/'ENCODED.jsonl').write_text(raw)
            dump(src/'BENCHMARKS.json',[{'frozen':True}]);plan={'row_path_ids':['p'],'optimizer_updates':2};dump(src/'A1_PLAN.json',plan);dump(src/'MANIFEST.json',{'files':manifest(src)})
            with patch.object(inputs.long_training,'validate_plan',return_value={'fixture':True}),patch.object(inputs,'write_endpoint'):
                proofs=inputs.consume(src,out,[{'frozen':True}],[])
            self.assertEqual((src/'A1_PLAN.json').read_bytes(),(out/'A1/plan.json').read_bytes())
            self.assertEqual(json.loads((out/'A1/encoded.json').read_text()),[row]);self.assertEqual(len(proofs),3)
            self.assertTrue((out/'A1/rates_S-F15.json').exists())
    def test_production_main_functions_not_import_time_model_calls(self):
        import ast
        for name in ('scripts/prepare_p011_long_runtime_inputs.py','scripts/p011_long_io.py','scripts/analyze_p011_long_pair.py'):
            tree=ast.parse(Path(name).read_text())
            self.assertTrue(any(isinstance(n,ast.FunctionDef) and n.name=='main' for n in tree.body))
    def test_source_permission_not_self_granted_by_input_A1(self):
        with patch.object(p.shared,'fixed_report',return_value={}):
            with self.assertRaises(ValueError):inputs.source_review({'source_files':{},'input_basis_files':{}},{'scope':'input-A1'})
if __name__=='__main__':unittest.main()
