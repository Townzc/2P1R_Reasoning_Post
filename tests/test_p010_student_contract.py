import ast
import copy
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
from experiments.p010.common import read, dump, digest
from experiments.p010.student_contract import CELLS, evaluation_jobs, sampling, forecast
from experiments.p010.student_training import checked_recipe


class StudentChecks(unittest.TestCase):
    def test_new_multi_answer_recipe_preserves_dose(self):
        for k in (4, 8):
            root = Path('.local/p010_20261019/r1/student_inputs_r1')/f't15_s17_n400_k{k}'
            config, rows, plan = [read(root/(n+'.json')) for n in ('config', 'encoded', 'plan')]
            recipe = checked_recipe(config, rows, plan)
            self.assertEqual(recipe['budget']['supervised_response_tokens'], 2097148)
            self.assertEqual(recipe['endpoint_repetitions'], 5)

    def test_wrong_seed_original_cell_and_truncated_answer_rejected(self):
        root = Path('.local/p010_20261019/r1/student_inputs_r1/t15_s17_n400_k4')
        config, encoded, plan = [read(root/(n+'.json')) for n in ('config', 'encoded', 'plan')]
        for field, value in [('seed', 29), ('run_id', 't15_s17_n400_k1'), ('targets', 2097147), ('P', 401)]:
            bad = dict(config, **{field: value})
            with self.assertRaises(ValueError):
                checked_recipe(bad, encoded, plan)
        bad = copy.deepcopy(encoded)
        bad[0]['input_ids'].pop()
        with self.assertRaises(ValueError):
            checked_recipe(config, bad, plan)

    def test_original_training_body_identical(self):
        def body(name):
            tree = ast.parse(Path(name).read_text())
            return ast.dump(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='train_and_merge'))
        self.assertEqual(body('experiments/p010/student_training.py'),
            body('experiments/learning_regime_p009/stage1_training_core.py'))

    def test_fixed_grid_and_sample_seeds(self):
        self.assertEqual(len(CELLS), 15)
        self.assertNotIn('t15_s17_n400_k1', CELLS)
        self.assertEqual([x[1] for x in evaluation_jobs()], [17, 0, 1, 2, 3])
        self.assertEqual([sampling(x)['temperature'] for x in evaluation_jobs()], [0, .6, .6, .6, .6])
        with self.assertRaises(ValueError):
            sampling(('sample9', 9, .6, .95))

    def test_all_batches_time_and_budget_retained(self):
        proof = forecast(0, 64, 10, [43.307480978], [20.412141323], 19.65)
        self.assertLess(proof['forecast_total_seconds'], 4470)
        with self.assertRaises(TimeoutError):
            forecast(0, 64, 10, [43.307480978, 100], [20.412141323], 19.65)
        with self.assertRaises(ValueError):
            forecast(0, 64, 10, [43.307480978], [20.412141323], 145)

    def test_actual_worker_emits_five_endpoints_and_replay_preserves_original(self):
        tree = ast.parse(Path('experiments/p010/modal_students.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='worker')
        fn.decorator_list = []
        store = {}

        class Store:
            def put(self, key, value, **kwargs):
                if key in store:
                    return False
                store[key] = value
                return True
            def get(self, key):
                return store.get(key)

        class Pipe:
            def poll(self, timeout): return True
            def recv(self): return 'complete', {'updates': 1024, 'targets': 2097148}, [1.]
            def close(self): pass

        class Proc:
            pid = 123
            exitcode = 0
            def __init__(self, **kwargs): pass
            def start(self): pass
            def join(self, **kwargs): pass
            def is_alive(self): return False

        class Engine:
            calls = 0
            llm_engine = types.SimpleNamespace(vllm_config={})
            def __init__(self, **kwargs): pass
            def generate(self, prompts, params, **kwargs):
                Engine.calls += 1
                return [types.SimpleNamespace(prompt_token_ids=x['prompt_token_ids'],
                    outputs=[types.SimpleNamespace(token_ids=[11, 151643], text='answer',
                        finish_reason='stop', stop_reason=None)]) for x in prompts]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def localpath(name):
                text = str(name)
                return root/text.lstrip('/') if text.startswith('/') else Path(name)
            volume = types.SimpleNamespace(commit=lambda: None, reload=lambda: None)
            run = 't15_s17_n400_k4'
            inputs = root/'evidence/p010-20261019/student_inputs'
            dump(inputs/run/'config.json', {'recipe': 'mocked training child'})
            dump(inputs/'MATH_ENDPOINT.json', [dict(candidate_id=str(i), problem_id=str(i),
                source_row_sha256='fixture', input_ids=[1, 2]) for i in range(500)])
            spec = dict(configs={run: {'recipe': 'mocked training child'}}, input_files={},
                source_files={}, model={'files': {}}, timing={'training_seconds': [1.], 'endpoint_seconds': [1.]})
            dump(root/'workspace/SPEC.json', spec)
            ns = dict(Path=localpath, SPEC='SPEC.json', volume=volume,
                modal=types.SimpleNamespace(Dict=types.SimpleNamespace(from_name=lambda *a,**kw: Store())))
            exec(compile(ast.Module(body=[fn], type_ignores=[]), '<actual worker>', 'exec'), ns)
            context = types.SimpleNamespace(Pipe=lambda: (Pipe(), Pipe()), Process=Proc)
            fake_vllm = types.SimpleNamespace(LLM=Engine, SamplingParams=lambda **kw: kw)
            with patch('multiprocessing.get_context', return_value=context), \
                    patch('experiments.p010.common.read', side_effect=lambda name: read(localpath(name)) if str(name).startswith('/workspace/') else read(name)), \
                    patch.dict('sys.modules', {'vllm': fake_vllm}), \
                    patch('experiments.p010.runtime_support.source_check'), \
                    patch('experiments.p010.runtime_support.hard_timer', return_value=types.SimpleNamespace(cancel=lambda: None)), \
                    patch('experiments.learning_regime_p009.high_throughput_v1.actual_engine', return_value={}):
                result = ns['worker'](run, 'fixture', {}, '0')
                self.assertEqual(result['result']['raw_endpoint_count'], 2500)
                self.assertEqual(Engine.calls, 10)
                out = root/'evidence/p010-20261019/students'/run
                terminal = (out/'TERMINAL.json').read_bytes()
                with self.assertRaises(RuntimeError):
                    ns['worker'](run, 'fixture', {}, '0')
                self.assertEqual((out/'TERMINAL.json').read_bytes(), terminal)
                self.assertFalse((out/'FAILURE.json').exists())
                self.assertEqual(Engine.calls, 10)


if __name__ == '__main__':
    unittest.main()
