"""New actual worker-body control checks with wholly synthetic providers only."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


c = load('experiments.p010.e3_contract', 'e3_contract.py')
rt = load('e3_runtime_worker_fixture', 'e3_runtime.py')
fixtures = load('e3_contract_fixture_only', 'test_e3_contract.py')


class Store:
    def __init__(self):
        self.data = {c.KEY + '/claim': {'synthetic': True}}

    def get(self, key):
        return self.data.get(key)

    def put(self, key, value, skip_if_exists=False):
        if skip_if_exists and key in self.data:
            return False
        self.data[key] = value
        return True


class ActualBody(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.inputs = self.root / 'inputs'
        self.out = self.root / 'out'
        self.inputs.mkdir()
        self.out.mkdir()
        self.roster, groups = fixtures.fixture()
        rt.dump(self.inputs / 'ROSTER.json', self.roster)
        for label, rows in groups.items():
            rt.dump(self.inputs / (label + '_requests.json'), rows)
        rt.dump(self.inputs / 'PROMPT_TEXTS.json', [
            dict(problem_id=p, problem='synthetic', prompt_token_ids=[17, 29])
            for p in self.roster['problem_ids']])
        self.model = dict(model_id=rt.MODELS['t72'][0], revision=rt.MODELS['t72'][1],
                          remote_path=str(self.root / 'model'), files={})
        rt.dump(self.root / 'model/config.json', {'vocab_size': 152000})
        self.store = Store()
        self.calls = []
        self.transports = []
        self.generated = []
        self.mismatch = False
        self.transport_failure = False
        self.claim_tamper = False
        self.gpu_count = 4
        outer = self

        class Tokenizer:
            all_special_ids = [151643, 151645]
            eos_token_id = 151645

            def get_vocab(self):
                return {'synthetic': 17, 'eos': 151645}

            def apply_chat_template(self, *args, **kwargs):
                return [17, 29]

        class LLM:
            def __init__(self, **kwargs):
                outer.assertTrue((outer.out / 'BEFORE_MODEL_FORECAST.json').exists())
                outer.assertEqual(kwargs['tensor_parallel_size'], 4)
                self.llm_engine = types.SimpleNamespace(vllm_config=types.SimpleNamespace(
                    parallel_config=types.SimpleNamespace(tensor_parallel_size=4)))
                if outer.claim_tamper:
                    outer.store.data[c.KEY + '/claim'] = {'different': True}

            def generate(self, prompts, params, use_tqdm):
                outer.calls.append((len(prompts), params))
                return [None] * len(prompts)

        def returned(rows, params, outputs):
            values = [dict(candidate_id=r['candidate_id'], prompt_token_ids=r['prompt_token_ids'],
                           output_count=1, sampling=p, token_ids=[17, 151645],
                           finish_reason='stop', stop_reason=151645)
                      for r, p in zip(rows, params)]
            if outer.mismatch:
                values[0]['candidate_id'] = 'wrong'
            outer.generated.extend(values)
            return values

        def completion(raw, *args):
            # The production body must preserve raw first, even when validation fails.
            outer.assertTrue(list((outer.out / 'raw').rglob('*.json')))
            outer.transports.append(raw['candidate_id'])
            if outer.transport_failure:
                raise ValueError('synthetic transport failure')
            return {'stop_reason': 'native_eos'}, {'synthetic': True}

        self.modules = {
            'torch': types.SimpleNamespace(cuda=types.SimpleNamespace(
                device_count=lambda: outer.gpu_count, get_device_name=lambda i: 'NVIDIA H100',
                get_device_properties=lambda i: types.SimpleNamespace(total_memory=80 * 1024**3))),
            'transformers': types.SimpleNamespace(AutoTokenizer=types.SimpleNamespace(
                from_pretrained=lambda *a, **k: Tokenizer())),
            'vllm': types.SimpleNamespace(LLM=LLM, SamplingParams=lambda **k: k),
            'experiments.learning_regime_p009.high_throughput_v1': types.SimpleNamespace(
                engine_kwargs=lambda: {}, actual_engine=lambda value: {'synthetic': True}),
            'experiments.learning_regime_p009.stage0_generation_engine_v2': types.SimpleNamespace(
                returned_records=returned),
            'experiments.p010.teacher_transport': types.SimpleNamespace(completion=completion),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self):
        with patch.dict(sys.modules, self.modules), patch.object(rt, 'verify', lambda *a: None), \
                patch.object(rt.time, 'time', return_value=1):
            return rt.generate(self.inputs, self.out, self.model, {'synthetic': True},
                               0, 1800, {'original_full_batch_seconds': [38.1],
                                         'observed_pre_first_batch_seconds': 457.34},
                               self.store, types.SimpleNamespace(commit=lambda: None))

    def test_all_original_3200_and_14_forecasts_no_t08(self):
        result = self.invoke()
        self.assertEqual(result['new_outputs'], 3200)
        self.assertEqual(result['saved_T08_regenerated'], 0)
        self.assertEqual(len(self.calls), 14)
        self.assertEqual(len(self.transports), 3200)
        self.assertEqual(len(list((self.out / 'forecasts').rglob('*.json'))), 14)
        self.assertEqual({x['sampling']['temperature'] for x in self.generated}, {.6, 1.})
        self.assertEqual(len({x['candidate_id'] for x in self.generated}), 3200)

    def test_raw_survives_transport_failure_before_done_ack(self):
        self.transport_failure = True
        with self.assertRaisesRegex(ValueError, 'synthetic transport'):
            self.invoke()
        self.assertEqual(len(self.calls), 1)
        self.assertTrue((self.out / 'raw/t06/0000.json').exists())
        self.assertFalse(any(k.startswith(c.KEY + '/done/') for k in self.store.data))

    def test_raw_identity_failure_preserved_without_ack(self):
        self.mismatch = True
        with self.assertRaisesRegex(ValueError, 'raw identity'):
            self.invoke()
        self.assertTrue((self.out / 'raw/t06/0000.json').exists())
        self.assertEqual(self.transports, [])

    def test_prior_batch_intent_blocks_regeneration(self):
        self.store.data[c.KEY + '/batch/t06/0000'] = {'old': True}
        with self.assertRaisesRegex(RuntimeError, 'already attempted'):
            self.invoke()
        self.assertEqual(self.calls, [])

    def test_claim_change_blocks_first_generation(self):
        self.claim_tamper = True
        with self.assertRaisesRegex(ValueError, 'claim changed'):
            self.invoke()
        self.assertEqual(self.calls, [])

    def test_wrong_GPU_allocation_blocks_model(self):
        self.gpu_count = 1
        with self.assertRaisesRegex(ValueError, 'TP4'):
            self.invoke()
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
