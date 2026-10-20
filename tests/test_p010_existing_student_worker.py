"""New actual sample-only worker-body checks; all models/provider are synthetic."""
import ast
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments.p010.common import dump, read, sha, manifest


class Store:
    def __init__(self): self.values = {}
    def get(self, key): return self.values.get(key)
    def put(self, key, value, skip_if_exists):
        if key in self.values: return False
        self.values[key] = value
        return True


class WorkerTests(unittest.TestCase):
    def body(self, exitcode=0, claimed=False, wrong_parent=False):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        root = Path(temp.name); run = 's1_s17_n400'
        def path(value):
            value = str(value)
            return root/value.lstrip('/') if value.startswith('/evidence/') else Path(value)
        old = path('/evidence/old'); old.mkdir(parents=True)
        checkpoint = {'sha256': 'synthetic-state'}
        dump(old/'checkpoint_1024/manifest.json', checkpoint)
        original = root/'original'; original.mkdir()
        (original/'model.safetensors').write_bytes(b'synthetic merged model')
        merge = {'merged_files': manifest(original)}; dump(old/'MERGE_PROOF.json', merge)
        endpoint = path('/evidence/p010-20261019/student_inputs/MATH_ENDPOINT.json')
        dump(endpoint, [dict(problem_id=str(i), input_ids=[21,22]) for i in range(500)])
        parent = dict(remote_path='/evidence/old', terminal_key='old/terminal',
            terminal={'status':'completed'}, merge_proof=merge,
            proof=dict(checkpoint=checkpoint, merged_files=merge['merged_files']))
        spec = dict(source_files={}, parents={run:parent}, model={'remote_path':'synthetic/base','files':{}},
            endpoint_sha256=sha(endpoint), batch_observations_seconds=[11.55])
        newstore, oldstore = Store(), Store()
        oldstore.values[parent['terminal_key']] = {'status':'failed'} if wrong_parent else parent['terminal']
        if claimed: newstore.values['existing_s1_samples/'+run+'/claim'] = {'existing':True}
        out = path('/evidence/p010-20261019/existing_s1_samples')/run
        counter = dict(process=0, joined=False, llm=0, rows=0, seeds=[])
        restored = dict(actual_merged_files=merge['merged_files'])
        class Process:
            pid = 1234
            def __init__(self, **kwargs): self.exitcode = exitcode
            def start(self):
                counter['process'] += 1
                dump(out/'restore/COMPLETED.json', restored)
                (out/'merged').mkdir(); (out/'merged/model.safetensors').write_bytes(b'synthetic merged model')
            def join(self, timeout): counter['joined'] = True
            def is_alive(self): return False
        connection = types.SimpleNamespace(poll=lambda _:True, recv=lambda:('restored', {'proof':restored}))
        other = types.SimpleNamespace(close=lambda:None)
        context = types.SimpleNamespace(Process=Process, Pipe=lambda:(connection,other))
        class LLM:
            def __init__(self, **kwargs):
                assert counter['joined'] and exitcode == 0
                counter['llm'] += 1; self.llm_engine = types.SimpleNamespace(vllm_config=None)
            def generate(self, prompts, params, use_tqdm):
                counter['rows'] += len(prompts); counter['seeds'].extend(p['seed'] for p in params)
                return [types.SimpleNamespace(prompt_token_ids=p['prompt_token_ids'], outputs=[
                    types.SimpleNamespace(token_ids=[31,151643], text='synthetic', finish_reason='stop', stop_reason=151643)]) for p in prompts]
        tree = ast.parse(Path('experiments/p010/modal_existing_student_samples.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'worker'); node.decorator_list=[]
        fake_modal = types.SimpleNamespace(Dict=types.SimpleNamespace(from_name=lambda name,**kw:
            oldstore if name == 'sft-allocation-midpoint-claims-v1' else newstore))
        ns = dict(Path=path, SPEC='synthetic.json', modal=fake_modal,
            read=lambda p: spec if str(p) == '/workspace/synthetic.json' else read(p),
            volume=types.SimpleNamespace(reload=lambda:None,commit=lambda:None))
        exec(compile(ast.Module(body=[node],type_ignores=[]), '<sample worker body>', 'exec'), ns)
        with patch('experiments.p010.runtime_support.source_check'), \
             patch('experiments.p010.runtime_support.hard_timer', return_value=types.SimpleNamespace(cancel=lambda:None)), \
             patch('experiments.p010.runtime_support.compact', return_value={'synthetic':True}), \
             patch('multiprocessing.get_context',return_value=context), \
             patch('experiments.learning_regime_p009.high_throughput_v1.actual_engine',return_value={'synthetic':True}), \
             patch.dict('sys.modules', {'vllm':types.SimpleNamespace(LLM=LLM,SamplingParams=lambda **kw:kw)}):
            try: result=ns['worker'](run,'synthetic',{},'31.24')
            except Exception as exc: result=exc
        return result, counter, newstore, oldstore, out

    def test_exact_four_passes_only_after_restore_process_exits(self):
        result,counter,store,old,out=self.body()
        if isinstance(result,Exception): raise result
        self.assertEqual(result['status'],'completed')
        self.assertEqual(counter['rows'],2000)
        self.assertEqual(counter['seeds'],sum(([seed]*500 for seed in range(4)),[]))
        self.assertEqual(counter['llm'],1)
        self.assertEqual(len(list((out/'sample_acks').glob('*.json'))),8)
        self.assertEqual(result['result']['greedy_outputs_generated'],0)
        self.assertEqual(result['result']['new_training_updates'],0)
        self.assertEqual(old.get('old/terminal'),{'status':'completed'})

    def test_failed_restore_stops_before_vllm_and_preserves_failure(self):
        result,counter,store,old,out=self.body(exitcode=1)
        self.assertIsInstance(result,RuntimeError)
        self.assertEqual(counter['llm'],0)
        self.assertEqual(counter['rows'],0)
        self.assertTrue((out/'FAILURE.json').is_file())
        self.assertEqual(store.get('existing_s1_samples/s1_s17_n400/terminal')['status'],'failed')

    def test_existing_claim_and_wrong_parent_both_block_before_restore(self):
        for options in ({'claimed':True},{'wrong_parent':True}):
            result,counter,store,old,out=self.body(**options)
            self.assertIsInstance(result,(ValueError,RuntimeError))
            self.assertEqual(counter['process'],0)
            self.assertFalse(out.exists())


if __name__=='__main__': unittest.main()
