from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.public_math_pilot_v1 import parallel_evaluate as pe
from experiments.public_math_pilot_v1 import runtime_evaluate as old
from experiments.public_math_pilot_v1.preflight import sha, write_json


class ParallelEvaluationTest(unittest.TestCase):
    def test_whole_draw_partitions_preserve_all_frozen_outputs(self):
        jobs = old.evaluation_jobs()
        before = json.dumps(jobs, sort_keys=True)
        shards = pe.partition_jobs(jobs)
        names = [[j['name'] for j in shard] for shard in shards]
        self.assertFalse(set(names[0]) & set(names[1]))
        self.assertEqual(set(names[0] + names[1]), {j['name'] for j in jobs})
        self.assertEqual([sum(pe.COUNTS[j['dataset']] for j in shard) for shard in shards], [16005, 14686])
        self.assertEqual(sum(pe.COUNTS[j['dataset']] for shard in shards for j in shard) + 512, 31203)
        self.assertEqual(json.dumps(jobs, sort_keys=True), before)
        with self.assertRaises(ValueError):
            pe.partition_jobs(jobs[:-1])
        with self.assertRaises(ValueError):
            pe.partition_jobs(jobs[:-1] + [jobs[0]])

    def test_hardware_aliases_cannot_double_allocate_one_gpu(self):
        rows = [dict(index=str(i), uuid='GPU-' + str(i), name='NVIDIA A800-SXM4-80GB',
            memory_mib=81920) for i in range(2)]
        self.assertEqual([r['uuid'] for r in pe.select_devices(rows, ['1', '0'])], ['GPU-1', 'GPU-0'])
        for selectors in (['0', '0'], ['0', 'GPU-0'], ['0'], ['0', '2']):
            with self.assertRaises(ValueError):
                pe.select_devices(rows, selectors)
        rows[1]['memory_mib'] = 40960
        with self.assertRaises(ValueError):
            pe.select_devices(rows, ['0', '1'])

    def test_one_visible_device_preserves_rng_topology_and_allocator(self):
        with patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '0,1', 'PYTORCH_CUDA_ALLOC_CONF': 'other'}):
            a = pe.child_environment('GPU-a'); b = pe.child_environment('GPU-b')
        self.assertEqual(a['CUDA_VISIBLE_DEVICES'], 'GPU-a')
        self.assertEqual(b['CUDA_VISIBLE_DEVICES'], 'GPU-b')
        self.assertEqual(a['PYTORCH_CUDA_ALLOC_CONF'], 'expandable_segments:True')

    def test_scientific_contract_equals_original_evaluator_output(self):
        identity = {'model_sha256': 'a' * 64}
        contract = {'scientific_identity': identity}
        released = {name: [dict(problem_id=f'{name}-{i}', question=str(i)) for i in range(count)]
            for name, count in pe.COUNTS.items()}
        rows = {name: [dict(id=r['problem_id'], prompt_ids=[int(r['question']), 5]) for r in rr]
            for name, rr in released.items()}
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()), \
                patch.object(old, 'prepare_identity', return_value=(None, identity, None)), \
                patch.object(old, 'load_inputs', return_value=released), \
                patch.object(old, 'encode_prompt', side_effect=lambda tok, q: [int(q), 5]), \
                patch.object(old, 'GsmOomRetryLedger', return_value=SimpleNamespace(evidence_sha256='e' * 64)), \
                patch.object(old, 'wait_endpoint', side_effect=RuntimeError('stop before model load')), \
                patch.object(old, 'load_base') as model:
            out = Path(d)
            write_json(out / 'TRAIN_CONTRACT.json', contract)
            args = SimpleNamespace(output=d, base='unused', release='unused', inputs='unused',
                ledger='unused', retry_evidence='unused', volume_root=[],
                deadline_unix=time.time() + 3600, source_commit=pe.FROZEN_SOURCE)
            with self.assertRaisesRegex(RuntimeError, 'stop before model'):
                old.run(args)
            model.assert_not_called()
            expected = pe.expected_evaluation_contract(identity, contract, rows, old.evaluation_jobs(), 'e' * 64)
            self.assertEqual(pe.read(out / 'EVALUATION_CONTRACT.json'), expected)

    def test_original_code_digest_is_enforced_after_inventory_verification(self):
        current = Path(pe.__file__).resolve().parents[2]
        name = 'experiments/public_math_pilot_v1/runtime_common.py'
        with tempfile.TemporaryDirectory() as d, patch.object(pe, 'verify_inventory') as verify:
            p = Path(d) / 'SOURCE_INVENTORY.json'
            p.write_text(json.dumps({'source_files_sha256': {name: sha(current / name)}}))
            pe.verify_original_sources(d)
            self.assertEqual(verify.call_args.kwargs['expected_source_commit'], pe.FROZEN_SOURCE)
            p.write_text(json.dumps({'source_files_sha256': {name: '0' * 64}}))
            with self.assertRaisesRegex(ValueError, 'Original model/evaluation code changed'):
                pe.verify_original_sources(d)

    def test_inherited_phase_lock_survives_coordinator_exit(self):
        with tempfile.TemporaryDirectory() as d:
            child = None
            try:
                with pe.phase_lock(d) as held:
                    with self.assertRaises(BlockingIOError):
                        with pe.phase_lock(d):
                            pass
                    child = subprocess.Popen([sys.executable, '-c',
                        'import sys; print("ready",flush=True); sys.stdin.read(1)'],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                        pass_fds=(held.fileno(),))
                    self.assertEqual(child.stdout.readline().strip(), 'ready')
                with self.assertRaises(BlockingIOError):
                    with pe.phase_lock(d):
                        pass
                child.communicate('x', timeout=10)
                with pe.phase_lock(d):
                    pass
            finally:
                if child is not None and child.poll() is None:
                    child.kill(); child.communicate()

    def test_concurrent_physical_reservations_are_serialized(self):
        with tempfile.TemporaryDirectory() as d:
            script = ('import sys; from experiments.public_math_pilot_v1.runtime_common import PhysicalLedger; '
                'PhysicalLedger(sys.argv[1]).reserve("generation",[sys.argv[2]+str(i) for i in range(64)])')
            ledger = str(Path(d) / 'ledger.jsonl')
            children = [subprocess.Popen([sys.executable, '-c', script, ledger, prefix],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for prefix in ('a', 'b')]
            for child in children:
                _, err = child.communicate(timeout=30)
                self.assertEqual(child.returncode, 0, err)
            entries = [json.loads(line) for line in Path(ledger).read_text().splitlines()]
            self.assertEqual(len(entries), 128)
            self.assertEqual(len({e['logical_id'] for e in entries}), 128)
            self.assertEqual([e['ordinal'] for e in entries], list(range(1, 129)))

    def completion_fixture(self, root):
        jobs = old.evaluation_jobs(); attempt = root / 'attempt'; attempt.mkdir()
        write_json(root / 'EVALUATION_CONTRACT.json', {'frozen': True})
        for job in jobs + [{'name': 'Base-dev'}]:
            folder = root / 'generation' / job['name']; folder.mkdir(parents=True)
            write_json(folder / 'COMPLETE.json', {'logical_name': job['name']})
        args = SimpleNamespace(output=str(root), source_commit='f' * 40, volume_root=[])
        for rank, shard in enumerate(pe.partition_jobs(jobs)):
            write_json(attempt / f'WORKER_{rank}_RESULT.json', dict(rank=rank,
                source_commit=args.source_commit, status='complete', runs=[dict(name=j['name'],
                    completion_sha256=sha(root / 'generation' / j['name'] / 'COMPLETE.json')) for j in shard]))
        return args, attempt, jobs

    def test_closeout_rejects_a_changed_completion_before_any_pruning(self):
        with tempfile.TemporaryDirectory() as d, patch('experiments.public_math_pilot_v1.runtime_train.store_for') as store:
            root = Path(d); args, attempt, jobs = self.completion_fixture(root)
            (root / 'generation' / jobs[0]['name'] / 'COMPLETE.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'completion changed'):
                pe.finalize(args, attempt, jobs, {}, {})
            self.assertFalse((root / 'EVALUATION_COMPLETE.json').exists())
            store.assert_not_called()

    def test_closeout_merges_in_original_order_and_only_then_prunes(self):
        with tempfile.TemporaryDirectory() as d, patch('experiments.public_math_pilot_v1.runtime_train.store_for') as store:
            root = Path(d); args, attempt, jobs = self.completion_fixture(root)
            from experiments.public_math_pilot_v1.losses import ARMS
            done = {'endpoints': {a: {'64': {'checkpoint': a}} for a in ARMS}}
            value = pe.finalize(args, attempt, jobs, {}, done)
            self.assertEqual([r['name'] for r in value['runs']], [j['name'] for j in jobs])
            self.assertEqual(value['total_generations'], 31203)
            self.assertEqual(store.call_count, 4)
            self.assertEqual(store.return_value.prune_scientific_temp.call_count, 4)

    def test_pause_request_prevents_worker_model_calls(self):
        import torch
        jobs = old.evaluation_jobs()
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()), \
                patch.dict(os.environ, pe.child_environment('GPU-a')), \
                patch.object(torch.cuda, 'device_count', return_value=1), \
                patch.object(pe, 'checked_context', return_value=(None, {}, {}, {}, {}, None, jobs)), \
                patch('experiments.public_math_pilot_v1.preflight.load_base') as load:
            root = Path(d); attempt = root / 'attempt'; attempt.mkdir()
            args = SimpleNamespace(worker_rank=0, output=d, attempt_dir=str(attempt), source_commit='f' * 40)
            write_json(attempt / 'START.json', dict(source_commit=args.source_commit, devices=[{'uuid': 'GPU-a'}]))
            write_json(root / 'EVALUATION_CONTRACT.json', {})
            write_json(root / 'DUAL_GPU_CONTRACT.json', pe.parallel_contract(args, jobs))
            write_json(root / 'EVALUATION_PAUSE_AFTER_RUN.json', {'reason': 'owner-requested maintenance'})
            with pe.phase_lock(d) as lock:
                args.owner_lock_fd = lock.fileno()
                result = pe.worker(args)
            self.assertEqual(result['status'], 'paused')
            self.assertEqual(result['runs'], [])
            load.assert_not_called()


if __name__ == '__main__':
    unittest.main()
