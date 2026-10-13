import ast
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch
from experiments.sft_allocation_p008.frozen_student_plan import validate_frozen_lrs, validate_plan
from experiments.sft_allocation_p008 import student_runtime as legacy

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'reports/p008_20261013/student_admission_v1'
VECTORS=json.loads((ROOT/'reports/p008_20261013/LR_VECTORS.json').read_text())


def prepared(run):
    cfg=json.loads((PACK/(run+'.json')).read_text())
    plan=json.loads((PACK/'inputs'/cfg['plan_file']).read_text())
    rows=[json.loads(x) for x in (PACK/'inputs'/cfg['rows_file']).read_text().split('\n') if x.strip()]
    encoded=[dict(problem_id=x['problem_id'],path_id=x['path_id'],response_hash=hashlib.sha256(x['response'].encode()).hexdigest(),n_supervised=x['source']['n_supervised'],n_processed=x['source']['n_processed']) for x in rows]
    return cfg,plan,rows,encoded


class FrozenStudentPlanTest(unittest.TestCase):
    def test_exact_preregistered_vectors_all_horizons(self):
        for u,v in VECTORS.items():
            self.assertEqual(validate_frozen_lrs(v,int(u)),v)

    def test_one_ulp_plan_mutation_rejected(self):
        for u in (256,2048):
            for index in (0,75,u-1):
                v=list(VECTORS[str(u)]);v[index]=math.nextafter(v[index],math.inf)
                with self.assertRaises(ValueError):validate_frozen_lrs(v,u)

    def test_wrong_horizon_or_truncation_rejected(self):
        v=VECTORS['256']
        for x,u in ((v,2048),(v[:-1],256),(v,255),(v,True)):
            with self.assertRaises(ValueError):validate_frozen_lrs(x,u)

    def test_nonfinite_boolean_and_integer_entries_rejected(self):
        for x in (float('nan'),float('inf'),True,1,0.0,-1e-5):
            v=list(VECTORS['256']);v[0]=x
            with self.assertRaises(ValueError):validate_frozen_lrs(v,256)

    def test_observed_linux_rounding_reproduces_old_refusal_but_keeps_frozen_plan(self):
        # Original Linux/glibc2.36 observation at index75, saved in diagnostic r3.
        cfg,plan,rows,encoded=prepared('d1_b1_p0_breadth_t1')
        linux=list(plan['lrs']);self.assertEqual(linux[75].hex(),'0x1.6c260e5264d43p-14')
        linux[75]=float.fromhex('0x1.6c260e5264d42p-14')
        before=deepcopy(plan)
        with patch.object(legacy,'lrs',return_value=linux):
            with self.assertRaisesRegex(ValueError,'Fixed LR,seed or update count differs'):
                legacy.validate_plan(rows,encoded,plan,cfg)
            got=validate_plan(rows,encoded,plan,cfg)
        self.assertEqual(got['supervised_response_tokens'],524287)
        self.assertEqual(plan,before)
        with self.assertRaises(ValueError):validate_frozen_lrs(linux,256)

    def test_all_original_plans_preserve_exact_budget_checks(self):
        spec=json.loads((PACK/'ADMISSION.json').read_text())
        for run,c in spec['configs'].items():
            if c['role']=='base':continue
            cfg,plan,rows,encoded=prepared(run)
            with patch.object(legacy,'lrs',return_value=VECTORS[str(cfg['updates'])]):
                expected=legacy.validate_plan(rows,encoded,plan,cfg)
            self.assertEqual(validate_plan(rows,encoded,plan,cfg),expected)
            bad=deepcopy(plan);bad['supervised_targets']-=1
            with self.assertRaises(ValueError):validate_plan(rows,encoded,bad,cfg)

    def test_frozen_scientific_run_body_unchanged(self):
        def run_ast(name):
            t=ast.parse((ROOT/'experiments/sft_allocation_p008'/name).read_text())
            return ast.dump(next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name=='run'))
        self.assertEqual(run_ast('block_student_runtime.py'),run_ast('frozen_lr_block_student_runtime.py'))

if __name__=='__main__':unittest.main()
