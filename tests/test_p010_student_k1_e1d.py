"""Only new dispatch/transfer boundary cases; no models, tokens or scoring."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
from decimal import Decimal

from experiments.p010.common import dump, read, manifest
from experiments.p010.student_dispatch_v2 import original_T_records, reserved_and_slots, validate_data_binding


class DispatchBoundary(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def record(self,name,amount,app=None,error=False):
        p=self.root/name/'INTENT.json';dump(p,{'budget':{'category':'T','new_reserved_usd':amount}})
        if app:dump(p.parent/'SUBMITTED.json',{'app_id':app})
        if error:dump(p.parent/'ERROR.json',{'type':'ConnectionError'})
        return p

    def test_failed_parents_and_endpoint_child_reservations_remain(self):
        self.record('e4_n400_r1','6.55','old',True)
        self.record('student_runs/t15','6.55','student')
        self.record('e4_endpoint_only_runs/e4','2.52','endpoint')
        self.record('e4_failure_preservation_r1/n400','0')
        paths=original_T_records(self.root)
        total,slots=reserved_and_slots(paths,[],{'old':'stopped','student':'stopped','endpoint':'stopped'})
        self.assertEqual((len(paths),total,slots),(3,Decimal('15.62'),0))

    def test_callback_error_does_not_release_active_provider_slot(self):
        p=self.record('student_runs/a','6.55','app',True)
        self.assertEqual(reserved_and_slots([p],[],{'app':'ephemeral (detached)'})[1],1)

    def test_unknown_pending_unmatched_and_multiple_containers_all_count(self):
        paths=[self.record('student_runs/a','6.55','a'),self.record('student_runs/b','6.55')]
        containers=[{'app_id':'a'},{'app_id':'a'},{'app_id':'foreign'}]
        self.assertEqual(reserved_and_slots(paths,containers,{})[1],4)

    def test_stopped_provider_with_owned_container_still_counts(self):
        p=self.record('student_runs/a','6.55','a')
        self.assertEqual(reserved_and_slots([p],[{'app_id':'a'}],{'a':'stopped'})[1],1)

    def test_duplicate_app_bindings_rejected(self):
        paths=[self.record('student_runs/a','6.55','a'),self.record('student_runs/b','6.55','a')]
        with self.assertRaises(ValueError):reserved_and_slots(paths,[],{'a':'stopped'})

    def test_teacher_specific_A1_rejects_another_teacher_or_fixed_commit(self):
        expected={'scope':'p010-T72-complete-data-A1','data_manifest_sha256':'72','data_fixed_commit':'fixed72','data_cell':'n400_k1'}
        spec={'data_reviews':{'run':expected}};good={'scope':expected['scope'],'data_manifest_sha256':'72','target_commit':'fixed72','accepted_cells':['n400_k1']}
        self.assertTrue(validate_data_binding(spec,'run',good))
        for key,value in [('scope','p010-T7-complete-data-A1'),('data_manifest_sha256','7'),('target_commit','other')]:
            with self.assertRaises(ValueError):validate_data_binding(spec,'run',{**good,key:value})

    def test_actual_new_worker_and_score_execution_bodies_retain_original_science(self):
        def body(path,name):
            tree=ast.parse(Path(path).read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
            return ast.dump(node,include_attributes=False)
        self.assertEqual(body('experiments/p010/modal_students.py','worker'),body('experiments/p010/modal_students_k1_e1d.py','worker'))
        self.assertEqual(body('scripts/score_p010_student.py','execute'),body('scripts/score_p010_student_k1_e1d.py','execute'))
        self.assertEqual(body('scripts/audit_p010_student.py','collect_records'),body('scripts/audit_p010_student_k1_e1d.py','collect_records'))


class TransferBoundary(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        src=self.root/'student_inputs_r2';src.mkdir();(src/'MATH_ENDPOINT.json').write_bytes(b'original endpoint')
        (src/'run').mkdir();(src/'run/rows.json').write_bytes(b'original selected rows')
        self.spec=self.root/'spec.json';dump(self.spec,{'input_files':manifest(src)})
        spec=importlib.util.spec_from_file_location('new_p010_transfer','scripts/p010_student_k1_e1d_io.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.remote={'/p010-20261019/student_inputs/MATH_ENDPOINT.json':b'original endpoint'};self.writes=[]
        owner=self
        class Batch:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def put_file(self,local,name):
                if name in owner.remote:raise AssertionError('overwrite')
                owner.remote[name]=Path(local).read_bytes();owner.writes.append(name)
        class Volume:
            @staticmethod
            def from_name(*args,**kwargs):return Volume()
            def read_file(self,name):
                if name not in owner.remote:raise FileNotFoundError(name)
                return iter([owner.remote[name]])
            def batch_upload(self,force=False):
                if force:raise AssertionError('force overwrite')
                return Batch()
        mod=types.ModuleType('modal');mod.Volume=Volume;exc=types.ModuleType('modal.exception');exc.NotFoundError=type('NotFoundError',(Exception,),{})
        self.mods={'modal':mod,'modal.exception':exc}

    def test_wrapped_missing_only_upload_preserves_existing_original(self):
        with patch.dict('sys.modules',self.mods):self.module.upload(self.root,self.spec)
        self.assertEqual(self.writes,['/p010-20261019/student_inputs/run/rows.json'])
        proof=read(self.root/'student_input_upload_r2/COMPLETED.json')
        self.assertTrue(proof['files']['MATH_ENDPOINT.json']['reused_original'])
        self.assertFalse(proof['files']['run/rows.json']['reused_original'])

    def test_conflicting_remote_bytes_are_not_overwritten_or_retried(self):
        self.remote['/p010-20261019/student_inputs/MATH_ENDPOINT.json']=b'wrong original'
        with patch.dict('sys.modules',self.mods),self.assertRaises(ValueError):self.module.upload(self.root,self.spec)
        self.assertEqual(self.writes,[])
        self.assertTrue((self.root/'student_input_upload_r2/FAILED.json').exists())
        self.assertFalse((self.root/'student_input_upload_r2/COMPLETED.json').exists())

    def test_partial_directory_blocks_whole_helper_repeat(self):
        (self.root/'student_input_upload_r2').mkdir()
        with patch.dict('sys.modules',self.mods),self.assertRaises(FileExistsError):self.module.upload(self.root,self.spec)
        self.assertEqual(self.writes,[])


class ScopedCells(unittest.TestCase):
    def test_same_teacher_review_cannot_silently_admit_unreviewed_E1d(self):
        spec={'data_reviews':{'run':{'scope':'A1','data_manifest_sha256':'data','data_fixed_commit':'fixed','data_cell':'e1d_n3200_k1'}}}
        review={'scope':'A1','data_manifest_sha256':'data','target_commit':'fixed','accepted_cells':['n400_k1','n3200_k1']}
        with self.assertRaises(ValueError):validate_data_binding(spec,'run',review)
        self.assertTrue(validate_data_binding(spec,'run',{**review,'accepted_cells':['e1d_n3200_k1']}))

    def test_missing_explicit_cell_acceptance_is_not_full_packet_approval(self):
        spec={'data_reviews':{'run':{'scope':'A1','data_manifest_sha256':'data','data_fixed_commit':'fixed','data_cell':'n400_k1'}}}
        with self.assertRaises(ValueError):validate_data_binding(spec,'run',{'scope':'A1','data_manifest_sha256':'data','target_commit':'fixed'})


if __name__=='__main__':unittest.main()
