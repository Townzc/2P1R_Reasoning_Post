"""New isolated C2 fixtures only; no replay of original data or prior test suite."""
from pathlib import Path
from types import SimpleNamespace as NS
from tempfile import TemporaryDirectory
import unittest
from experiments.p011 import c2_generation_window as p,c2_generation_execution as x
from tests.test_p011_c1_short_drafts import saved
from experiments.sft_allocation_midpoint.common import read

class Store(dict):
    def put(self,key,value,skip_if_exists):
        if key in self:return False
        self[key]=value;return True

class C2Window(unittest.TestCase):
    def fixture(self,n=500):
        ids=[f'p{i}' for i in range(n)]
        right={f'{pid}::attempt01':saved(pid,1,True) for pid in ids}
        return ids,right,{}, {pid:[1,2] for pid in ids},set(ids[:23])

    def test_reuse_existing_and_exhausted_without_new_attempts(self):
        ids,right,left,prompts,s1=self.fixture()
        left['p0::attempt01']=saved('p0',1,True)
        for a in range(1,5):right[f'p1::attempt{a:02d}']=saved('p1',a,False)
        left['p2::attempt03']=saved('p2',3,True)
        plan=p.plan_window(ids,right,left,prompts,s1,2)
        self.assertEqual(plan['window_parents'],['p2','p3'])
        self.assertEqual([r['request']['attempt'] for r in plan['new_requests'][:3]],[1,2,4])
        self.assertFalse(any(r['request']['problem_id'] in ('p0','p1') for r in plan['new_requests']))

    def test_missing_old_T72_never_generates_replacement(self):
        args=list(self.fixture());del args[1]['p1::attempt01']
        plan=p.plan_window(*args,window_size=3)
        self.assertEqual(plan['new_requests'],[])
        self.assertEqual(plan['blocked_missing_old_T72'],'p1')

    def test_unknown_verdict_is_not_false(self):
        args=list(self.fixture());args[2]['p0::attempt01']=saved('p0',1,False)
        args[2]['p0::attempt01']['score']['score']['correct']=None
        with self.assertRaisesRegex(ValueError,'Boolean'):p.plan_window(*args,window_size=2)

    def test_exact_first400_in_order_keeps_overlap_and_extra_outputs(self):
        args=self.fixture();plan=p.plan_window(*args,window_size=500)
        new={r['request']['candidate_id']:saved(r['request']['problem_id'],r['request']['attempt'],True)
             for r in plan['new_requests']}
        result=p.after_window(plan,args[0],args[1],args[2],new,args[4])
        self.assertEqual([r['problem_id'] for r in result['selected']],args[0][:400])
        self.assertEqual(result['S1_overlap'],23);self.assertEqual(result['new_window_output_count'],2000)
        self.assertFalse(result['training_admitted'])

    def test_missing_new_row_blocks_selection_instead_of_zero(self):
        args=self.fixture();plan=p.plan_window(*args,window_size=1)
        new={r['request']['candidate_id']:saved('p0',r['request']['attempt'],True) for r in plan['new_requests']}
        del new['p0::attempt04']
        with self.assertRaisesRegex(ValueError,'Complete exact'):p.after_window(plan,args[0],args[1],args[2],new,args[4])

    def test_basis_change_blocks_even_if_verdict_unchanged(self):
        args=list(self.fixture());plan=p.plan_window(*args,window_size=1)
        new={r['request']['candidate_id']:saved('p0',r['request']['attempt'],True) for r in plan['new_requests']}
        args[1]['p0::attempt01']['answer_text']='different frozen source'
        with self.assertRaisesRegex(ValueError,'basis changed'):p.after_window(plan,args[0],args[1],args[2],new,args[4])

    def job(self,root,mode=None):
        args=self.fixture(70);plan=p.plan_window(*args,window_size=70)
        state={'clock':0.,'calls':0,'forecasts':[]};claim={'synthetic':True};store=Store({'c2/claim':claim})
        def commit():state['clock']+=1
        class LLM:
            def generate(self,rows,params,use_tqdm):
                state['calls']+=1;state['clock']+=1
                if mode=='backend':raise RuntimeError('synthetic backend unavailable')
                values=[NS(prompt_token_ids=r['prompt_token_ids'],outputs=[NS(token_ids=[3,151645],text='fake',finish_reason='stop',stop_reason=151645)]) for r in rows]
                return values[:-1] if mode=='shape' else values
        def forecast(left,cycles):
            state['forecasts'].append((left,cycles))
            if mode=='budget':raise ValueError('synthetic budget gate')
            return {'synthetic':True}
        kw=dict(plan=plan,out=Path(root)/'out',key='c2',claim=claim,store=store,commit=commit,
            llm=LLM(),parameter_constructor=lambda **v:v,transport=lambda r:{'fake':True},
            forecast=forecast,check=lambda:None,clock=lambda:state['clock'])
        return kw,state

    def test_one_window_full_and_tail_batch_cycle_accounted(self):
        with TemporaryDirectory() as root:
            kw,s=self.job(root);r=x.generate_window(**kw)
            self.assertEqual(r['new_outputs'],280);self.assertEqual(s['calls'],2)
            self.assertEqual(s['forecasts'],[(2,[]),(1,[4.])])
            self.assertEqual(read(kw['out']/'batches/001/ACK.json')['count'],24)
            self.assertEqual(r['new_symbolic_scores'],0)

    def test_unknown_backend_consumes_fence_no_retry(self):
        with TemporaryDirectory() as root:
            kw,s=self.job(root,'backend')
            with self.assertRaises(RuntimeError):x.generate_window(**kw)
            self.assertIn('c2/batch/000',kw['store'])
            with self.assertRaisesRegex(ValueError,'replayed'):x.generate_window(**kw)
            self.assertEqual(s['calls'],1)

    def test_shape_failure_retains_all_returned_raw(self):
        with TemporaryDirectory() as root:
            kw,s=self.job(root,'shape')
            with self.assertRaisesRegex(ValueError,'shape'):x.generate_window(**kw)
            self.assertEqual(len(read(kw['out']/'batches/000/RAW.json')),255)
            self.assertNotIn('c2/batch_done/000',kw['store'])

    def test_budget_blocks_before_any_generation(self):
        with TemporaryDirectory() as root:
            kw,s=self.job(root,'budget')
            with self.assertRaisesRegex(ValueError,'budget'):x.generate_window(**kw)
            self.assertEqual(s['calls'],0);self.assertNotIn('c2/batch/000',kw['store'])

    def test_fifth_attempt_rejected_before_global_fence(self):
        with TemporaryDirectory() as root:
            kw,s=self.job(root);kw['plan']['new_requests'][0]['request']['attempt']=5
            with self.assertRaisesRegex(ValueError,'1..4'):x.generate_window(**kw)
            self.assertNotIn('c2/window',kw['store'])

    def test_already_complete_common_support_does_no_generation(self):
        args=list(self.fixture());args[2]={f'{pid}::attempt01':saved(pid,1,True) for pid in args[0][:400]}
        plan=p.plan_window(*args,window_size=700)
        self.assertTrue(plan['initial_prefix']['complete']);self.assertEqual(plan['new_requests'],[])

if __name__=='__main__':unittest.main()
