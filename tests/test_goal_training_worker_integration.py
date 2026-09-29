"""Whole Post-E037 worker orchestration, with NO_REAL_MODEL computation.

Set GOAL_TRAINING_TEST_TOKENIZER to the local pinned tokenizer snapshot. The
real release, encoding/dose checks, queue, publication and accounting execute.
Only temporary files are written. No weights are loaded and no GPU is used.
"""
import hashlib
import json
import os
from contextlib import ExitStack
from pathlib import Path
import signal
import tempfile
import time
import unittest
from unittest.mock import patch

import torch

from experiments.post_e037_goal_training import analyze, launcher, queue
from experiments.thursday_probe.common import dump
from src.sft_data import sha256_file


class NoParameterModel:
    def __init__(self):
        self.training = False
        self.adapter = queue.PARENT_SHA

    def cuda(self):
        return self

    def eval(self):
        return self.train(False)

    def train(self, mode=True):
        self.training = mode
        return self


def run_integration(tokenizer_dir):
    """Return mock-only first-run/resume evidence; never return model results."""
    calls = dict(train_segments=0, nll=0, new_generation_events=0, new_operator_states=0)
    registered = json.loads((queue.ROOT/'registration.json').read_text())['entries']
    run_ids = {r['state']: r['run_id'] for r in registered}

    def checkpoint_digest(run_id, step):
        return hashlib.sha256(f'{run_id}/{step}'.encode()).hexdigest()

    def parameter_digest(model, adapter_only=False):
        return dict(sha256=model.adapter if adapter_only else queue.BASE_SHA, parameters=18464768)

    def restore(model, path):
        identity = json.loads((Path(path)/'checkpoint_identity.json').read_text())
        model.adapter = identity['parameter_digest']['sha256']
        return identity

    def train(model, encoded, schedule, lrs, tokenizer, out, *, identity, end_step, deadline):
        calls['train_segments'] += 1
        # Actual frozen row counts and macro slots, but no optimization.
        history = [dict(step=s+1, seconds=.001,
            supervised_tokens=sum(encoded[i]['n_supervised'] for i in schedule[s]),
            processed_tokens=sum(encoded[i]['n_processed'] for i in schedule[s])) for s in range(end_step)]
        out = Path(out)
        (out/'recovery').mkdir(exist_ok=True)
        queue.atomic_json(out/'recovery/latest.json', dict(step=end_step))
        model.adapter = checkpoint_digest(out.name, end_step)
        for step in (128, 256):
            if end_step >= step:
                directory = out/f'checkpoint_{step}'
                directory.mkdir(exist_ok=True)
                queue.atomic_json(directory/'checkpoint_identity.json', dict(
                    parameter_digest=dict(sha256=checkpoint_digest(out.name, step), parameters=18464768),
                    files_sha256={}))
        return dict(step=end_step, cumulative_history=history)

    def generate(model, tokenizer, rows, path, event, identity, remaining, budget, deadline):
        expected = (queue.PARENT_SHA if event['state'] == 'E031' else
                    checkpoint_digest(run_ids[event['state']], event['checkpoint_step']))
        assert model.adapter == expected, 'Queue evaluated the wrong checkpoint'
        path = Path(path)
        if not path.exists():
            budget.reserve('mock_'+event['name'], event['generations'])
            path.write_text('[]\n')
            calls['new_generation_events'] += 1
        return dict(status='completed', completed_records=event['generations'], reason=None,
                    batch_timings=[], substreams=[])

    def operators(model, rows, out, state, modelhash, release, deadline):
        path = Path(out)/'operator_scores'/f'{state}.json'
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            return json.loads(path.read_text())
        calls['new_operator_states'] += 1
        record = dict(state=state, status='completed', forward_contexts=len(rows),
            candidate_scores=4*len(rows), recorded_contexts=len(rows), unavailable_contexts=0,
            forward_calls=len(rows), input_tokens=sum(len(r['context_ids']) for r in rows),
            seconds=.2, records=[])
        dump(path, record)
        return record

    def nll(model, rows, tokenizer, batch):
        calls['nll'] += 1
        return dict(nll=1., tokens=sum(r['n_supervised'] for r in rows))

    with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
        root = Path(temporary)
        out = root/'run'
        parent = root/'endpoints/thu_v2_e031_r1/checkpoint_32'
        parent.mkdir(parents=True)
        (parent/'adapter_model.safetensors').write_bytes(b'CPU-MOCK-NOT-WEIGHTS')
        dump(parent/'checkpoint_identity.json', dict(
            parameter_digest=dict(sha256=queue.PARENT_SHA, parameters=18464768),
            files_sha256={'adapter_model.safetensors': sha256_file(parent/'adapter_model.safetensors')}))
        stack.callback(signal.signal, signal.SIGTERM, signal.getsignal(signal.SIGTERM))
        stack.callback(torch.set_num_threads, torch.get_num_threads())
        stack.callback(torch.set_rng_state, torch.get_rng_state())
        stack.enter_context(patch.dict(os.environ, dict(
            GOAL_TRAINING_BOUNDED='post_e037_goal_training_v1',
            GOAL_TRAINING_DEADLINE=str(time.time()+36000), GOAL_TRAINING_PUBLISHED_COMMIT='f'*40)))
        stack.enter_context(patch.object(queue, 'OUT', out))
        stack.enter_context(patch.object(launcher, 'source', lambda *args: {'source_commit': 'f'*40}))
        stack.enter_context(patch('transformers.AutoModelForCausalLM.from_pretrained',
                                  lambda *args, **kwargs: NoParameterModel()))
        stack.enter_context(patch.object(queue, 'attach', lambda model: model))
        stack.enter_context(patch.object(queue, 'parameter_digest', parameter_digest))
        stack.enter_context(patch.object(queue, 'restore_adapter', restore))
        stack.enter_context(patch.object(queue, 'train_segment', train))
        stack.enter_context(patch.object(queue, 'run_event', generate))
        stack.enter_context(patch.object(queue, 'run_operator', operators))
        stack.enter_context(patch('src.relation_experiment.reference_nll', nll))
        stack.enter_context(patch.object(torch.cuda, 'is_available', lambda: False))
        status = queue.worker(tokenizer_dir, root/'endpoints')
        final = json.loads((out/'run_manifest_final.json').read_text())
        models, training = analyze.checkpoint_models(out, final, queue.RELEASE)
        assert status == 0 and final['status'] == 'completed'
        assert final['training_updates'] == 512 and final['generation_attempts'] == 3344
        assert final['reference_forward_calls'] == 4096 and not final['reference_incomplete_intents']
        assert len(final['evaluations']) == 21 and final['recorded_contexts'] == 288
        assert len(models) == 5 and all(r['status'] == 'completed' for r in training)
        first_calls = dict(calls)
        assert first_calls == dict(train_segments=32, nll=8, new_generation_events=21, new_operator_states=3)
        status = queue.worker(tokenizer_dir, root/'endpoints')
        resumed = json.loads((out/'run_manifest_final.json').read_text())
        assert status == 0 and calls == first_calls
        for field, expected in (('reference_forward_calls', 4096), ('generation_attempts', 3344),
                                ('training_updates', 512), ('recorded_contexts', 288)):
            assert resumed[field] == expected
        assert not resumed['reference_incomplete_intents']
        return dict(status='FULL_WORKER_AND_RESUME_CPU_MOCK_PASS', computation='NO_REAL_MODEL',
            first_run=dict(mock_calls=first_calls, registered_views=len(final['evaluations']),
                simulated_generation_reservations=final['generation_attempts'],
                simulated_training_updates=final['training_updates'],
                simulated_reference_forward_calls=final['reference_forward_calls'],
                real_encoded_reference_input_tokens=final['reference_forward_input_tokens'],
                simulated_operator_contexts=final['recorded_contexts'], analysis_checkpoint_models=len(models)),
            resume=dict(additional_mock_calls={key: calls[key]-first_calls[key] for key in calls},
                generation_reservations_unchanged=True, training_updates_unchanged=True,
                reference_totals_unchanged=True, pending_reference_intents=0),
            tokenizer=final['tokenizer'], release_manifest_sha256=final['release_manifest_sha256'],
            actual_real_tokenizer_and_frozen_dose_validated=True, real_model_calls=0,
            real_model_training_updates=0, real_generations=0, gpu_or_server_access=False)


class WholeWorkerIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('GOAL_TRAINING_TEST_TOKENIZER'),
                         'Set GOAL_TRAINING_TEST_TOKENIZER to the pinned local tokenizer snapshot')
    def test_complete_queue_and_completed_resume_publish_once(self):
        result = run_integration(os.environ['GOAL_TRAINING_TEST_TOKENIZER'])
        self.assertEqual(result['status'], 'FULL_WORKER_AND_RESUME_CPU_MOCK_PASS')


if __name__ == '__main__':
    unittest.main()
