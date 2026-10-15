"""Execute the new actual Modal worker body using only in-memory dependencies."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from tests.test_p009_stage1_nc_runtime import NCRuntime
from experiments.learning_regime_p009.stage1_nc_binding import marker,dispatch_key,logical_key,CAMPAIGN


class NCEntryBody(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        NCRuntime.setUpClass()
        tree=ast.parse(Path('experiments/learning_regime_p009/modal_stage1_nc.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='work')
        node.decorator_list=[];cls.code=compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'actual_NC_worker_body','exec')

    def exercise(self,corrupt=False):
        spec=deepcopy(NCRuntime.spec);plan=deepcopy(NCRuntime.plan);release=deepcopy(NCRuntime.release)
        release.update(dispatch_app_id='ap-synthetic-memory-only',execution_commit='a'*40)
        run='nc_s17_n400';files={};directories=set();model=Mock(return_value=dict(updates=1024,targets=2097148,new_outputs=1319));volume=Mock()
        class Store(dict):
            def put(self,k,v,skip_if_exists=False):
                if skip_if_exists and k in self:return False
                self[k]=deepcopy(v);return True
        store=Store(spec['required_records'])
        for k in (dispatch_key(run),logical_key(run)):store[k]=marker(spec,run,release)
        class FakePath:
            def __init__(self,p):self.p=str(p)
            def __str__(self):return self.p
            def __truediv__(self,n):return FakePath(self.p+'/'+str(n))
            def mkdir(self,parents=False,exist_ok=False):
                if self.p in directories and not exist_ok:raise FileExistsError(self.p)
                directories.add(self.p)
            def exists(self):return self.p in directories
        def dump(p,v):
            if str(p) in files:raise FileExistsError(str(p))
            files[str(p)]=deepcopy(v)
        def source_sha(p):return '0'*64 if corrupt else spec['source_files'][str(p).removeprefix('/workspace/')]
        modal=SimpleNamespace(Dict=SimpleNamespace(from_name=lambda *a,**k:store))
        namespace=dict(Path=FakePath,modal=modal,volume=volume,SPEC='synthetic-exact-spec')
        exec(self.code,namespace)
        timer=Mock()
        with patch('threading.Timer',return_value=timer),patch('experiments.sft_allocation_midpoint.common.read',return_value=spec),patch('experiments.sft_allocation_midpoint.common.dump',side_effect=dump),patch('experiments.sft_allocation_midpoint.common.sha',side_effect=source_sha),patch('experiments.sft_allocation_midpoint.common.manifest',return_value={'synthetic_result.json':{'bytes':1,'sha256':'1'*64}}),patch('experiments.sft_allocation_p008.evidence_bundle.pack'),patch('experiments.learning_regime_p009.stage1_nc_runtime.execute',model):
            if corrupt:
                with self.assertRaises(ValueError):namespace['work'](plan,run,release)
                self.assertNotIn('midpoint/'+CAMPAIGN+'/claim/'+run,store);model.assert_not_called()
            else:
                result=namespace['work'](plan,run,release)
                self.assertEqual(result['receipt']['status'],'completed');model.assert_called_once()
                self.assertAlmostEqual(model.call_args.args[-1]-model.call_args.args[-2],4500)
                self.assertEqual(store['midpoint/'+CAMPAIGN+'/claim/'+run]['reserved_cents'],655)
            timer.start.assert_called_once();timer.cancel.assert_called_once()

    def test_actual_nested_schema_successful_single_worker_body(self):self.exercise()
    def test_source_failure_cancels_timer_before_claim_or_model(self):self.exercise(corrupt=True)


if __name__=='__main__':unittest.main()
