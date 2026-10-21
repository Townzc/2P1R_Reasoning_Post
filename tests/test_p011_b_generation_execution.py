"""New synthetic orchestration tests only; no original data/model/scorer."""
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from experiments.p011 import b_generation_execution as x
from experiments.p011.short_generation import b_requests
from experiments.sft_allocation_midpoint.common import read


class Store(dict):
    def put(self, key, value, skip_if_exists):
        if key in self:
            return False
        self[key] = value
        return True


class BGeneration(unittest.TestCase):
    def setup_job(self, root, mode=None):
        ids=[f'synthetic-{i}' for i in range(400)]
        prompts={p:[1,2] for p in ids}
        rows=b_requests(ids,prompts)
        state={'time':1.,'calls':0,'forecasts':[]}
        store=Store();claim={'synthetic':True};store['b/claim']=claim
        def commit():state['time']+=2
        def forecast(left,times):
            state['forecasts'].append((left,list(times)))
            if mode=='forecast':raise ValueError('synthetic budget failure')
            return {'synthetic':True}
        class LLM:
            def generate(self,prompts,params,use_tqdm):
                state['calls']+=1;state['time']+=1
                if mode=='backend':raise RuntimeError('synthetic backend failure')
                result=[NS(prompt_token_ids=q['prompt_token_ids'],outputs=[NS(
                    token_ids=[4,151645],text='synthetic',finish_reason='stop',
                    stop_reason=151645)]) for q in prompts]
                if mode=='shape':result.pop()
                return result
        def transport(raw):
            if mode=='transport':raise ValueError('synthetic transport failure')
            return {'synthetic_valid':True}
        kwargs=dict(ordered400=ids,prompts=prompts,rows=rows,out=Path(root)/'out',
            key='b',claim=claim,store=store,commit=commit,llm=LLM(),
            parameter_constructor=lambda **v:v,transport=transport,
            forecast=forecast,check=lambda:None,clock=lambda:state['time'])
        return kwargs,state

    def test_complete6400_and_full_cycle_prediction(self):
        with tempfile.TemporaryDirectory() as d:
            kw,s=self.setup_job(d);r=x.generate(**kw)
            self.assertEqual((r['new_outputs'],r['complete_batches'],s['calls']),(6400,25,25))
            self.assertEqual(s['forecasts'][1],(24,[7.]))
            self.assertEqual(r['new_symbolic_scores'],0)

    def test_unknown_backend_failure_consumes_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            kw,s=self.setup_job(d,'backend')
            with self.assertRaisesRegex(RuntimeError,'backend'):x.generate(**kw)
            self.assertIn('b/batch/000',kw['store'])
            with self.assertRaisesRegex(ValueError,'partial'):x.generate(**kw)
            self.assertEqual(s['calls'],1)

    def test_shape_failure_preserves_every_return_before_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            kw,s=self.setup_job(d,'shape')
            with self.assertRaisesRegex(ValueError,'raw output'):x.generate(**kw)
            self.assertEqual(len(read(kw['out']/'batches/000/RAW.json')),255)
            self.assertNotIn('b/batch_done/000',kw['store'])

    def test_transport_failure_preserves_raw_and_never_retries(self):
        with tempfile.TemporaryDirectory() as d:
            kw,s=self.setup_job(d,'transport')
            with self.assertRaisesRegex(ValueError,'transport'):x.generate(**kw)
            self.assertEqual(len(read(kw['out']/'batches/000/RAW.json')),256)
            self.assertEqual(s['calls'],1)

    def test_wrong_seed_rejected_before_markers_or_generation(self):
        with tempfile.TemporaryDirectory() as d:
            kw,s=self.setup_job(d);kw['rows'][0]['request']['seed']+=1
            with self.assertRaisesRegex(ValueError,'ordered seeds'):x.generate(**kw)
            self.assertNotIn('b/generation',kw['store']);self.assertEqual(s['calls'],0)

    def test_budget_rejects_before_first_batch(self):
        with tempfile.TemporaryDirectory() as d:
            kw,s=self.setup_job(d,'forecast')
            with self.assertRaisesRegex(ValueError,'budget'):x.generate(**kw)
            self.assertEqual(s['calls'],0)
            self.assertNotIn('b/batch/000',kw['store'])
            self.assertFalse((kw['out']/'COMPLETED.json').exists())

    def test_missing_prompt_rejected_before_generation(self):
        with tempfile.TemporaryDirectory() as d:
            kw,s=self.setup_job(d);kw['prompts'].pop(kw['ordered400'][-1])
            with self.assertRaisesRegex(ValueError,'prompt identities'):x.generate(**kw)
            self.assertEqual(s['calls'],0)


if __name__=='__main__':unittest.main()
