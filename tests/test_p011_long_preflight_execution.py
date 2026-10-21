"""Additional new mocked preflight execution tests; no GPU or old test methods."""
from pathlib import Path
from types import SimpleNamespace
import os,sys,tempfile,unittest
from unittest.mock import Mock,patch
from tests.test_p011_long_preflight import inputs,candidate
from tests.test_p011_c1_execution_draft import Store
from experiments.p011.long_preflight import subset,execution
from experiments.sft_allocation_midpoint.common import dump,read,manifest,digest


class ExecutionTests(unittest.TestCase):
    def test_terminal_phase_includes_final_commit_and_only_two_updates(self):
        with tempfile.TemporaryDirectory() as d:
            e,r,l,c=inputs();rows,plan,rates,req,proof=subset.select(e,r,c,'S-L15')
            ticks=[0.]
            def mono():ticks[0]+=.1;return ticks[0]
            def commit():ticks[0]+=2
            store=Store()
            with patch.object(execution.time,'monotonic',side_effect=mono):
                journal=execution.PhaseJournal(d,'new',store,commit,lambda:None,rows,plan,rates,lambda n,t:{'engineering':True})
                targets=processed=0
                for rec in journal.records:
                    name=f"update_{rec['step']:05d}";journal.begin(name,rec);journal.commit()
                    targets+=rec['supervised_tokens'];processed+=rec['processed_tokens']
                    journal.end(name,{**rec,'loss':1.,'gradient_norm':1.,'seconds':.1,
                        'cumulative_supervised':targets,'cumulative_processed':processed});journal.commit();journal.finish_update()
                for name in ('terminal_state','terminal_model_export'):
                    journal.begin(name,{});journal.commit();journal.end(name,{});journal.commit()
                journal.complete()
                self.assertEqual(len(journal.cycles),2);self.assertTrue(all(p['seconds']>=4 for p in journal.phases))
                self.assertTrue(all(p['final_volume_commit_included'] for p in journal.phases))
                with self.assertRaises(ValueError):journal.begin('update_00003',{})

    def body(self,root,partial=False):
        e,r,l,c=inputs();rows,plan,rates,req,proof=subset.select(e,r,c,'S-L15')
        inp=root/'input';inp.mkdir();out=root/'output';out.mkdir()
        dump(inp/'ENDPOINT_GPU.json',req);dump(inp/'SUBSET_PROOF.json',proof)
        job=candidate()['jobs']['preflight_S-L15_s17_r1'];job['input_files']=manifest(inp)
        identity={'engineering_preflight':True,'job_sha256':digest(job)}
        claim={'new':'claim'};store=Store({'new/claim':claim});volume=Mock();volume.commit.return_value=None
        tok=SimpleNamespace(eos_token_id=151645,decode=lambda *_args,**_kwargs:'native')
        calls=[]
        def generate(prompts,params,use_tqdm):
            calls.append((prompts,params));items=prompts[:-1] if partial else prompts
            return [SimpleNamespace(prompt_token_ids=x['prompt_token_ids'],outputs=[SimpleNamespace(token_ids=[151645],text='<|im_end|>',finish_reason='stop',stop_reason=151645)]) for x in items]
        cfg=SimpleNamespace(model_config=SimpleNamespace(hf_config=SimpleNamespace(eos_token_id=[151645,151643],architectures=['Qwen2ForCausalLM'])))
        llm=SimpleNamespace(llm_engine=SimpleNamespace(vllm_config=cfg),generate=generate)
        modules={'transformers':SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=lambda *_a,**_k:tok)),
                 'vllm':SimpleNamespace(LLM=lambda **_k:llm,SamplingParams=lambda **k:k)}
        tick=execution.time.time();timing={'worker_start_epoch':tick,'worker_hard_seconds':900,'owner_decision_sha256':subset.OWNER_SHA}
        with patch.dict(os.environ,{'VLLM_USE_V1':'1'}),patch.dict(sys.modules,modules), \
                patch.object(execution,'joined_training',return_value=({'engineering_preflight':True},[1.,2.],str(out/'model_for_vllm'))) as joined, \
                patch.object(execution.original,'software',return_value={'mocked':True}), \
                patch.object(execution.original,'validate_engine',return_value={'max_num_seqs':256}):
            if partial:
                with self.assertRaisesRegex(ValueError,'Partial/invalid'):execution.worker_body(job,inp,out,identity,'new',claim,tick+900,timing,store,volume)
            else:
                result=execution.worker_body(job,inp,out,identity,'new',claim,tick+900,timing,store,volume)
                self.assertFalse(result['scientific_cell_result']);self.assertTrue(result['no_correctness_scoring'])
                self.assertEqual(result['generated_tokens'],32);self.assertTrue(result['formal_batch_throughput_is_not_measured'])
            joined.assert_called_once();self.assertEqual(len(calls),1)
        return out,store

    def test_join_precedes_single_original_engine_batch_and_engineering_result(self):
        with tempfile.TemporaryDirectory() as d:
            out,store=self.body(Path(d));self.assertEqual(len(read(out/'raw/eval_0000.json')),32)
            self.assertIn('new/done/eval_0000',store)

    def test_partial_backend_return_retained_without_complete_or_retry(self):
        with tempfile.TemporaryDirectory() as d:
            out,store=self.body(Path(d),True)
            self.assertEqual(len(read(out/'raw/eval_0000.json')),31)
            self.assertIn('new/unit/eval_0000',store);self.assertNotIn('new/done/eval_0000',store)
            self.assertFalse((out/'RESULT.json').exists())

if __name__=='__main__':unittest.main()
