import tempfile
import types
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import json

from experiments.sft_allocation_midpoint.dispatch import spawn_once, wait_existing, validate_replacement
from experiments.sft_allocation_midpoint.monitor import GPURecorder


class Store:
    def __init__(self): self.records = {}
    def put(self, key, value, skip_if_exists):
        assert skip_if_exists
        if key in self.records: return False
        self.records[key] = value
        return True
    def get(self, key): return self.records.get(key)


class DispatchTests(unittest.TestCase):
    def binding(self):
        store=Store();terminal={'status':'failed','evidence_sha256':'same'}
        store.records={'midpoint/old/terminal/controller':terminal,'midpoint/old/terminal/repeat':terminal}
        plan={'campaign_id':'new','deadline_epoch':999,'slots':{'repeat':{},'new_arm':{},'controller':{}}}
        binding={'replacement_campaign':'new','parent_campaign':'old','deadline_epoch':999,
            'replacement_count_cap_per_failed_run':1,'replacement_is_not_exact_resume':True,
            'old_app_stopped':True,'old_containers':0,'old_controller_terminal':terminal,
            'fresh_replacement_runs':['repeat'],'previously_unattempted_runs':['new_arm'],
            'old_runs':{'repeat':{'terminal':terminal}}}
        return store,plan,binding

    def test_replacement_binds_failed_parent_without_mutation(self):
        import copy
        store,plan,binding=self.binding();before=copy.deepcopy(store.records)
        validate_replacement(store,plan,binding)
        self.assertEqual(store.records,before)

    def test_replacement_refuses_live_or_changed_parent(self):
        for field,value in [('old_containers',1),('old_app_stopped',False),('deadline_epoch',1000),('replacement_count_cap_per_failed_run',2)]:
            store,plan,binding=self.binding();binding[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_replacement(store,plan,binding)
        store,plan,binding=self.binding();store.records['midpoint/old/claim/new_arm']={'attempt':1}
        with self.assertRaises(ValueError):validate_replacement(store,plan,binding)

    def test_completed_parent_cannot_be_called_failed_replacement(self):
        store,plan,binding=self.binding();binding['old_runs']['repeat']['terminal']['status']='completed'
        with self.assertRaises(ValueError):validate_replacement(store,plan,binding)

    def test_replacement_refuses_added_or_omitted_work(self):
        store,plan,binding=self.binding();plan['slots']['extra']={}
        with self.assertRaises(ValueError):validate_replacement(store,plan,binding)

    def test_success_saves_intent_before_spawn_and_call_after(self):
        store = Store(); events = []
        fn = types.SimpleNamespace(spawn=lambda *args: (events.append('spawn') or types.SimpleNamespace(object_id='fc-one')))
        call = spawn_once(store, 'k', fn, ({'job': 1},), {}, lambda name, record: events.append(name))
        self.assertEqual(events, ['intent', 'spawn', 'submitted'])
        self.assertEqual(call.object_id, 'fc-one')
        with self.assertRaises(RuntimeError): spawn_once(store, 'k', fn, ({'job': 1},), {}, lambda *args: None)
        self.assertEqual(events.count('spawn'), 1)

    def test_lost_spawn_response_is_ambiguous_never_replayed(self):
        store = Store(); fn = types.SimpleNamespace(spawn=Mock(side_effect=OSError('lost response after admission')))
        with self.assertRaises(OSError): spawn_once(store, 'k', fn, (), {}, lambda *args: None)
        with self.assertRaises(RuntimeError): spawn_once(store, 'k', fn, (), {}, lambda *args: None)
        self.assertEqual(fn.spawn.call_count, 1)
        self.assertIn('k/intent', store.records)
        self.assertNotIn('k/submitted', store.records)

    def test_lost_local_receipt_does_not_lose_remote_call_id(self):
        store = Store(); fn = types.SimpleNamespace(spawn=Mock(return_value=types.SimpleNamespace(object_id='fc-one')))
        def save(name, record):
            if name == 'submitted': raise OSError('volume interrupted')
        with self.assertRaises(OSError): spawn_once(store, 'k', fn, (), {}, save)
        self.assertEqual(store.records['k/submitted']['call_id'], 'fc-one')
        with self.assertRaises(RuntimeError): spawn_once(store, 'k', fn, (), {}, save)
        self.assertEqual(fn.spawn.call_count, 1)

    def test_pending_poll_only_reads_existing_call(self):
        call = types.SimpleNamespace(get=Mock(side_effect=[TimeoutError(), TimeoutError(), {'done': True}]))
        check = Mock()
        self.assertEqual(wait_existing(call, check), {'done': True})
        self.assertEqual(call.get.call_count, 3); self.assertEqual(check.call_count, 3)
        call.get.assert_called_with(timeout=30)

    def test_remote_timeout_is_not_polled_forever(self):
        call = types.SimpleNamespace(get=Mock(side_effect=TimeoutError('worker deadline')))
        with self.assertRaises(TimeoutError): wait_existing(call, lambda: None, lambda: True)
        self.assertEqual(call.get.call_count, 1)

    def test_parent_interrupt_does_not_cancel_children(self):
        call = types.SimpleNamespace(get=Mock(), cancel=Mock())
        with self.assertRaises(KeyboardInterrupt): wait_existing(call, Mock(side_effect=KeyboardInterrupt))
        call.cancel.assert_not_called(); call.get.assert_not_called()

    def test_worker_failure_is_preserved(self):
        call = types.SimpleNamespace(get=Mock(side_effect=ValueError('actual failure')), cancel=Mock())
        with self.assertRaisesRegex(ValueError, 'actual failure'): wait_existing(call, lambda: None)
        call.cancel.assert_not_called()

    def test_sampler_closes_before_artifact_manifest(self):
        import threading
        observed = threading.Event()
        def smi(*args, **kwargs): observed.set(); return 'A100, 90, 20, 12000, 80000, 160, 250\n'
        with tempfile.TemporaryDirectory() as tmp, patch('subprocess.check_output', side_effect=smi):
            recorder = GPURecorder(tmp); recorder.start()
            self.assertTrue(observed.wait(2)); recorder.stop()
            records = [json.loads(x) for x in (Path(tmp)/'gpu_samples.jsonl').read_text().splitlines()]
            self.assertEqual(len(records), 1)
            self.assertIn('A100', records[0]['csv']); self.assertFalse(recorder.thread.is_alive())


if __name__ == '__main__': unittest.main()
