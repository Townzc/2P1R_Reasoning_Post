"""Mocked worker integration: frozen ordering, parents, and interrupted finalization."""
from contextlib import ExitStack, nullcontext, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.thursday_probe_v2 import resume_queue as queue


class QueueIntegrationTests(unittest.TestCase):
    def test_frozen_complete_remaining_plan(self):
        plan = queue.dry_run()
        self.assertEqual((plan['updates'], plan['new_generations']), (1088, 4192))
        self.assertEqual([r['experiment_id'] for r in plan['runs']], [f'E{i:03}' for i in range(31, 37)])
        self.assertEqual([r['state'] for r in plan['runs']], ['C', 'B', 'C-S', 'C-P', 'B-S', 'B-P'])
        self.assertEqual([r['parent'] for r in plan['runs']], ['C0', 'C0', 'C', 'C', 'B', 'B'])
        self.assertEqual(sum(e['generations'] for e in plan['events'] if e['view'] == 'train_diagnostic'), 64)
        self.assertEqual(plan['planned_cumulative_generations'], 4784)
        self.assertFalse(plan['outcomes_affect_queue'])

    def mocked_worker(self, root, *, pause_final_once=False):
        import torch
        inputs, regs, schedules, lrs, doses, events = queue.frozen_inputs()
        model = SimpleNamespace(adapter=None, parameters=lambda: [], cuda=lambda: model)
        digest = lambda value: dict(sha256=hashlib.sha256(value.encode()).hexdigest(), parameters=1)
        initial = root / 'original_C0'; initial.mkdir(exist_ok=True)
        checkpoint_map = {str(initial): dict(sha256=queue.C0_SHA, parameters=1)}
        states = {}; train_calls = []; evaluations = []; paused = False
        out = root / 'resume'; out.mkdir(exist_ok=True)
        by_id = {r['run_id']: r for r in regs}

        class Budget:
            def __init__(self, _path): pass
            used = 4784

        def restore(current, path):
            current.adapter = checkpoint_map[str(path)]
            return dict(parameter_digest=current.adapter)

        def train(current, encoded, schedule, learning_rates, tokenizer, folder, *, identity, end_step, deadline):
            folder = Path(folder); reg = by_id[folder.name]
            self.assertEqual(len(schedule), reg['updates'])
            self.assertEqual(schedule, schedules['prep' if reg['state'] in ('C', 'B') else 'main'])
            self.assertEqual(learning_rates, lrs['prep' if reg['state'] in ('C', 'B') else 'main'])
            expected_parent = (checkpoint_map[str(initial)] if reg['parent'] == 'C0' else
                states[next(r['run_id'] for r in regs if r['state'] == reg['parent'])]['final_adapter'])
            self.assertEqual(identity['parent'], expected_parent)
            prior = states.get(folder.name)
            start = prior['step'] if prior else 0
            train_calls.append((reg['state'], start, end_step))
            history = list(prior['cumulative_history']) if prior else []
            for step in range(start + 1, end_step + 1):
                history.append(dict(step=step, seconds=.01,
                    supervised_tokens=doses[reg['data']]['supervised_response_tokens'] if step == 1 else 0,
                    processed_tokens=doses[reg['data']]['processed_nonpadding_tokens'] if step == 1 else 0))
                if step in (32, 64, 128, 256):
                    checkpoint_map[str(folder / f'checkpoint_{step}')] = digest(folder.name + str(step))
            current.adapter = digest(folder.name + str(end_step))
            recovery = folder / 'recovery'; recovery.mkdir(exist_ok=True)
            (recovery / 'latest.json').write_text(json.dumps(dict(step=end_step)))
            result = dict(step=end_step, status='completed' if end_step == reg['updates'] else 'partial',
                cumulative_history=history, final_adapter=current.adapter, checkpoints={},
                initial_adapter=expected_parent, fingerprint='a' * 64)
            states[folder.name] = result
            return result

        def nll(current, rows, tokenizer, microbatch):
            nonlocal paused
            main = next(r for r in regs if r['state'] == 'C-S')
            endpoint = digest(main['run_id'] + '256')
            if pause_final_once and not paused and current.adapter == endpoint:
                paused = True
                raise queue.SegmentPause('injected endpoint-finalization interruption')
            return dict(nll=1., supervised_tokens=len(rows), reference_count=len(rows))

        def evaluate(current, tokenizer, rows, path, event, identity, limit, budget, deadline):
            reg = next(r for r in regs if r['state'] == event['state'])
            step = 128 if event['view'] == 'midpoint' else reg['updates']
            expected = digest(reg['run_id'] + str(step))
            self.assertEqual(current.adapter, expected, event['name'])
            self.assertEqual(identity['model_hash'], expected['sha256'])
            evaluations.append((event['state'], event['view'], step, limit))
            count = min(event['generations'], 8 if limit == 1 else event['generations'])
            records = [dict(problem_id=f'fake_{i}', sample_index=0) for i in range(count)]
            Path(path).write_text(''.join(json.dumps(row) + '\n' for row in records))
            progress = Path(path).with_suffix('.resume'); progress.mkdir(exist_ok=True)
            (progress / 'progress.json').write_text(json.dumps(dict(completed_batches=(count + 7)//8)))
            return dict(status='completed' if count == event['generations'] else 'partial',
                records=records, batch_timings=[], reason=None, request_ids=list(range(event['generations'])),
                new_batches=(count + 7)//8)

        stack = ExitStack()
        stack.enter_context(patch.object(queue, 'OUT', out))
        stack.enter_context(patch.dict(os.environ, THU_RESUME_BOUNDED=out.name,
                                      THU_RESUME_DEADLINE=str(time.time()+100000)))
        stack.enter_context(patch.object(queue, 'source', return_value=dict(source_commit='f'*40, source_files_sha256={})))
        stack.enter_context(patch.object(queue, 'ResumeGenerationBudget', Budget))
        stack.enter_context(patch.object(queue, 'admit_unit', return_value=True))
        stack.enter_context(patch.object(queue, 'verified_tokenizer', return_value=(SimpleNamespace(eos_token='EOS'), {})))
        stack.enter_context(patch.object(queue, 'encode_row', return_value=dict(n_supervised=1,n_processed=1)))
        stack.enter_context(patch('transformers.AutoModelForCausalLM.from_pretrained', return_value=model))
        stack.enter_context(patch.object(torch.cuda, 'reset_peak_memory_stats'))
        stack.enter_context(patch.object(queue, 'attach', side_effect=lambda current: current))
        stack.enter_context(patch.object(queue, 'parameter_digest', side_effect=lambda current, adapter=False:
            current.adapter if adapter else dict(sha256=queue.BASE_SHA, parameters=1)))
        stack.enter_context(patch.object(queue, 'restore_adapter', side_effect=restore))
        stack.enter_context(patch.object(queue, 'train_segment', side_effect=train))
        stack.enter_context(patch.object(queue, 'reference_nll', side_effect=nll))
        stack.enter_context(patch.object(queue, '_caller_state', side_effect=lambda current: nullcontext()))
        stack.enter_context(patch.object(queue, 'run_batches', side_effect=evaluate))
        stack.enter_context(patch.object(queue, 'summarize', side_effect=lambda records: dict(count=len(records))))
        stack.enter_context(patch.object(queue.signal, 'signal'))
        stack.enter_context(redirect_stdout(io.StringIO()))
        return stack, initial, out, train_calls, evaluations

    def test_complete_worker_preserves_parent_and_midpoint_order(self):
        with tempfile.TemporaryDirectory() as folder:
            stack, initial, out, train_calls, evaluations = self.mocked_worker(Path(folder))
            with stack:
                self.assertEqual(queue.worker('FAKE_SNAPSHOT', initial), 0)
            self.assertEqual(train_calls[:2], [('C', 0, 32), ('B', 0, 32)])
            self.assertEqual(train_calls[2:6], [('C-S', 0, 64), ('C-S', 64, 128),
                                               ('C-S', 128, 192), ('C-S', 192, 256)])
            self.assertEqual([e[:2] for e in evaluations[:4]], [('C', 'probes'), ('C', 'discovery_sampled'),
                                                               ('B', 'probes'), ('B', 'discovery_sampled')])
            self.assertEqual([e[2] for e in evaluations if e[1]=='midpoint'], [128]*4)
            result = json.loads((out/'run_manifest_final.json').read_text())
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(len(result['runs']), 6)
            self.assertTrue(all(r['status']=='completed' for r in result['runs']))

    def test_resume_committed_endpoint_restores_before_final_nll(self):
        with tempfile.TemporaryDirectory() as folder:
            stack, initial, out, train_calls, evaluations = self.mocked_worker(Path(folder), pause_final_once=True)
            with stack:
                self.assertEqual(queue.worker('FAKE_SNAPSHOT', initial), 75)
                self.assertEqual(queue.worker('FAKE_SNAPSHOT', initial), 0)
            self.assertIn(('C-S', 256, 256), train_calls)
            self.assertEqual(sum(call==('C',0,32) for call in train_calls),1)
            self.assertEqual(sum(call==('B',0,32) for call in train_calls),1)
            self.assertEqual(sum(e[:2]==('C-S','midpoint') for e in evaluations),1)
            result = json.loads((out/'run_manifest_final.json').read_text())
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(len(result['runs']), 6)


if __name__ == '__main__':
    unittest.main()
