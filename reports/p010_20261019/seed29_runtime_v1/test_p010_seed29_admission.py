import ast
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from experiments.p010.common import dump
from experiments.p010.tier3_dispatch import (
    attempted_records, totals_and_slots, validate_a4, validate_seed29_data, SEED29_RUNS,
)


class Seed29Admission(unittest.TestCase):
    def records(self, root):
        a=Path(root)/'teacher_r1/INTENT.json'; b=Path(root)/'student_runs/run/INTENT.json'
        dump(a,dict(budget=dict(category='G',new_reserved_usd='8')))
        dump(a.parent/'SUBMITTED.json',dict(app_id='ended'))
        dump(b,dict(budget=dict(category='T',new_reserved_usd='6.55')))
        dump(Path(root)/'selection_r1/INTENT.json',dict(local_only=True))
        return a,b

    def test_failed_and_pending_reserves_both_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.records(tmp)
            paths=attempted_records(tmp); self.assertEqual(set(paths),{a,b})
            total,slots=totals_and_slots(paths,[],{'ended':'stopped'})
            self.assertEqual((total['G'],total['T'],slots),(Decimal('8'),Decimal('6.55'),1))

    def test_unknown_and_unmatched_count_as_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.records(tmp)
            total,slots=totals_and_slots([a,b],[dict(app_id='unmatched')],{})
            self.assertEqual(slots,3)

    def test_stopped_with_owned_container_is_not_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.records(tmp)
            self.assertEqual(totals_and_slots([a,b],[dict(app_id='ended')],{'ended':'stopped'})[1],2)

    def test_duplicate_app_binding_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=self.records(tmp);dump(b.parent/'SUBMITTED.json',dict(app_id='ended'))
            with self.assertRaises(ValueError):totals_and_slots([a,b],[],{'ended':'stopped'})

    def test_exact_input_binding_rejects_different_seed_data(self):
        expected=dict(target_commit='a'*40,basis_sha256='b'*64,input_archive_sha256='c'*64,source_files={'x':'d'*64})
        spec=dict(data_binding=expected,configs={r:{} for r in SEED29_RUNS})
        review=dict(expected,scope='p010-Tier3-seed29-exact-input-and-plan-A1',accepted_cells=sorted(SEED29_RUNS))
        self.assertTrue(validate_seed29_data(spec,'t15_s29_n400_k1',review))
        review['input_archive_sha256']='e'*64
        with self.assertRaises(ValueError):validate_seed29_data(spec,'t15_s29_n400_k1',review)

    def test_A4_report_does_not_require_extra_permission_but_requires_A3(self):
        a3=dict(scope='p010-K1-E1d-existing-samples-and-C9-complete-A3',decision='PASS-WITH-NOTES',
            target_commit='a8fb5c78190b5cd5f75cdcafd269af81cf717ff8',report_sha256='f'*64)
        a4=dict(scope='p010-A4-scientific-signal-report',issued=True,
            original_plan_commit='4287537f7733f5c3568ddb11695d47b566ef75fa',
            actual_A3_report_sha256='f'*64,results_target_commit=a3['target_commit'],
            automatic_Tier3_under_original_plan=True)
        self.assertTrue(validate_a4(a4,a3))
        for changed in [dict(a4,issued=False),dict(a4,actual_A3_report_sha256='x')]:
            with self.assertRaises(ValueError):validate_a4(changed,a3)

    def test_worker_scientific_AST_is_original(self):
        def worker(name):
            tree=ast.parse(Path(name).read_text())
            return ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='worker'))
        self.assertEqual(worker('experiments/p010/modal_students_seed29.py'),
                         worker('experiments/p010/modal_students_k1_e1d.py'))

    def test_local_entry_has_only_four_seed29_slots_and_true_A4(self):
        tree=ast.parse(Path('experiments/p010/modal_students_seed29.py').read_text())
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        calls=[n for n in ast.walk(main) if isinstance(n,ast.Call)]
        self.assertEqual(sum(isinstance(n.func,ast.Attribute) and n.func.attr=='spawn' for n in calls),1)
        self.assertEqual(sum(isinstance(n.func,ast.Name) and n.func.id=='validate_a4' for n in calls),1)
        self.assertEqual(len(SEED29_RUNS),4)


if __name__=='__main__':unittest.main()
