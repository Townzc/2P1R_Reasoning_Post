"""New B wiring fixtures only; no original data/model/old test invocation."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from experiments.p010.common import dump, read
from experiments.p011 import b_numeric as n, b_student_execution as x
from experiments.p011 import b_student_evidence as ev
from experiments.p011.b_student_process import CompleteBlockJournal


def policy(kind='student'):
    return dict(kind=kind, category='B', measurement_exceptions=0,
        projection_multiplier=1.2, uncalibrated_future_seconds=600,
        worker_start_epoch=10000., worker_seconds=3000, full_result_seconds=10000,
        result_cutoff_epoch=50000., training_cycle_seconds=[1.] if kind=='student' else [],
        batch_cycle_seconds=[1.], hourly_rate_usd='.01', startup_seconds=600,
        platform_seconds=3060, reserved_usd='.02', prior_B_reserved_usd='0')


def endpoint():
    return [dict(candidate_id=f'c{i}', problem_id=f'q{i}', input_ids=[1,2],
                 source_row_sha256='a'*64) for i in range(500)]


class Store(dict):
    def __init__(self, tick):
        super().__init__(); self.tick=tick
    def put(self, key, value, skip_if_exists):
        self.tick[0]+=1
        if key in self:return False
        self[key]=value;return True


class NewBStudent(unittest.TestCase):
    def test_B_scope_rejects_C1_exception_and_insufficient_reservation(self):
        p=policy();self.assertEqual(n.forecast(p,64,10,[],[],10000.)['measurement_exceptions'],0)
        for k,v in [('measurement_exceptions',1),('category','C'),('reserved_usd','0')]:
            bad=copy.deepcopy(p);bad[k]=v
            with self.assertRaises(ValueError):n.forecast(bad,64,10,[],[],10000.)

    def test_all_cycle_maximum_and_original_deadline_are_retained(self):
        p=policy();a=n.forecast(p,64,10,[3.,2.],[4.],10001.)
        self.assertEqual(a['training_cycle_max'],3.);self.assertEqual(a['batch_cycle_max'],4.)
        p['result_cutoff_epoch']=19999.
        with self.assertRaisesRegex(ValueError,'window'):n.forecast(p,64,10,[],[],10000.)

    def test_missing_timing_or_80percent_forecast_blocks_before_work(self):
        p=policy();p['batch_cycle_seconds']=[]
        with self.assertRaisesRegex(ValueError,'timing'):n.forecast(p,64,10,[],[],10000.)
        p=policy();p['hourly_rate_usd']='40';p['reserved_usd']='20'
        with self.assertRaisesRegex(ValueError,'reservation'):n.forecast(p,64,10,[],[],10000.)

    def test_generation_has_no_training_or_C1_measurement_transfer(self):
        p=policy('generation');self.assertEqual(n.forecast(p,0,25,[],[],10000.)['kind'],'generation')
        with self.assertRaises(ValueError):n.forecast(p,1,25,[],[],10000.)

    def test_block_cycle_includes_forecast_commit_and_remote_block_fences(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            tick=[10000.];store=Store(tick)
            def commit():tick[0]+=2
            j=CompleteBlockJournal(Path(d),'b/student/B1',store,commit,lambda:None,
                deadline=lambda:None,expected_updates=1024,policy=policy(),clock=lambda:tick[0])
            j.configure_training([{'n_supervised':1,'n_processed':2}],[[0]]*1024,[.001]*1024)
            for i in range(16):
                record=j.records[i];j.begin(f'update_{i+1:04d}',record);tick[0]+=.5
                j.end(f'update_{i+1:04d}',dict(record,cumulative_targets=i+1,cumulative_processed=2*(i+1)))
            self.assertEqual(j.times,[14.]);self.assertIsNone(j.tick)
            self.assertIn('b/student/B1/unit/training_block_0001_0016',store)
            with self.assertRaises(ValueError):j.begin('update_0001',j.records[0])

    def test_endpoint_rejects_dict_or_gold_bearing_rows_before_generation(self):
        with self.assertRaises(ValueError):x.endpoint_rows({'rows':endpoint()})
        rows=endpoint();rows[0]['gold']='hidden'
        with self.assertRaisesRegex(ValueError,'gold-free'):x.endpoint_rows(rows)

    def endpoint_fixture(self,d,bad=False):
        tick=[10000.];store=Store(tick);claim={'fixture':True};store['b/student/B1/claim']=claim
        def commit():tick[0]+=2
        calls=[]
        class LLM:
            def generate(self, prompts, params, use_tqdm):
                calls.append(len(prompts));tick[0]+=1
                values=[NS(prompt_token_ids=r['prompt_token_ids'],outputs=[NS(token_ids=[151643],
                    text='',finish_reason='stop',stop_reason=151643)]) for r in prompts]
                if bad:values.pop()
                return values
        args=dict(rows=endpoint(),out=Path(d),key='b/student/B1',claim=claim,policy=policy(),
            training_times=[1.]*64,store=store,commit=commit,check=lambda:None,
            llm=LLM(),constructor=lambda **kw:kw,clock=lambda:tick[0])
        return args,calls

    def test_full2500_original_endpoint_and_three_commit_cycles(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            args,calls=self.endpoint_fixture(d);times=x.evaluate(**args)
            self.assertEqual(calls,[256,244]*5);self.assertEqual(times,[9.]*10)
            f=read(Path(d)/'eval_forecasts/greedy/0256.json')
            self.assertEqual(f['batch_cycle_max'],9.)
            with self.assertRaisesRegex(ValueError,'already attempted'):x.evaluate(**args)
            self.assertEqual(len(calls),10)

    def test_partial_raw_kept_no_ack_no_replay(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            args,calls=self.endpoint_fixture(d,True)
            with self.assertRaisesRegex(ValueError,'Incomplete'):x.evaluate(**args)
            self.assertEqual(len(read(Path(d)/'raw/greedy/0000.json')),255)
            self.assertNotIn('b/student/B1/eval_done/greedy/0000',args['store'])
            with self.assertRaisesRegex(ValueError,'already attempted'):x.evaluate(**args)
            self.assertEqual(len(calls),1)

    def test_training_child_not_joined_or_nonzero_never_qualifies_for_vllm(self):
        for alive,code in [(True,None),(False,1)]:
            proc=NS(is_alive=lambda:alive,exitcode=code)
            with self.assertRaises(RuntimeError):x.require_exited(proc,('complete',{},[1.]*64))
        proc=NS(is_alive=lambda:False,exitcode=0)
        self.assertEqual(x.require_exited(proc,('complete',{'updates':1024},[1.]*64))[0]['updates'],1024)

    def test_new_readonly_endpoint_oracle_uses_complete_cycles_without_scoring(self):
        with tempfile.TemporaryDirectory(dir='.local/p011_20261020/r1') as d:
            args,calls=self.endpoint_fixture(d);times=x.evaluate(**args);root=Path(d)
            dump(root/'ENGINE.json',{'fixture':True})
            dump(root/'RESULT.json',dict(raw_endpoint_count=2500,unique_questions=500,
                evaluations=['greedy','sample0','sample1','sample2','sample3'],eval_batch_seconds=times,
                endpoint_complete_cycles_include_three_commits_and_ack=True,symbolic_scoring_performed=False))
            tok=NS(get_vocab=lambda:{'x':151643},all_special_ids=[151643])
            with patch.object(ev,'validate_observed_engine'),patch.object(ev,'decode_record',return_value=({'stop_reason':'native_eos','answer_segment':'synthetic'},[])) as decoder:
                result=ev.verify_endpoint(root,endpoint(),policy(),'B1',args['store'],
                    {'train_seconds':[1.]*64},tok,{f'q{i}':{'answer':'synthetic'} for i in range(500)},151936)
                self.assertEqual(decoder.call_count,2500);self.assertEqual(result['technical_unknown'],0)
                self.assertFalse(result['symbolic_scoring_performed'])
                record=root/'eval_acks/greedy/0000.json';wrong=read(record);wrong['count']=255;record.write_text(json.dumps(wrong))
                with self.assertRaisesRegex(ValueError,'intent/ack'):ev.verify_endpoint(root,endpoint(),policy(),'B1',args['store'],{'train_seconds':[1.]*64},tok,{f'q{i}':{'answer':'synthetic'} for i in range(500)},151936)


if __name__=='__main__':unittest.main()
