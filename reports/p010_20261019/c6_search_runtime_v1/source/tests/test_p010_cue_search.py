"""New search contract and actual worker-body mocks; no model or original data."""
import ast
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.p010.cue_search_contract import forecast, sampling, screen_rows
from experiments.p010.common import dump, read, sha


def dev_rows():
    return [dict(problem_id=f'synthetic/{i}', input_ids=[21,22,23]) for i in range(30)]


def proposal():
    return dict(problem_ids=[r['problem_id'] for r in dev_rows()], beam_width=20,
        maximum_depth=2, gold_used=False, correctness_used=False,
        candidates=[dict(token_ids=[i]) for i in range(1,21)])


class ContractTests(unittest.TestCase):
    def test_complete_pairing_roster_and_sampling(self):
        rows = screen_rows(dev_rows(), proposal(), range(1,24))
        self.assertEqual(len(rows), 10080)
        self.assertEqual(len({r['candidate_id'] for r in rows}), 10080)
        self.assertEqual(rows[0]['input_ids'], [21,22,23])
        self.assertEqual(rows[480]['input_ids'], [21,22,23,1])
        self.assertEqual([r['rollout'] for r in rows[:480:30]], list(range(16)))
        self.assertTrue(all(sampling(i)['max_tokens'] == 1024 and sampling(i)['seed'] == i for i in range(16)))

    def test_no_gold_or_reordered_original_rows(self):
        rows = dev_rows(); rows[0]['solution'] = 'forbidden'
        with self.assertRaises(ValueError): screen_rows(rows, proposal(), range(1,24))
        with self.assertRaises(ValueError): screen_rows(dev_rows()[::-1], proposal(), range(1,24))

    def test_no_unsupported_or_duplicate_cues(self):
        p = proposal(); p['candidates'][0]['token_ids'] = [151643]
        with self.assertRaises(ValueError): screen_rows(dev_rows(), p, range(1,24))
        p = proposal(); p['candidates'][0] = p['candidates'][1]
        with self.assertRaises(ValueError): screen_rows(dev_rows(), p, range(1,24))

    def test_complete_time_history_and_no_bootstrap_exception(self):
        f = forecast(0, 0, [], [11.55,10.4], '0', proposal_complete=False)
        self.assertAlmostEqual(f['total_seconds'], 1634.4)
        self.assertEqual(f['first_paid_measurement_exceptions'], 0)
        self.assertEqual(f['proposal_allowance_seconds'], 300)
        with self.assertRaises(ValueError): forecast(1,1,[],[11.55],'0',proposal_complete=True)
        with self.assertRaises(TimeoutError): forecast(0,0,[],[30.],'0',proposal_complete=False)

    def test_all_actual_maximum_and_budget_retention(self):
        f = forecast(30,1,[15.],[11.55],'0',proposal_complete=True)
        self.assertEqual(f['maximum_seconds'],15.)
        self.assertEqual(f['actual_completed_seconds'],[15.])
        with self.assertRaises(ValueError): forecast(0,0,[],[11.55],'12',proposal_complete=False)
        with self.assertRaises(ValueError): sampling(16)


class Store:
    def __init__(self): self.values = {}
    def get(self,key): return self.values.get(key)
    def put(self,key,value,skip_if_exists):
        if key in self.values: return False
        self.values[key] = value
        return True


class WorkerTests(unittest.TestCase):
    def run_body(self, proc_exit=0, already_claimed=False):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        def mapped(path):
            if str(path).startswith('/evidence/'):
                return base/str(path).removeprefix('/')
            return Path(path)
        inp = mapped('/evidence/p010-20261019/cue_inputs_r1/DEV_PROMPTS.json')
        dump(inp,dev_rows())
        out = mapped('/evidence/p010-20261019/cue/search_r1')
        s = dict(dev_input_sha256=sha(inp), source_files={}, batch_observations_seconds=[11.55],
                 model={'remote_path':'synthetic/base','tokenizer_remote_path':'synthetic/base'})
        sp = base/'SPEC.json'; dump(sp,s)
        store = Store()
        if already_claimed: store.values['cue/search_r1/claim'] = {'old':True}
        volume = types.SimpleNamespace(commit=lambda:None,reload=lambda:None)
        timer = types.SimpleNamespace(cancel=lambda:None)
        counter = {'llm':0,'generated':0,'process_start':0,'joined':False}
        class Process:
            exitcode = proc_exit
            pid = 1234
            def __init__(self,*args,**kwargs): pass
            def start(self):
                counter['process_start'] += 1
                dump(out/'PROPOSAL.json',proposal())
                dump(out/'ALLOWED_CUE_TOKENS.json',list(range(1,24)))
            def join(self,timeout): counter['joined'] = True
            def is_alive(self): return False
        parent = types.SimpleNamespace(poll=lambda _:True,recv=lambda:('complete',{}))
        remote = types.SimpleNamespace(close=lambda:None)
        ctx = types.SimpleNamespace(Pipe=lambda:(parent,remote),Process=Process)
        class LLM:
            def __init__(self,**kwargs):
                self.llm_engine = types.SimpleNamespace(vllm_config=None)
                self.assert_exit = counter['joined'] and proc_exit == 0
                assert self.assert_exit
                counter['llm'] += 1
            def generate(self,prompts,params,use_tqdm):
                counter['generated'] += len(prompts)
                return [types.SimpleNamespace(prompt_token_ids=p['prompt_token_ids'], outputs=[
                    types.SimpleNamespace(token_ids=[31,151643],text='synthetic',finish_reason='stop',stop_reason=151643)])
                    for p in prompts]
        tree = ast.parse(Path('experiments/p010/modal_cue_search.py').read_text())
        node = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='worker')
        node.decorator_list = []
        fake_modal = types.SimpleNamespace(Dict=types.SimpleNamespace(from_name=lambda *a,**kw:store))
        ns = dict(Path=mapped,modal=fake_modal,volume=volume,SPEC=str(sp))
        # '/workspace/'+SPEC points to a synthetic map; no real runtime is imported.
        actual_read = read
        def fixture_read(path):
            return s if str(path) == '/workspace/'+str(sp) else actual_read(path)
        ns['read'] = fixture_read
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual C6 worker body>','exec'),ns)
        with patch('experiments.p010.common.read',side_effect=fixture_read), \
             patch('experiments.p010.runtime_support.source_check'), \
             patch('experiments.p010.runtime_support.hard_timer',return_value=timer), \
             patch('experiments.p010.runtime_support.compact',return_value={'synthetic':True}), \
             patch('multiprocessing.get_context',return_value=ctx), \
             patch('experiments.learning_regime_p009.high_throughput_v1.actual_engine',return_value={'synthetic':True}), \
             patch.dict('sys.modules',{'vllm':types.SimpleNamespace(LLM=LLM,SamplingParams=lambda **kw:kw)}):
            try: result = ns['worker']('synthetic-execution',{'synthetic':True},'0')
            except Exception as exc: result = exc
        return result, store, counter, out

    def test_actual_body_completes_exact_roster_after_process_exit(self):
        result,store,counter,out = self.run_body()
        if isinstance(result,Exception): raise result
        self.assertEqual(result['status'],'completed')
        self.assertEqual(counter['generated'],10080)
        self.assertEqual(counter['llm'],1)
        self.assertEqual(len(list((out/'screen_acks').glob('*.json'))),40)
        self.assertEqual(result['result']['new_training_updates'],0)
        self.assertIsNone(result['result']['selected_cue'])

    def test_actual_body_rejects_failed_proposal_before_llm(self):
        result,store,counter,out = self.run_body(proc_exit=1)
        self.assertIsInstance(result,RuntimeError)
        self.assertEqual(counter['llm'],0)
        self.assertEqual(counter['generated'],0)
        self.assertEqual(store.get('cue/search_r1/terminal')['status'],'failed')

    def test_actual_body_replay_rejected_before_process(self):
        result,store,counter,out = self.run_body(already_claimed=True)
        self.assertIsInstance(result,RuntimeError)
        self.assertEqual(counter['process_start'],0)
        self.assertFalse(out.exists())


if __name__ == '__main__': unittest.main()
