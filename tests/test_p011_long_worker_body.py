"""Only new full-body orchestration checks; no real model, input or old tests."""
from contextlib import ExitStack
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from experiments.p011 import long_execution as x
from experiments.p011.long_numeric import forecast
from experiments.sft_allocation_midpoint.common import dump,digest,manifest,read
from tests.test_p011_long_execution import LongExecutionChecks,Store


class LongWorkerBody(unittest.TestCase):
    def body(self,kind,tmp,events,child_fails=False):
        root=Path(tmp);inputs=root/'inputs';out=root/'out';model=root/'model'
        inputs.mkdir();out.mkdir();model.mkdir();(model/'synthetic.bin').write_bytes(b'model-placeholder')
        rows=LongExecutionChecks.endpoint()
        for r in rows:r['prompt_text_sha256']=digest('native prompt')
        dump(inputs/'ENDPOINT_GPU.json',rows)
        job=dict(kind=kind,arm='S-L15',model=dict(model_id=x.training.ARMS['S-L15']['model_id'],
            revision=x.training.ARMS['S-L15']['revision'],remote_path=str(model),files=manifest(model)),
            input_files=manifest(inputs),context=16386,eos_token_ids=[151645])
        claim={'identity':'synthetic'};store=Store();store['r/claim']=claim
        now=time.time();policy=LongExecutionChecks.policy()
        policy.update(worker_start_epoch=now,result_deadline_epoch=now+3000)
        volume=NS(commit=lambda:None,reload=lambda:None)
        conf=NS(model_config=NS(max_model_len=16386,enforce_eager=False,dtype='torch.bfloat16',
            hf_config=NS(eos_token_id=151645,architectures=['Qwen2ForCausalLM'])),
            scheduler_config=NS(max_num_seqs=32,max_num_batched_tokens=8192,enable_chunked_prefill=True),
            cache_config=NS(enable_prefix_caching=False,gpu_memory_utilization=.8),
            compilation_config=NS(level=3,cudagraph_mode=NS(name='FULL_AND_PIECEWISE'),
                                  cudagraph_capture_sizes=[1,2,4,8,16,32]))
        class LLM:
            def __init__(self,**kw):events.append(('LLM',kw['model']));self.llm_engine=NS(vllm_config=conf)
            def generate(self,prompts,params,use_tqdm):
                events.append(('generate',len(prompts)))
                return [NS(prompt_token_ids=p['prompt_token_ids'],outputs=[NS(token_ids=[20,151645],
                    text='synthetic',finish_reason='stop',stop_reason=151645)]) for p in prompts]
        def joined(*args,**kw):
            events.append(('joined',0))
            if child_fails:raise RuntimeError('synthetic training failure')
            return {'complete':True},[1.],str(out/'model_for_vllm')
        tokenizer=NS(eos_token_id=151645,decode=lambda *a,**kw:'native prompt')
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ,{'VLLM_USE_V1':'1'}))
            stack.enter_context(patch.dict('sys.modules',{
                'vllm':NS(LLM=LLM,SamplingParams=lambda **kw:kw),
                'transformers':NS(AutoTokenizer=NS(from_pretrained=lambda *a,**kw:tokenizer))}))
            stack.enter_context(patch.object(x,'software',lambda:{'synthetic':True}))
            stack.enter_context(patch.object(x,'joined_training',joined))
            result=x.worker_body(job,inputs,out,{'job_sha256':digest(job)},'r',claim,now+1800,
                                 policy,store,volume)
        return result,out,store

    def test_student_exits_before_engine_and_emits_all3300(self):
        with tempfile.TemporaryDirectory() as tmp:
            events=[];result,out,store=self.body('student',tmp,events)
            self.assertEqual(events[:2],[('joined',0),('LLM',str(out/'model_for_vllm'))])
            self.assertEqual(result['raw_endpoint_count'],3300)
            self.assertEqual(sum(v for k,v in events if k=='generate'),3300)
            self.assertEqual(len(list((out/'raw').glob('*.json'))),104)
            self.assertEqual(read(out/'LINUX_CONSTRUCTORS.json')['count'],3300)

    def test_baseline_skips_training_and_uses_original_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            events=[];result,out,store=self.body('baseline',tmp,events)
            self.assertFalse(any(k=='joined' for k,v in events))
            self.assertEqual(events[0],('LLM',str(Path(tmp)/'model')))
            self.assertIsNone(result['training'])
            self.assertEqual(read(out/'BASELINE_PROOF.json')['training_updates'],0)

    def test_failed_training_never_constructs_engine_or_generates(self):
        with tempfile.TemporaryDirectory() as tmp:
            events=[]
            with self.assertRaisesRegex(RuntimeError,'synthetic training'):
                self.body('student',tmp,events,child_fails=True)
            self.assertEqual(events,[('joined',0)])
            self.assertFalse((Path(tmp)/'out/RESULT.json').exists())

    def test_80percent_gate_independent_of_full_reservation(self):
        p=LongExecutionChecks.policy()
        p.update(prior_reserved_usd='111.92',uncalibrated_future_seconds=1400)
        # The3.08 reserve fits exactly; the predicted2.89 exceeds .8*3.08.
        with self.assertRaisesRegex(ValueError,'80-percent'):
            forecast(p,3,4,[],[],1005.)


if __name__=='__main__':unittest.main()
