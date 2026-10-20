"""New worker integration checks; synthetic inputs and fake cloud/model only."""
import copy
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest

from experiments.p011 import long_execution as x
from experiments.p011.long_numeric import forecast
from experiments.sft_allocation_midpoint.common import dump,read,digest,manifest


class Store(dict):
    def put(self,key,value,skip_if_exists):
        assert skip_if_exists
        if key in self:return False
        self[key]=copy.deepcopy(value)
        return True


class LongExecutionChecks(unittest.TestCase):
    def journal(self,tmp,store=None):
        rows=[{'n_supervised':2,'n_processed':4}]
        plan={'updates':[[0],[0],[0]]}
        return x.WholeAnswerJournal(tmp,'r',Store() if store is None else store,
            lambda:None,lambda:None,rows,plan,[1.,.5,.1],lambda n,t:{'left':n,'times':t})

    def finish_updates(self,j):
        for i,intent in enumerate(j.records):
            name=f'update_{i+1:05d}'
            j.begin(name,intent)
            j.end(name,{**intent,'cumulative_supervised':2*(i+1),'cumulative_processed':4*(i+1),
                        'loss':.3,'gradient_norm':.7,'seconds':.01})

    def test_arbitrary_U_and_terminal_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=self.journal(tmp);self.finish_updates(j)
            for name in ('terminal_state','terminal_model_export'):
                j.begin(name,{});j.end(name,{'saved':True})
            j.complete()
            self.assertEqual((j.cursor,j.total_supervised,j.total_processed),(3,6,12))

    def test_partial_unit_remains_reserved_and_new_object_cannot_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store();j=self.journal(tmp,store);j.begin('update_00001',j.records[0])
            with self.assertRaises(ValueError):j.end('update_00001',{})
            self.assertIn('r/unit/update_00001',store)
            with self.assertRaises(RuntimeError):j.begin('update_00001',j.records[0])
            other=self.journal(Path(tmp)/'other',store)
            with self.assertRaisesRegex(RuntimeError,'marker'):other.begin('update_00001',other.records[0])

    def test_early_export_never_gets_remote_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            j=self.journal(tmp)
            with self.assertRaises(ValueError):j.begin('terminal_model_export',{})
            self.assertFalse(j.store)

    @staticmethod
    def endpoint():
        rows=[]
        for b,n in x.BENCHMARK_COUNTS.items():
            for i in range(n):
                for mode,seeds in ([('sample',range(4)),('greedy',[0])] if b=='math500' else [('sample',range(8))]):
                    for seed in seeds:
                        pid=f'{b}:{i:04d}'
                        rows.append(dict(id=f'{pid}:{mode}:{seed}',problem_id=pid,benchmark=b,
                            source_row=i,mode=mode,seed=seed,prompt_token_ids=[10,11],
                            prompt_text_sha256='a'*64,required_context=16386,request_sha256='b'*64))
        return rows

    def test_full_3300_roster_rejects_missing_row_gold_and_prompt_disagreement(self):
        rows=self.endpoint();x.validate_endpoint(rows,16386)
        self.assertEqual(len(rows),3300)
        for mutation in ('missing','gold','prompt'):
            copyrows=copy.deepcopy(rows)
            if mutation=='missing':copyrows.pop()
            elif mutation=='gold':copyrows[0]['gold']='2'
            else:copyrows[1]['prompt_token_ids']=[10,12]
            with self.assertRaises(ValueError):x.validate_endpoint(copyrows,16386)

    def test_raw_shape_failure_is_saved_before_error_and_not_retried(self):
        rows=self.endpoint()[:2];store=Store();calls=[]
        class BadLLM:
            def generate(self,prompts,params,use_tqdm):
                calls.append(True)
                return [NS(prompt_token_ids=prompts[0]['prompt_token_ids'],outputs=[])]
        with tempfile.TemporaryDirectory() as tmp:
            args=(BadLLM(),lambda **kw:kw,rows,[151645],tmp,'r',store,lambda:None,
                  lambda:None,lambda n,t:{'left':n})
            with self.assertRaisesRegex(ValueError,'Partial'):x.evaluate(*args)
            self.assertEqual(read(Path(tmp)/'raw/eval_0000.json')[0]['answers'],[])
            self.assertIn('r/unit/eval_0000',store)
            self.assertNotIn('r/done/eval_0000',store)
            self.assertEqual(len(calls),1)

    def test_complete_raw_batches_preserve_each_distinct_seed(self):
        rows=self.endpoint()[:35];seen=[]
        class LLM:
            def generate(self,prompts,params,use_tqdm):
                seen.extend(p['seed'] for p in params)
                return [NS(prompt_token_ids=p['prompt_token_ids'],outputs=[NS(
                    token_ids=[20,151645],text='synthetic',finish_reason='stop',stop_reason=151645)]) for p in prompts]
        with tempfile.TemporaryDirectory() as tmp:
            store=Store()
            times=x.evaluate(LLM(),lambda **kw:kw,rows,[151645],tmp,'r',store,
                lambda:None,lambda:None,lambda n,t:{'left':n})
            self.assertEqual(len(times),2)
            self.assertEqual(seen,[r['seed'] for r in rows])
            self.assertEqual(read(Path(tmp)/'completed/eval_0001.json')['count'],3)

    @staticmethod
    def policy():
        return dict(category='A',worker_start_epoch=1000.,worker_hard_seconds=1800,
            result_deadline_epoch=10000.,full_result_seconds=2500,measurement_exceptions=0,
            projection_multiplier=1.2,uncalibrated_future_seconds=300,
            training_unit_seconds=[1.,2.],endpoint_batch_seconds=[1.,3.],hourly_rate_usd='4.5',
            startup_allowance_seconds=600,platform_timeout_seconds=1860,reserved_usd='3.08',
            prior_reserved_usd='0')

    def test_all_history_plus_actual_max_cost_and_window(self):
        f=forecast(self.policy(),3,4,[9],[5],1005.)
        self.assertEqual(f['projected_total_worker_seconds'],1.2*(5+3*9+4*5+300))
        self.assertEqual(f['training_unit_max_seconds'],9)
        self.assertEqual(f['reserved_usd'],'3.08')

    def test_no_measurement_exemption_and_independent_80percent_gate(self):
        for key,val in [('training_unit_seconds',[]),('measurement_exceptions',1),
                        ('prior_reserved_usd','112'),('worker_hard_seconds',350),
                        ('result_deadline_epoch',3400)]:
            p=self.policy();p[key]=val
            with self.assertRaises(ValueError):forecast(p,3,4,[],[],1005.)

    def test_join_exit_and_export_binding_before_returning_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);model=root/'model_for_vllm';model.mkdir();(model/'mock.bin').write_bytes(b'x')
            export=dict(relative_path='model_for_vllm',files=manifest(model),final_state={'step':3},
                        optimizer_updates_after_terminal_state=0)
            dump(root/'MODEL_EXPORT.json',export)
            result={'model_export_sha256':digest(export),'terminal_state':{'step':3}}
            events=[]
            class Pipe:
                def close(self):pass
                def poll(self,t):return True
                def recv(self):return ('complete',result,[.1,.2,.3])
            class Process:
                pid=99;exitcode=0
                def start(self):events.append('start')
                def join(self,timeout):events.append('joined')
                def is_alive(self):return False
            ctx=NS(Pipe=lambda:(Pipe(),Pipe()),Process=lambda **kw:Process())
            output=x.joined_training(root,root,{},'S-L15',{},'r',{},time.time()+100,{},
                lambda:events.append('commit'),lambda:events.append('reload'),context=ctx)
            self.assertEqual(output[2],str(model))
            self.assertLess(events.index('joined'),events.index('reload'))
            self.assertTrue(read(root/'TRAINING_EXIT.json')['joined_before_vllm'])

    def test_nonzero_child_exit_rejected_without_export_or_eval(self):
        with tempfile.TemporaryDirectory() as tmp:
            class Pipe:
                def close(self):pass
                def poll(self,t):return True
                def recv(self):return ('complete',{},[])
            class Process:
                pid=99;exitcode=1
                def start(self):pass
                def join(self,timeout):pass
                def is_alive(self):return False
            ctx=NS(Pipe=lambda:(Pipe(),Pipe()),Process=lambda **kw:Process())
            with self.assertRaises(RuntimeError):
                x.joined_training(tmp,tmp,{},'S-L15',{},'r',{},time.time()+100,{},
                    lambda:None,lambda:None,context=ctx)
            self.assertFalse((Path(tmp)/'TRAINING_EXIT.json').exists())


if __name__=='__main__':unittest.main()
