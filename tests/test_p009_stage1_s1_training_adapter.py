"""Execute the new S1 training-child adapter with fully mocked GPU/Modal/core."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from experiments.sft_allocation_midpoint.common import read
from experiments.learning_regime_p009 import stage1_s1_training_process as worker
from tests.test_p009_stage1_s1_execution import limits


class S1TrainingAdapter(unittest.TestCase):
    def exercise(self, run, wrong_config=False):
        root = Path('.local/p009_20261014/r1/stage1_s1_inputs_r1')
        cfg = read(root/(run+'_config.json'))
        if wrong_config: cfg = dict(cfg, seed=17 if cfg['seed']==29 else 29)
        reads = []
        def fake_read(path):
            reads.append(Path(path).name)
            return cfg if str(path).endswith('_config.json') else []
        fake_torch = SimpleNamespace(set_num_threads=Mock(), get_num_threads=lambda:4,
            cuda=SimpleNamespace(is_available=lambda:True, device_count=lambda:1,
            get_device_name=lambda _: 'SYNTHETIC H100',
            get_device_properties=lambda _:SimpleNamespace(total_memory=80*1024**3)))
        volume = Mock(); store = {}; guard = SimpleNamespace(prefix='synthetic/')
        fake_modal = SimpleNamespace(Volume=SimpleNamespace(from_name=lambda *a,**k:volume),
                                    Dict=SimpleNamespace(from_name=lambda *a,**k:store))
        checker = Mock(); checker.metrics = {'synthetic':True}
        journal = SimpleNamespace(new_full_blocks=[1.]*64, metrics={'synthetic':True})
        trained = dict(updates=1024, targets=2097148, checkpoint={'synthetic':True})
        core = Mock(return_value=trained); connection = Mock(); start = worker.time.time()-1
        with tempfile.TemporaryDirectory() as folder:
            paths = dict(out=folder, base='synthetic-base', tokenizer='synthetic-base',
                         inputs='synthetic-inputs', merged=str(Path(folder)/'merged'))
            identity = dict(config=cfg, run_id=run, base_files={'synthetic':True},
                            input_files={'synthetic':True})
            with patch.dict('os.environ', {'CUBLAS_WORKSPACE_CONFIG':':4096:8'}), \
                 patch.dict('sys.modules', {'torch':fake_torch, 'modal':fake_modal}), \
                 patch.object(worker, 'verify'), patch.object(worker, 'read', side_effect=fake_read), \
                 patch.object(worker, 'MeasuredS1Journal', return_value=journal) as factory, \
                 patch('experiments.sft_allocation_midpoint.guard.RunGuard', return_value=guard), \
                 patch('experiments.sft_allocation_p008.parallel_guard.ParallelActiveCheck', return_value=checker), \
                 patch('experiments.learning_regime_p009.stage1_training_core.train_and_merge', core):
                args = (connection, paths, {'synthetic':True}, SimpleNamespace(), identity,
                        dict(training_block_seconds=[1.], endpoint_batch_seconds=[1.]),
                        3690, limits(), start, start+4000)
                if wrong_config:
                    with self.assertRaises(ValueError):worker.child(*args)
                    core.assert_not_called(); factory.assert_not_called()
                    self.assertEqual(connection.send.call_args.args[0][0], 'error')
                else:
                    worker.child(*args); core.assert_called_once()
                    self.assertEqual(reads, [run+'_'+k+'.json' for k in ('rows','encoded','plan','config')])
                    self.assertEqual(factory.call_args.kwargs['limits'], limits())
                    self.assertEqual(core.call_args.args[-1]['config']['seed'], cfg['seed'])
                    result = read(Path(folder)/'TRAINING_CHILD_RESULT.json')
                    self.assertEqual((result['updates'], result['targets'], result['new_generations']),
                                     (1024, 2097148, 0))
                    self.assertEqual(connection.send.call_args.args[0][0], 'trained')
                connection.close.assert_called_once()

    def test_actual_adapter_preserves_seed29_and_s1_filename_without_model_calls(self):
        self.exercise('s1_s29_n3200')

    def test_foreign_seed_rejected_before_any_training_core(self):
        self.exercise('s1_s29_n3200', wrong_config=True)


if __name__ == '__main__':unittest.main()
