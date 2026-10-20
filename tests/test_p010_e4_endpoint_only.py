"""New repair-contract and actual worker-body tests; no cloud/model/scoring."""
import ast
from copy import deepcopy
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from experiments.p010.common import read, dump, sha, digest, manifest
from experiments.p010.e4_endpoint_contract import endpoint_rows, forecast, sampling, validate_parent


def fixture_rows():
    return dict(n=1319, max_context=2048, max_new_tokens=512, eos_token_id=100257,
        prompts=[dict(problem_id='test/'+str(i), input_ids=[10,20+i]) for i in range(1319)])


class Contract(unittest.TestCase):
    def test_actual_original_wrapper_unwrapped_without_mutation(self):
        path = Path('.local/p010_20261019/r1/inputs/olmo_gsm_zero.json')
        original = read(path); before = digest(original); rows = endpoint_rows(original)
        self.assertIs(rows, original['prompts']); self.assertEqual(digest(original),before)
        self.assertEqual(len(rows),1319); self.assertEqual(sampling()['max_tokens'],512)
        self.assertEqual(sampling()['stop_token_ids'],[100257])

    def test_wrapper_rejects_partial_duplicate_long_or_changed_endpoint(self):
        values=[]
        a=fixture_rows();a['prompts'].pop();values.append(a)
        a=fixture_rows();a['prompts'][1]=a['prompts'][0];values.append(a)
        a=fixture_rows();a['prompts'][0]['input_ids']=[1]*1537;values.append(a)
        a=fixture_rows();a['max_new_tokens']=1024;values.append(a)
        for value in values:
            with self.assertRaises(ValueError):endpoint_rows(value)

    def test_forecast_no_bootstrap_exemption_all_times_and_budget(self):
        value=forecast(0,0,[],'26.20');self.assertLess(value['total_seconds'],1170)
        self.assertEqual(value['budget']['new_reserved_usd'],'2.52')
        self.assertEqual(forecast(100,2,[21,40],'26.20')['maximum_seconds'],40)
        with self.assertRaises(TimeoutError):forecast(350,0,[],'26.20')
        with self.assertRaises(ValueError):forecast(0,0,[],'149')
        with self.assertRaises(ValueError):forecast(0,1,[],'26.20')

    def worker(self, folder, fail=False):
        import experiments.p010.runtime_support as support
        import experiments.learning_regime_p009.high_throughput_v1 as engine
        run='e4_s17_n400';old=folder/'evidence/p010-20261019/e4'/run;old.mkdir(parents=True)
        (old/'checkpoint_1024').mkdir();(old/'checkpoint_1024/state.pt').write_bytes(b'fake-state-not-loaded')
        (old/'merged').mkdir();dump(old/'merged/config.json',dict(synthetic=True))
        merged=manifest(old/'merged');claim=dict(run=run,execution='original');terminal=dict(status='failed',error='slice(0, 256, None)')
        identity=dict(run_id=run,synthetic=True)
        dump(old/'INTENT.json',dict(identity=identity));dump(old/'MERGE_PROOF.json',dict(merged_files=merged));dump(old/'TRAINING_EXIT.json',dict(joined_before_vllm=True))
        proof=dict(passed=True,run=run,updates_verified=1024,targets_verified=2097148,
            full_state_loaded_once=True,no_endpoint_intent_or_raw=True,original_run_stays_failed=True,
            new_training=0,new_generations=0,original_claim=claim,original_failed_terminal=terminal,
            state_sha256=sha(old/'checkpoint_1024/state.pt'),original_identity=identity,merged_files=merged)
        endpoint=folder/'evidence/p010-20261019/inputs/olmo_gsm_zero.json';dump(endpoint,fixture_rows())
        spec=dict(source_files={},parents={run:dict(proof_canonical_sha256=digest(proof))},endpoint_file_sha256=sha(endpoint))
        spec_path=folder/'workspace/spec.json';dump(spec_path,spec)
        class Store:
            def __init__(self):self.data={'e4/'+run+'/claim':claim,'e4/'+run+'/terminal':terminal}
            def get(self,key):return self.data.get(key)
            def put(self,key,value,skip_if_exists=False):
                if skip_if_exists and key in self.data:return False
                self.data[key]=value;return True
        store=Store();calls=[];loads=[]
        class LLM:
            def __init__(self,**kwargs):
                loads.append(kwargs);self.llm_engine=types.SimpleNamespace(vllm_config=None)
            def generate(self,prompts,params,use_tqdm):
                calls.append(deepcopy(prompts))
                if fail:raise RuntimeError('synthetic generation failure')
                return [types.SimpleNamespace(prompt_token_ids=x['prompt_token_ids'],outputs=[types.SimpleNamespace(token_ids=[1,100257],text='fake',finish_reason='stop',stop_reason=100257)]) for x in prompts]
        def path(value):
            value=str(value)
            if value.startswith('/evidence/') or value.startswith('/workspace/'):
                return folder/value.lstrip('/')
            return Path(value)
        tree=ast.parse(Path('experiments/p010/modal_e4_endpoint_only.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='worker');fn.decorator_list=[]
        ns=dict(Path=path,SPEC='spec.json',read=lambda value:read(path(value)),volume=types.SimpleNamespace(reload=lambda:None,commit=lambda:None),modal=types.SimpleNamespace(Dict=types.SimpleNamespace(from_name=lambda *a,**k:store)))
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual endpoint-only worker body>','exec'),ns)
        fake=types.SimpleNamespace(LLM=LLM,SamplingParams=lambda **kwargs:kwargs)
        with patch.dict('sys.modules',vllm=fake),patch.object(support,'source_check',return_value=None),patch.object(support,'hard_timer',return_value=types.SimpleNamespace(cancel=lambda:None)),patch.object(engine,'actual_engine',return_value={'synthetic':True}):
            if fail:
                with self.assertRaisesRegex(RuntimeError,'synthetic generation'):ns['worker'](run,'new',proof,{},'26.20')
            else:
                result=ns['worker'](run,'new',proof,{},'26.20')
                self.assertEqual(result['result']['raw_endpoint_count'],1319)
                self.assertEqual(result['result']['new_training_updates'],0)
                self.assertEqual([p['prompt_token_ids'] for batch in calls for p in batch],[x['input_ids'] for x in fixture_rows()['prompts']])
                self.assertEqual(len(calls),6)
            before=len(calls)
            with self.assertRaisesRegex(RuntimeError,'already attempted'):ns['worker'](run,'new',proof,{},'26.20')
            self.assertEqual(len(calls),before);self.assertEqual(len(loads),1)
            self.assertEqual(store.get('e4/'+run+'/terminal'),terminal)
            self.assertIsNone(store.get('e4/'+run+'/eval/0000'))
        return proof,claim,terminal

    def test_actual_worker_all_six_batches_and_permanent_replay_block(self):
        with tempfile.TemporaryDirectory() as temp:self.worker(Path(temp))

    def test_actual_worker_failure_preserves_intent_and_no_retry(self):
        with tempfile.TemporaryDirectory() as temp:self.worker(Path(temp),True)

    def test_parent_partial_or_original_endpoint_rejects(self):
        proof=dict(passed=True,run='e4_s17_n400',updates_verified=1024,targets_verified=2097148,
            full_state_loaded_once=True,no_endpoint_intent_or_raw=True,original_run_stays_failed=True,
            new_training=0,new_generations=0,original_claim={},original_failed_terminal={'status':'failed'})
        validate_parent(proof,'e4_s17_n400',{}, {'status':'failed'},[None]*12,[])
        for field,value in [('updates_verified',896),('no_endpoint_intent_or_raw',False)]:
            p=deepcopy(proof);p[field]=value
            with self.assertRaises(ValueError):validate_parent(p,'e4_s17_n400',{}, {'status':'failed'},[None]*12,[])
        with self.assertRaises(ValueError):validate_parent(proof,'e4_s17_n400',{}, {'status':'failed'},[{}]+[None]*11,[])
        with self.assertRaises(ValueError):validate_parent(proof,'e4_s17_n400',{}, {'status':'failed'},[None]*12,['old-raw'])


if __name__=='__main__':unittest.main()
