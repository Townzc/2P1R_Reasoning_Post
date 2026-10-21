"""New synthetic C1 body/pack checks only; no original corpus/model admission."""
import copy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.p011 import c1_execution as c, c1_nll
from scripts import prepare_p011_c1_inputs as inputs
from experiments.sft_allocation_midpoint.common import digest, dump, read, sha


def spec():
    # Entirely synthetic values, never an actual runtime/timing candidate.
    return {'limits':{'worker_seconds':900,'platform_seconds':960,'startup_seconds':600,
        'closeout_seconds':600,'full_result_window_seconds':2160,
        'future_allowance_seconds':300,'measurement_exceptions':0,
        'usd_per_second':.00125,'reserved_usd':'1.95'},
        'model':{**c1_nll.MODEL,'remote_path':'/evidence/mp-engineering-20261012-r1/assets/model',
                 'files':{'synthetic':{'sha256':'0'*64,'bytes':1}}},
        'forward':{'dtype':'bfloat16','loss_dtype':'float32','attention':'sdpa',
            'model_batch_size':1,'journal_chunk_size':32,'use_cache':False,
            'training':False,'adapter':False,'original_EOS':151643},
        'timing':{'complete_chunk_seconds':[.01,.02],'measurement_basis_accepted':True,
            'source_evidence_files':{'synthetic_only':'0'*64},
            'basis_kind':'actual_C1_complete_chunk',
            'target_scope':'C1_sequential32_original_token_forwards_including_FP32_loss'}}


class Store(dict):
    def put(self,key,value,skip_if_exists):
        assert skip_if_exists is True
        if key in self:return False
        self[key]=copy.deepcopy(value);return True


def roster(n=64):
    tasks={};members=[]
    for i in range(n):
        enc={'input_ids':[10,i+100,151643],'labels':[-100,i+100,151643],
             'n_processed':3,'n_prompt':1,'n_supervised':2}
        task={'input_ids':enc['input_ids'],'labels':enc['labels'],**c1_nll.checked_sequence(enc)}
        tasks[task['sequence_sha256']]=task
        members.append({'sequence_sha256':task['sequence_sha256'],'unverified_fallback':bool(i%3==0)})
    return tasks,{'synthetic':members}


def forward(model,task):
    return {'sequence_sha256':task['sequence_sha256'],'target_positions':[1,2],
            'supervised_tokens':2,'token_nll':[.25,.5],'nll_sum':.75,'mean_nll':.375}


def loader(s,out,deadline):
    dump(out/'MODEL_LOADED.json',{'synthetic_only':True});return object()


class C1ExecutionDraftTests(unittest.TestCase):
    def test_cutoff_and_full_window(self):
        self.assertEqual(datetime.fromtimestamp(c.CUTOFF_EPOCH,timezone.utc).isoformat(),
                         '2026-10-22T05:00:00+00:00')
        s=spec();c.validate_spec(s);s['limits']['full_result_window_seconds']-=1
        with self.assertRaises(ValueError):c.validate_spec(s)

    def test_numeric_malformed_values_fail(self):
        for name,value in [('worker_seconds',True),('future_allowance_seconds',float('nan')),
                           ('future_allowance_seconds',True),('measurement_exceptions',False)]:
            s=spec();s['limits'][name]=value
            with self.assertRaises(ValueError):c.validate_spec(s)

    def test_prior_proxy_needs_explicit_scope(self):
        s=spec();s['timing']['basis_kind']='independently_accepted_prior_measurement_proxy'
        with self.assertRaises(ValueError):c.validate_spec(s)
        s['timing']['uncalibrated_proxy_scope_accepted']=True;c.validate_spec(s)
        s['timing']['complete_chunk_seconds']=[]
        with self.assertRaises(ValueError):c.validate_spec(s)

    def test_allmax_and_remaining_budget_guard(self):
        s=spec();f=c.forecast(s,10,2,[.5,.25],0)
        self.assertEqual(f['total_scenario_seconds'],1.2*(10+2*.5+300))
        self.assertEqual(f['actual_observation_count'],2)
        s['limits']['reserved_usd']='1.95'
        # Reservation fits at prior10.04, but forecast exceeds80% of remaining1.96.
        with self.assertRaises(ValueError):c.forecast(s,400,0,[],10.04)

    def test_whole_billed_reservation_required(self):
        s=spec();s['limits']['reserved_usd']='1.94'
        with self.assertRaises(ValueError):c.validate_spec(s)

    def test_complete_body_and_readonly_replay(self):
        tasks,members=roster();store=Store({'c1/claim':{'id':'synthetic'}});s=spec()
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'run';start=time.time()
            with patch.object(c1_nll,'forward_one',side_effect=forward) as fn:
                result=c.run_body(s,tasks,members,out,{'synthetic':True},store,'c1',
                    store['c1/claim'],lambda:None,start,start+900,0,loader)
                self.assertEqual(fn.call_count,64)
            self.assertEqual(result['unique_sequences'],64)
            with patch.object(c1_nll,'forward_one',side_effect=AssertionError('no reforward')), \
                 patch.object(c1_nll,'descriptive_summary',side_effect=AssertionError('no reaggregate')):
                proof=c.check_body(s,out,tasks,members,{'synthetic':True},store,'c1',store['c1/claim'])
            self.assertTrue(proof['complete']);self.assertFalse(proof['statistics_recomputed'])
            store['c1/chunk_done/00001']['count']=31
            with self.assertRaises(ValueError):
                c.check_body(s,out,tasks,members,{'synthetic':True},store,'c1',store['c1/claim'])

    def test_failure_retained_no_summary_or_second_invocation(self):
        tasks,members=roster(2);store=Store({'c1/claim':{'id':'synthetic'}})
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'run';start=time.time()
            with patch.object(c1_nll,'forward_one',side_effect=RuntimeError('synthetic forward failure')) as fn:
                with self.assertRaises(RuntimeError):
                    c.run_body(spec(),tasks,members,out,{'synthetic':True},store,'c1',
                        store['c1/claim'],lambda:None,start,start+900,0,loader)
                self.assertEqual(fn.call_count,1)
                with self.assertRaises(FileExistsError):
                    c.run_body(spec(),tasks,members,out,{'synthetic':True},store,'c1',
                        store['c1/claim'],lambda:None,start,start+900,0,loader)
                self.assertEqual(fn.call_count,1)
            self.assertTrue((out/'FAILED.json').exists())
            self.assertFalse((out/'ALL_CONFIRMED.json').exists())
            self.assertFalse((out/'DESCRIPTIVE_SUMMARY.json').exists())

    def test_remote_chunk_fence_prevents_forward(self):
        tasks,members=roster(1);store=Store({'c1/claim':{'id':'synthetic'},'c1/chunk/00000':{}})
        with tempfile.TemporaryDirectory() as d:
            start=time.time()
            with patch.object(c1_nll,'forward_one',side_effect=AssertionError('must not forward')) as fn:
                with self.assertRaisesRegex(ValueError,'already attempted'):
                    c.run_body(spec(),tasks,members,Path(d)/'run',{'synthetic':True},store,'c1',
                        store['c1/claim'],lambda:None,start,start+900,0,loader)
                fn.assert_not_called()

    def test_changed_claim_and_cutoff_fail_before_output(self):
        tasks,members=roster(1)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'run';start=time.time()
            with self.assertRaises(ValueError):
                c.run_body(spec(),tasks,members,out,{'synthetic':True},{},'c1',{},lambda:None,
                           start,start+900,0,loader)
            self.assertFalse(out.exists())
            start=c.CUTOFF_EPOCH-1000
            with self.assertRaises(ValueError):
                c.run_body(spec(),tasks,members,out,{'synthetic':True},{'c1/claim':{}},'c1',{},
                           lambda:None,start,start+900,0,loader)
            self.assertFalse(out.exists())

    def test_input_pack_exact18_and_no_encoding(self):
        tasks,members=roster(2);expected=inputs.inventory_metadata(tasks,members)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);manifest={}
            for t in ('t15','t7','t72'):
                for n in (400,3200):
                    folder=root/f'{t}_n{n}';folder.mkdir()
                    for kind in ('config','rows','encoded'):
                        path=folder/(kind+'.json');dump(path,{'synthetic':True})
                        manifest[path.relative_to(root).as_posix()]={'sha256':sha(path),'bytes':path.stat().st_size}
            with patch.object(c1_nll,'inventory',return_value=(tasks,members)) as fn:
                self.assertEqual(inputs.load_pack(root,manifest,expected),(tasks,members))
                self.assertEqual(len(fn.call_args.args[0]),6)
                bad=copy.deepcopy(expected);bad['tasks_sha256']='0'*64
                with self.assertRaises(ValueError):inputs.load_pack(root,manifest,bad)
            manifest.pop(next(iter(manifest)))
            with self.assertRaises(ValueError):inputs.load_pack(root,manifest,expected)

    def test_input_preparation_missing_review_does_not_touch_original(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dump(root/'binding.json',{});dump(root/'code.json',{'source_files':{}})
            dump(root/'review.json',{'scope':'wrong'})
            with patch.object(inputs,'OUT',root/'output'),patch.object(inputs,'FENCE',root/'fence'), \
                 patch.object(inputs.c1_evidence,'load_original_groups',side_effect=AssertionError('no original read')) as fn:
                with self.assertRaises(ValueError):
                    inputs.prepare(root/'binding.json',root/'code.json',root/'review.json')
                fn.assert_not_called();self.assertFalse((root/'fence').exists())

    def test_loader_rejects_cpu_before_any_weight_read(self):
        import torch
        from transformers import AutoModelForCausalLM
        versions={'torch':'2.8.0','transformers':'4.56.2','numpy':'2.2.6','safetensors':'0.6.2'}
        with tempfile.TemporaryDirectory() as d, \
             patch.dict(c.os.environ,{'CUBLAS_WORKSPACE_CONFIG':':4096:8'}), \
             patch('importlib.metadata.version',side_effect=lambda name:versions[name]), \
             patch.object(torch.cuda,'is_available',return_value=False), \
             patch.object(c,'verify',side_effect=AssertionError('no weight read')) as verify, \
             patch.object(AutoModelForCausalLM,'from_pretrained',side_effect=AssertionError('no model load')) as load:
            with self.assertRaisesRegex(ValueError,'Actual CUDA12.8'):
                c.load_base(spec(),Path(d),time.time()+60)
            verify.assert_not_called();load.assert_not_called()


if __name__=='__main__':unittest.main()
