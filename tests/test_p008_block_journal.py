"""CPU fault injection and scientific-body identity; never calls a model."""
import ast
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from experiments.sft_allocation_midpoint.common import read, digest
from experiments.sft_allocation_p008.block_journal import (
    BlockTrainingJournal, verify_training_blocks)
from tests.test_midpoint_guard import FakeAtomicStore


class BlockJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.store = FakeAtomicStore()
        self.checks = 0
        self.deadlines = 0
        self.fenced = False
        self.expired = False
        self.j = BlockTrainingJournal(self.out, 'run', self.store, lambda:None,
                                      self.check, deadline=self.deadline,
                                      expected_updates=256)
        self.j.configure_training([dict(n_supervised=7, n_processed=13)],
                                  [[0] for _ in range(256)], [1e-4]*256)

    def check(self):
        self.checks += 1
        if self.fenced:
            raise RuntimeError('fenced')

    def deadline(self):
        self.deadlines += 1
        if self.expired:
            raise TimeoutError('deadline')

    def update(self, step):
        item = deepcopy(self.j.records[step-1])
        name = f'update_{step:04d}'
        self.j.begin(name, item)
        self.j.end(name, {**item, 'loss':1.0, 'seconds':0.1,
                         'cumulative_targets':step*7,
                         'cumulative_processed':step*13})

    def records(self):
        return ({p.stem:read(p) for p in (self.out/'intents').glob('*.json')},
                {p.stem:read(p) for p in (self.out/'completed').glob('*.json')})

    def test_full_256_dose_and_original_evaluation_journal(self):
        for step in range(1,257):self.update(step)
        self.j.assert_training_complete()
        self.assertEqual(self.checks,32)
        self.assertGreaterEqual(self.deadlines,512)
        self.assertFalse(any('/update_' in k for k in self.store.records))
        self.j.begin('endpoint1319_batch_0000', {'count':16})
        self.j.end('endpoint1319_batch_0000', {'count':16})
        intents,done=self.records()
        blocks=verify_training_blocks(intents,done,self.store.records,'run/',256)
        self.assertEqual(len(blocks),16)
        self.assertEqual(len(done),273)
        self.assertEqual(done['update_0256']['cumulative_targets'],1792)

    def test_reservation_covers_future_updates_before_any_compute(self):
        self.j.begin('update_0001',self.j.records[0])
        block=self.store.records['run/unit/training_block_0001_0016']
        self.assertEqual([r['step'] for r in block['updates']],list(range(1,17)))
        self.assertEqual(block['updates_sha256'],digest(self.j.records[:16]))
        self.assertNotIn('run/done/training_block_0001_0016',self.store.records)

    def test_fence_inside_block_prevents_ack_and_next_block(self):
        for step in range(1,16):self.update(step)
        self.fenced=True
        with self.assertRaisesRegex(RuntimeError,'fenced'):self.update(16)
        self.assertTrue((self.out/'completed/update_0016.json').exists())
        self.assertNotIn('run/done/training_block_0001_0016',self.store.records)
        with self.assertRaisesRegex(RuntimeError,'cannot be reused'):self.update(17)

    def test_per_update_local_deadline_not_delayed_to_block_boundary(self):
        self.update(1);self.expired=True
        with self.assertRaises(TimeoutError):self.update(2)
        self.assertFalse((self.out/'intents/update_0002.json').exists())
        self.expired=False
        with self.assertRaisesRegex(RuntimeError,'cannot be reused'):self.update(2)

    def test_post_remote_deadline_stops_before_optimizer_intent(self):
        original=self.j.check
        def late():
            original();self.expired=True
        self.j.check=late
        with self.assertRaises(TimeoutError):self.update(1)
        self.assertIn('run/unit/training_block_0001_0016',self.store.records)
        self.assertFalse((self.out/'intents/update_0001.json').exists())

    def test_partial_block_cannot_be_replayed_with_new_local_directory(self):
        self.update(1)
        other=BlockTrainingJournal(self.out/'other','run',self.store,lambda:None,
            self.check,deadline=self.deadline,expected_updates=256)
        other.configure_training([dict(n_supervised=7,n_processed=13)],[[0]]*256,[1e-4]*256)
        with self.assertRaisesRegex(RuntimeError,'already attempted'):
            other.begin('update_0001',other.records[0])

    def test_eval_or_reconfiguration_cannot_bypass_incomplete_training(self):
        with self.assertRaisesRegex(RuntimeError,'before all training'):
            self.j.begin('endpoint1319_batch_0000',{})
        with self.assertRaisesRegex(RuntimeError,'cannot be reconfigured'):
            self.j.configure_training([],[],[])

    def test_wrong_step_or_lr_rejected_before_remote_reservation(self):
        wrong=deepcopy(self.j.records[0]);wrong['lr']=1e-3
        with self.assertRaises(ValueError):self.j.begin('update_0001',wrong)
        self.assertFalse(self.store.records)

    def test_duplicate_or_foreign_completion_fails_closed(self):
        self.j.begin('update_0001',self.j.records[0])
        with self.assertRaises(ValueError):self.j.end('update_0002',self.j.records[0])
        self.assertFalse(list((self.out/'completed').glob('*')))

    def test_modified_local_step_cannot_match_remote_block_ack(self):
        for step in range(1,257):self.update(step)
        intents,done=self.records();done['update_0031']['loss']=5.0
        with self.assertRaisesRegex(ValueError,'completion differs'):
            verify_training_blocks(intents,done,self.store.records,'run/',256)

    def test_extra_remote_step_or_missing_block_is_rejected(self):
        for step in range(1,257):self.update(step)
        intents,done=self.records()
        self.store.records['run/unit/update_0001']=intents['update_0001']
        with self.assertRaisesRegex(ValueError,'roster'):
            verify_training_blocks(intents,done,self.store.records,'run/',256)

    def test_base_only_uses_original_evaluation_units(self):
        base=BlockTrainingJournal(self.out/'base','base',self.store,lambda:None,
                                 self.check,deadline=self.deadline,expected_updates=0)
        base.begin('endpoint1319_batch_0000',{'count':16})
        base.end('endpoint1319_batch_0000',{'count':16})
        base.assert_training_complete()
        self.assertEqual(self.checks,1)

    def test_scientific_run_body_identical_except_two_journal_hooks(self):
        root=Path(__file__).resolve().parents[1]/'experiments/sft_allocation_p008'
        def run_node(name):
            return next(n for n in ast.parse((root/name).read_text()).body
                        if isinstance(n,ast.FunctionDef) and n.name=='run')
        original=run_node('student_runtime.py')
        current=run_node('block_student_runtime.py')
        def is_hook(n):
            return (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
                and isinstance(n.value.func,ast.Attribute)
                and isinstance(n.value.func.value,ast.Name)
                and n.value.func.value.id=='journal'
                and n.value.func.attr in ('configure_training','assert_training_complete'))
        self.assertEqual(sum(is_hook(n) for n in current.body),2)
        current.body=[n for n in current.body if not is_hook(n)]
        self.assertEqual(ast.dump(original),ast.dump(current))


if __name__=='__main__':unittest.main()
