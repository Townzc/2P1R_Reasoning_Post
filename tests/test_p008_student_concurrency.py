import ast
import copy
import tempfile
import unittest
from pathlib import Path
from experiments.sft_allocation_midpoint.common import digest
from experiments.sft_allocation_p008.student_concurrency import (
    dispatch_lock, occupied_capacity, require_capacity, validate_quota)


def fixture():
    owner = dict(authority='Direct human reply in this chat', maximum_student_H100_workers=8)
    quota = dict(confirmed=True, gpu_type='H100', workspace_id='test-workspace',
                 available_quota=8, evidence_sha256='a'*64, observed_utc='2026-10-13T18:00:00Z')
    spec = dict(maximum_concurrent_gpus=8, provider_workspace_id='test-workspace',
                student_concurrency_owner_sha256=digest(owner), student_quota_sha256=digest(quota))
    return spec, dict(student_concurrency_owner=owner, student_quota=quota)


class StudentConcurrencyTests(unittest.TestCase):
    def test_quota_and_owner_match(self): self.assertEqual(validate_quota(*fixture()), 8)
    def test_wrong_workspace_and_missing_proof(self):
        for key, value in [('workspace_id','another'),('confirmed',False),('gpu_type','A100'),('available_quota',4),('evidence_sha256','')]:
            spec,gates=fixture();gates['student_quota'][key]=value
            spec['student_quota_sha256']=digest(gates['student_quota'])
            with self.assertRaises(ValueError):validate_quota(spec,gates)
    def test_owner_is_not_reviewer_relay(self):
        spec,gates=fixture();gates['student_concurrency_owner']['authority']='Reviewer relayed approval'
        spec['student_concurrency_owner_sha256']=digest(gates['student_concurrency_owner'])
        with self.assertRaises(ValueError):validate_quota(spec,gates)
    def test_old_maximum_cannot_admit(self):
        spec,gates=fixture();spec['maximum_concurrent_gpus']=4
        with self.assertRaises(ValueError):validate_quota(spec,gates)
    def test_pending_without_container_counts(self):
        p=[dict(run_id=str(i),provider_app_id='ap-'+str(i)) for i in range(8)]
        with self.assertRaises(ValueError):require_capacity(p,[])
        self.assertEqual(require_capacity(p[:-1],[]),7)
    def test_disjoint_provider_and_queued_calls_sum(self):
        p=[dict(run_id=str(i),provider_app_id='ap-'+str(i)) for i in range(4)]
        c=[dict(container_id='ta-'+str(i),app_id='other-'+str(i)) for i in range(4)]
        with self.assertRaises(ValueError):require_capacity(p,c)
    def test_one_running_call_not_double_counted(self):
        p=[dict(run_id='one',provider_app_id='ap-one')]
        c=[dict(container_id='ta-one',app_id='ap-one')]
        self.assertEqual(occupied_capacity(p,c),1)
        c.append(dict(container_id='ta-two',app_id='ap-one'))
        self.assertEqual(occupied_capacity(p,c),2)
    def test_duplicate_or_unknown_identity_rejected(self):
        p=[dict(run_id='one',provider_app_id='ap-one')]
        with self.assertRaises(ValueError):occupied_capacity(p+p,[])
        with self.assertRaises(ValueError):occupied_capacity([], [dict(container_id='ta-one')])
    def test_local_dispatches_cannot_race(self):
        with tempfile.TemporaryDirectory() as root:
            with dispatch_lock(root):
                with self.assertRaises(ValueError):
                    with dispatch_lock(root):pass
            with dispatch_lock(root):pass
    def test_scientific_worker_unchanged_except_validation_import(self):
        funcs=[]
        for name in ('modal_students_lineage','modal_students_eight'):
            tree=ast.parse(Path('experiments/sft_allocation_p008/'+name+'.py').read_text())
            fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='work')
            for node in ast.walk(fn):
                if isinstance(node,ast.ImportFrom) and node.module.endswith('eight_gpu_student_binding'):
                    node.module=node.module.replace('eight_gpu_student_binding','lineage_student_binding')
            funcs.append(ast.dump(fn))
        self.assertEqual(*funcs)


if __name__=='__main__':unittest.main()
