"""New C2 oracle/adapter fixtures, without old corpus or old test execution."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import copy
import json
import unittest
from experiments.p011 import c2_generation_evidence as e,c2_generation_loader as l
from experiments.p011.c2_generation_execution import generate_window
from experiments.p011.c2_generation_window import plan_window
from experiments.sft_allocation_midpoint.common import read,digest


def saved(pid,a,good=True):
    return {'candidate_id':f'{pid}::attempt{a:02d}','problem_id':pid,'attempt':a,
        'answer_text':'1','gold_supported':True,'stop':{'stop_reason':'native_eos'},
        'score':{'score':{'box_extracted':True,'parsed':True,'correct':good}},'usable':good}


class Store(dict):
    def put(self,k,v,skip_if_exists):
        if k in self:return False
        self[k]=v;return True


class NewC2(unittest.TestCase):
    def make(self,root):
        ids=[f'q{i:03d}' for i in range(66)]
        old72={f'{p}::attempt01':saved(p,1) for p in ids};old15={}
        prompts={p:[9,10] for p in ids};plan=plan_window(ids,old72,old15,prompts,set(),66)
        tick=[0.];claim={'synthetic':'new-oracle'};store=Store({'c2/claim':claim})
        def commit():tick[0]+=.5
        class LLM:
            def generate(self,requests,params,use_tqdm):
                tick[0]+=2
                return [NS(prompt_token_ids=x['prompt_token_ids'],outputs=[NS(token_ids=[11,151645],
                    text='1',finish_reason='stop',stop_reason=151645)]) for x in requests]
        def transport(x):return {'stop':{'stop_reason':'native_eos','answer_segment':'1'},
            'answer_text':'1','transport':{'synthetic':True},'raw_record_sha256':digest(x)}
        forecast=lambda left,cycles:{'left':left,'cycles':cycles}
        out=Path(root)/'output'
        generate_window(plan,out,'c2',claim,store,commit,LLM(),lambda **x:x,transport,forecast,lambda:None,clock=lambda:tick[0])
        kwargs=dict(plan=plan,out=out,key='c2',claim=claim,records=store,
            verify_transport=transport,replay_forecast=forecast)
        return kwargs,ids,old72,old15,prompts

    def test_complete264_tail8_original_cycles_and_no_scoring(self):
        with TemporaryDirectory() as r:
            k,*_=self.make(r);proof=e.check_body(**k)
            self.assertEqual((proof['verified_new_outputs'],proof['verified_batches']),(264,2))
            self.assertEqual(proof['new_symbolic_comparisons'],0)
            self.assertEqual(read(k['out']/'batches/001/ACK.json')['count'],8)

    def test_missing_tail_ack_cannot_mean_complete(self):
        with TemporaryDirectory() as r:
            k,*_=self.make(r);del k['records']['c2/batch_done/001']
            with self.assertRaisesRegex(ValueError,'acknowledgment'):e.check_body(**k)

    def test_foreign_raw_identity_rejected_even_if_other_evidence_matches(self):
        with TemporaryDirectory() as r:
            k,*_=self.make(r);p=k['out']/'batches/001/RAW.json';raw=read(p);raw[0]['problem_id']='foreign'
            p.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError,'Foreign'):e.check_body(**k)

    def test_body_only_or_nonfinite_timing_not_wholecycle(self):
        with TemporaryDirectory() as r:
            k,*_=self.make(r);p=k['out']/'COMPLETED.json';v=read(p);v['cycles'][0]['seconds']=float('nan');p.write_text(json.dumps(v))
            with self.assertRaisesRegex(ValueError,'duration'):e.check_body(**k)

    def test_forecast_history_must_include_prior_complete_cycle(self):
        with TemporaryDirectory() as r:
            k,*_=self.make(r);p=k['out']/'batches/001/FORECAST.json';p.write_text(json.dumps({'left':1,'cycles':[]}))
            with self.assertRaisesRegex(ValueError,'forecast'):e.check_body(**k)

    def test_gpu_pack_rejects_gold_and_never_replaces_prompt(self):
        with TemporaryDirectory() as r:
            k,ids,_,_,prompts=self.make(r)
            pack={'plan':k['plan'],'source':{p:{'problem':'question'} for p in ids},'prompts':prompts}
            tok=NS(apply_chat_template=lambda *a,**kw:[9,10])
            l.check_native_prompts(tok,pack)
            pack['source'][ids[0]]['gold']='1'
            with self.assertRaisesRegex(ValueError,'question text'):l.check_native_prompts(tok,pack)
            del pack['source'][ids[0]]['gold'];pack['prompts'][ids[0]]=[10]
            with self.assertRaisesRegex(ValueError,'prompt mismatch'):l.check_native_prompts(tok,pack)

    def test_saved_boolean_adapter_keeps_original_four_attempts_without_rescore(self):
        with TemporaryDirectory() as r:
            k,ids,right,left,_=self.make(r);raw=[];transport=[]
            for i in range(2):
                raw+=read(k['out']/f'batches/{i:03d}/RAW.json');transport+=read(k['out']/f'batches/{i:03d}/TRANSPORT.json')
            gold=[{'problem_id':pid,'gold':'1','original_source_row_sha256':'a'*64} for pid in ids]
            rows=l.score_rows(k['plan'],gold,raw,transport)
            scores=[{'id':x['id'],'score':{'correct':True,'parsed':True,'box_extracted':True}} for x in rows]
            records,result=l.selected_records(k['plan'],gold,raw,transport,scores,ids,right,left,set())
            self.assertEqual(len(records),264);self.assertEqual(result['insufficient_common_support'],66)
            self.assertTrue(all(x['t15'].endswith('attempt01') for x in result['selected']))
            self.assertFalse(result['training_admitted']);scores[0]['score']['correct']=None
            with self.assertRaisesRegex(ValueError,'Boolean'):l.selected_records(k['plan'],gold,raw,transport,scores,ids,right,left,set())

    def test_request_reordering_rejected_without_model_or_symbolic_calls(self):
        with TemporaryDirectory() as r:
            k,*_=self.make(r);plan=copy.deepcopy(k['plan']);plan['new_requests'][0:2]=reversed(plan['new_requests'][0:2])
            with self.assertRaisesRegex(ValueError,'window order'):e.checked_plan(plan)


if __name__=='__main__':unittest.main()
